from . import gf256 as gf


def cauchy(rows, cols):
    """A rows x cols Cauchy matrix. Every square submatrix is invertible."""
    xs = range(cols, cols + rows)
    ys = range(cols)
    return [[gf.inv(x ^ y) for y in ys] for x in xs]


def invert(matrix):
    """Gauss-Jordan inversion over GF(256)."""
    n = len(matrix)
    aug = [list(row) + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(matrix)]

    for col in range(n):
        pivot = col
        while pivot < n and aug[pivot][col] == 0:
            pivot += 1
        if pivot == n:
            raise ValueError("matrix is singular")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]

        scale = gf.inv(aug[col][col])
        aug[col] = [gf.mul(v, scale) for v in aug[col]]

        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor:
                base = aug[col]
                aug[r] = [a ^ gf.mul(factor, b) for a, b in zip(aug[r], base)]

    return [row[n:] for row in aug]
