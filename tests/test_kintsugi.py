import itertools
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kintsugi import Codec, join_shards, split_bytes  # noqa: E402
from kintsugi import gf256 as gf  # noqa: E402
from kintsugi.container import pack_shard  # noqa: E402


def test_field_laws():
    rng = random.Random(0)
    for a in range(1, 256):
        assert gf.mul(a, gf.inv(a)) == 1
    for _ in range(5000):
        a = rng.randrange(1, 256)
        b = rng.randrange(1, 256)
        assert gf.div(gf.mul(a, b), b) == a


def test_mul_region_matches_scalar():
    data = bytes(range(256))
    for scalar in (0, 1, 7, 200, 255):
        expected = bytes(gf.mul(scalar, d) for d in data)
        assert gf.mul_region(scalar, data) == expected


@pytest.mark.parametrize("data,parity", [(4, 2), (10, 4), (6, 3), (1, 3)])
def test_recover_from_every_loss_pattern(data, parity):
    """Small configs: exhaustively check every possible loss pattern."""
    rng = random.Random(data * 100 + parity)
    shards = [bytes(rng.randrange(256) for _ in range(64)) for _ in range(data)]
    codec = Codec(data, parity)
    full = codec.encode(shards)

    for drop in range(parity + 1):
        for missing in itertools.combinations(range(data + parity), drop):
            damaged = [None if i in missing else s for i, s in enumerate(full)]
            assert codec.reconstruct(damaged) == full


@pytest.mark.parametrize("data,parity", [(16, 8), (32, 16)])
def test_recover_large_configs_sampled(data, parity):
    """Large configs: sample random maximum-loss patterns."""
    rng = random.Random(data * 100 + parity)
    shards = [bytes(rng.randrange(256) for _ in range(64)) for _ in range(data)]
    codec = Codec(data, parity)
    full = codec.encode(shards)

    for _ in range(50):
        missing = rng.sample(range(data + parity), parity)
        damaged = [None if i in missing else s for i, s in enumerate(full)]
        assert codec.reconstruct(damaged) == full


def test_too_many_losses_fails():
    codec = Codec(4, 2)
    shards = [os.urandom(32) for _ in range(4)]
    full = codec.encode(shards)
    damaged = list(full)
    for i in range(3):
        damaged[i] = None
    with pytest.raises(ValueError):
        codec.reconstruct(damaged)


@pytest.mark.parametrize("size", [0, 1, 17, 1000, 5000])
def test_container_roundtrip(size):
    data = os.urandom(size)
    shards, original_len = split_bytes(data, 6, 3)
    blobs = [pack_shard(6, 3, i, s, original_len) for i, s in enumerate(shards)]

    rng = random.Random(size)
    survivors = blobs[:]
    rng.shuffle(survivors)
    survivors = survivors[:6]
    assert join_shards(survivors) == data


def test_corrupted_shard_is_ignored():
    data = os.urandom(500)
    shards, original_len = split_bytes(data, 4, 2)
    blobs = [pack_shard(4, 2, i, s, original_len) for i, s in enumerate(shards)]
    blobs[0] = blobs[0][:-1] + bytes([blobs[0][-1] ^ 0xFF])
    assert join_shards(blobs) == data
