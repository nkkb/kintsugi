from typing import List, Optional, Sequence

from . import gf256 as gf
from .matrix import cauchy, invert


class Codec:
    """Reed-Solomon codec for a fixed (data, parity) layout.

    Given ``data`` data shards and ``parity`` parity shards, any ``data``
    surviving shards out of the total are enough to rebuild everything.
    """

    def __init__(self, data: int, parity: int):
        if data < 1 or parity < 1:
            raise ValueError("need at least one data shard and one parity shard")
        if data + parity > 256:
            raise ValueError("data + parity must not exceed 256")
        self.data = data
        self.parity = parity
        self.total = data + parity
        self._coeffs = cauchy(parity, data)

    def _row(self, index):
        if index < self.data:
            row = [0] * self.data
            row[index] = 1
            return row
        return self._coeffs[index - self.data]

    def _parity_shards(self, data_shards):
        size = len(data_shards[0])
        result = []
        for coeffs in self._coeffs:
            acc = bytes(size)
            for c, shard in zip(coeffs, data_shards):
                if c:
                    acc = gf.xor_region(acc, gf.mul_region(c, shard))
            result.append(acc)
        return result

    def encode(self, data_shards: Sequence[bytes]) -> List[bytes]:
        """Return all ``total`` shards (the data shards followed by parity)."""
        if len(data_shards) != self.data:
            raise ValueError(f"expected {self.data} data shards, got {len(data_shards)}")
        size = len(data_shards[0])
        if any(len(s) != size for s in data_shards):
            raise ValueError("all shards must be the same length")
        return list(data_shards) + self._parity_shards(list(data_shards))

    def reconstruct(self, shards: Sequence[Optional[bytes]]) -> List[bytes]:
        """Rebuild every shard from a list where missing ones are ``None``."""
        if len(shards) != self.total:
            raise ValueError(f"expected {self.total} slots, got {len(shards)}")

        present = [(i, s) for i, s in enumerate(shards) if s is not None]
        if len(present) < self.data:
            raise ValueError(
                f"not enough shards to reconstruct: need {self.data}, have {len(present)}"
            )

        chosen = present[: self.data]
        size = len(chosen[0][1])
        inverse = invert([self._row(i) for i, _ in chosen])

        recovered = []
        for row in inverse:
            acc = bytes(size)
            for coef, (_, shard) in zip(row, chosen):
                if coef:
                    acc = gf.xor_region(acc, gf.mul_region(coef, shard))
            recovered.append(acc)

        full = list(shards)
        for i in range(self.data):
            full[i] = recovered[i]

        if any(full[self.data + i] is None for i in range(self.parity)):
            parity = self._parity_shards(recovered)
            for i in range(self.parity):
                if full[self.data + i] is None:
                    full[self.data + i] = parity[i]

        return full
