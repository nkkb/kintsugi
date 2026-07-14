"""On-disk shard format.

Each shard file is a small header followed by its payload. The CRC lets the
reader drop a corrupted shard and treat it as missing rather than trusting
bad bytes.
"""

import struct
import zlib
from typing import List, Optional, Tuple

from .codec import Codec

MAGIC = b"KTSG"
VERSION = 1
_HEADER = struct.Struct("<4sBBBBIQI")


def split_bytes(data: bytes, data_shards: int, parity_shards: int) -> Tuple[List[bytes], int]:
    codec = Codec(data_shards, parity_shards)
    original_len = len(data)
    shard_len = max(1, (original_len + data_shards - 1) // data_shards)

    padded = data + bytes(shard_len * data_shards - original_len)
    pieces = [padded[i * shard_len:(i + 1) * shard_len] for i in range(data_shards)]
    return codec.encode(pieces), original_len


def pack_shard(data_shards: int, parity_shards: int, index: int, payload: bytes, original_len: int) -> bytes:
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    header = _HEADER.pack(MAGIC, VERSION, data_shards, parity_shards, index, len(payload), original_len, crc)
    return header + payload


def unpack_shard(blob: bytes) -> Optional[dict]:
    if len(blob) < _HEADER.size:
        return None
    magic, version, data_shards, parity_shards, index, shard_len, original_len, crc = _HEADER.unpack(
        blob[:_HEADER.size]
    )
    if magic != MAGIC or version != VERSION:
        return None

    payload = blob[_HEADER.size:_HEADER.size + shard_len]
    if len(payload) != shard_len or (zlib.crc32(payload) & 0xFFFFFFFF) != crc:
        return None

    return {
        "data": data_shards,
        "parity": parity_shards,
        "index": index,
        "original_len": original_len,
        "payload": payload,
    }


def join_shards(blobs: List[bytes]) -> bytes:
    parsed = [s for s in (unpack_shard(b) for b in blobs) if s is not None]
    if not parsed:
        raise ValueError("no valid shards provided")

    ref = parsed[0]
    data_shards, parity_shards, original_len = ref["data"], ref["parity"], ref["original_len"]

    slots: List[Optional[bytes]] = [None] * (data_shards + parity_shards)
    for s in parsed:
        if (s["data"], s["parity"], s["original_len"]) == (data_shards, parity_shards, original_len):
            slots[s["index"]] = s["payload"]

    full = Codec(data_shards, parity_shards).reconstruct(slots)
    return b"".join(full[:data_shards])[:original_len]
