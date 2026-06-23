"""Arithmetic in GF(2**8) using the 0x11d primitive polynomial."""

PRIMITIVE = 0x11D
ORDER = 256

_exp = [0] * 512
_log = [0] * ORDER


def _build():
    x = 1
    for i in range(ORDER - 1):
        _exp[i] = x
        _log[x] = i
        x <<= 1
        if x & ORDER:
            x ^= PRIMITIVE
    for i in range(ORDER - 1, 512):
        _exp[i] = _exp[i - (ORDER - 1)]


_build()


def mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _exp[_log[a] + _log[b]]


def div(a, b):
    if b == 0:
        raise ZeroDivisionError("division by zero in GF(256)")
    if a == 0:
        return 0
    return _exp[_log[a] - _log[b] + (ORDER - 1)]


def inv(a):
    if a == 0:
        raise ZeroDivisionError("inverse of zero in GF(256)")
    return _exp[(ORDER - 1) - _log[a]]


_region = [bytes(mul(s, d) for d in range(ORDER)) for s in range(ORDER)]


def mul_region(scalar, data):
    """Multiply every byte of ``data`` by ``scalar`` in the field."""
    if scalar == 0:
        return bytes(len(data))
    if scalar == 1:
        return bytes(data)
    return data.translate(_region[scalar])


def xor_region(a, b):
    n = len(a)
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(n, "big")
