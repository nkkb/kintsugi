import argparse
import os
import sys

from .container import join_shards, pack_shard, split_bytes


def _split(args):
    with open(args.file, "rb") as f:
        data = f.read()

    shards, original_len = split_bytes(data, args.data, args.parity)
    total = args.data + args.parity
    out_dir = args.out or os.path.dirname(os.path.abspath(args.file))
    os.makedirs(out_dir, exist_ok=True)

    width = len(str(total - 1))
    base = os.path.basename(args.file)
    for index, payload in enumerate(shards):
        name = f"{base}.{index:0{width}d}.ktsg"
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(pack_shard(args.data, args.parity, index, payload, original_len))

    print(f"{base}: wrote {total} shards to {out_dir}")
    print(f"any {args.data} of them can rebuild the file (up to {args.parity} may be lost)")
    return 0


def _join(args):
    blobs = []
    for path in args.shards:
        with open(path, "rb") as f:
            blobs.append(f.read())

    data = join_shards(blobs)
    with open(args.out, "wb") as f:
        f.write(data)

    print(f"rebuilt {args.out} ({len(data)} bytes) from {len(args.shards)} shard(s)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="kintsugi",
        description="Split files into Reed-Solomon shards and rebuild them from whatever survives.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("split", help="break a file into recoverable shards")
    sp.add_argument("file")
    sp.add_argument("-d", "--data", type=int, required=True, help="number of data shards")
    sp.add_argument("-p", "--parity", type=int, required=True, help="number of parity shards")
    sp.add_argument("-o", "--out", help="output directory (default: next to the file)")

    jp = sub.add_parser("join", help="rebuild a file from surviving shards")
    jp.add_argument("shards", nargs="+", help="shard files (any subset that is large enough)")
    jp.add_argument("-o", "--out", required=True, help="path to write the rebuilt file")

    args = parser.parse_args(argv)

    try:
        if args.command == "split":
            return _split(args)
        return _join(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
