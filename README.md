# kintsugi

Split a file into `n` shards so that **any `k` of them** are enough to rebuild
it. Lose disks, lose nodes, lose packets, lose whole shard files — as long as
`k` survive, the original comes back byte for byte.

The name comes from *kintsugi*, the craft of repairing broken pottery: the
object is whole again even after pieces are lost.

- Pure Python, no dependencies, fully offline.
- Real Reed-Solomon over GF(2⁸) with a Cauchy generator matrix, so recovery
  works for **any** combination of lost shards, not just a lucky few.
- A small CLI for splitting and rebuilding actual files.

## Install

```bash
pip install kintsugiV01
```

Or from a checkout:

```bash
pip install -e .
```

## How it works

You pick `k` data shards and `m` parity shards (`n = k + m` total).

| Layout | Storage overhead | Shards you can lose |
| ------ | ---------------- | ------------------- |
| 4 + 2  | +50%             | any 2               |
| 10 + 4 | +40%             | any 4               |
| 6 + 3  | +50%             | any 3               |

Recovery is all-or-nothing per file: with at least `k` shards you get an exact
rebuild; with fewer than `k` it is information-theoretically impossible (and
the library tells you so instead of guessing).

## CLI

Split a file into 6 data + 3 parity shards:

```bash
kintsugi split report.pdf -d 6 -p 3 -o shards/
```

Delete any 3 of the 9 `.ktsg` files, then rebuild from whatever is left:

```bash
kintsugi join shards/report.pdf.*.ktsg -o report.pdf
```

Each shard carries a CRC, so a corrupted shard is dropped and treated as
missing rather than poisoning the output.

## Library

```python
from kintsugi import Codec

codec = Codec(data=4, parity=2)

shards = codec.encode([b"....", b"....", b"....", b"...."])  # 6 shards back

shards[1] = None   # a shard goes missing
shards[4] = None   # and another

rebuilt = codec.reconstruct(shards)   # all 6 shards, whole again
```

For files there are two helpers:

```python
from kintsugi import split_bytes, join_shards
```

## What it does not do

- It assumes a shard is either intact or gone. Silent bit-rot inside a shard is
  caught by the CLI's per-shard CRC; the core codec works on the erasure model.
- It is not a backup scheduler or a network transport — just the coding layer.

## Tests

```bash
pip install pytest
pytest
```

## License

MIT
