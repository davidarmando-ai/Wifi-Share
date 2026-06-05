"""
QR Code generator — Pure Python, no external dependencies.
Supports Byte mode, Version 1-10, Error Correction Level M, Mask 2.
"""

# ── Galois Field GF(2^8) ─────────────────────────────────────────────────────
GF256_EXP = [0] * 512
GF256_LOG = [0] * 256

def _build_gf():
    x = 1
    for i in range(255):
        GF256_EXP[i] = x
        GF256_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        GF256_EXP[i] = GF256_EXP[i - 255]

_build_gf()

def _gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return GF256_EXP[(GF256_LOG[a] + GF256_LOG[b]) % 255]

def _rs_poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] ^= _gf_mul(a, b)
    return r

def _rs_generator(n):
    g = [1]
    for i in range(n):
        g = _rs_poly_mul(g, [1, GF256_EXP[i]])
    return g

def _rs_encode(data, n_ec):
    gen = _rs_generator(n_ec)
    msg = list(data) + [0] * n_ec
    for i in range(len(data)):
        coef = msg[i]
        if coef != 0:
            for j in range(len(gen)):
                msg[i + j] ^= _gf_mul(gen[j], coef)
    return msg[len(data):]

# ── Version / capacity table (Byte, ECL M) ───────────────────────────────────
# (version, data_codewords, ec_codewords, blocks_spec)
_QR_TABLE = [
    (1,  16, 10, [(1, 16)]),
    (2,  28, 16, [(1, 28)]),
    (3,  44, 26, [(1, 44)]),
    (4,  64, 36, [(2, 32)]),
    (5,  86, 48, [(2, 43)]),
    (6, 108, 64, [(4, 27)]),
    (7, 124, 72, [(4, 31)]),
    (8, 154, 88, [(2, 38), (2, 39)]),
    (9, 182,110, [(3, 36), (2, 37)]),
    (10,216,130, [(4, 43), (1, 44)]),
]

_ALIGN = {
    1: [], 2: [6,18], 3: [6,22], 4: [6,26], 5: [6,30],
    6: [6,34], 7: [6,22,38], 8: [6,24,42], 9: [6,26,46], 10: [6,28,50]
}

# ── Bit stream ───────────────────────────────────────────────────────────────
class _BS:
    __slots__ = ('bits',)
    def __init__(self): self.bits = []
    def put(self, v, n):
        for i in range(n-1, -1, -1):
            self.bits.append((v >> i) & 1)
    def pad(self):
        while len(self.bits) % 8: self.bits.append(0)
    def tobytes(self):
        self.pad()
        return bytes(int(''.join(map(str, self.bits[i:i+8])), 2)
                     for i in range(0, len(self.bits), 8))

_PAD = [0xEC, 0x11]

def _encode_data(text, dc):
    b = text.encode('iso-8859-1')
    bs = _BS()
    bs.put(0b0100, 4)
    bs.put(len(b), 8)
    for x in b: bs.put(x, 8)
    bs.put(0, min(4, dc*8 - len(bs.bits)))
    bs.pad()
    raw = list(bs.tobytes())
    i = 0
    while len(raw) < dc:
        raw.append(_PAD[i % 2]); i += 1
    return bytes(raw[:dc])

def _interleave(data, ec_total, blocks):
    db, eb = [], []
    off = 0
    for cnt, sz in blocks:
        for _ in range(cnt):
            blk = list(data[off:off+sz])
            db.append(blk)
            eb.append(_rs_encode(blk, ec_total // sum(c for c,_ in blocks)))
            off += sz
    res = []
    for i in range(max(len(b) for b in db)):
        for b in db:
            if i < len(b): res.append(b[i])
    for i in range(max(len(b) for b in eb)):
        for b in eb:
            if i < len(b): res.append(b[i])
    return res

def _make_matrix(version, codewords):
    n = 17 + 4*version
    M = [[None]*n for _ in range(n)]
    F = [[False]*n for _ in range(n)]

    def place(r, c, v):
        if 0 <= r < n and 0 <= c < n:
            M[r][c] = v; F[r][c] = True

    def finder(r, c):
        for dr in range(7):
            for dc in range(7):
                v = (dr in (0,6) or dc in (0,6) or 2<=dr<=4 and 2<=dc<=4)
                place(r+dr, c+dc, int(v))
        for i in range(8):
            place(r+7, c+i, 0); place(r+i, c+7, 0)

    finder(0,0); finder(0,n-7); finder(n-7,0)

    for i in range(8, n-8):
        place(6, i, i%2^1); place(i, 6, i%2^1)

    for r in _ALIGN.get(version, []):
        for c in _ALIGN.get(version, []):
            if F[r][c]: continue
            for dr in range(-2,3):
                for dc in range(-2,3):
                    place(r+dr,c+dc,int(dr in(-2,2) or dc in(-2,2) or dr==dc==0))

    place(4*version+9, 8, 1)

    for i in range(9):
        F[8][i]=True; F[i][8]=True
    for i in range(n-8,n):
        F[8][i]=True; F[i][8]=True

    bits = []
    for cw in codewords:
        for b in range(7,-1,-1): bits.append((cw>>b)&1)

    col = n-1; going_up=True; bi=0
    while col > 0:
        if col==6: col-=1; continue
        rows = range(n-1,-1,-1) if going_up else range(n)
        for row in rows:
            for dc in [0,-1]:
                c = col+dc
                if not F[row][c]:
                    bit = bits[bi] if bi < len(bits) else 0
                    bi += 1
                    if (row//2 + c//3)%2==0: bit ^= 1
                    M[row][c] = bit
        going_up = not going_up
        col -= 2

    # Format (ECL M=00, mask=010=2) XOR mask 101010000010010
    fd = 0b00010
    rem = fd << 10
    g = 0x537
    for i in range(4,-1,-1):
        if rem & (1<<(i+10)): rem ^= g<<i
    fmt = ((fd<<10)|rem) ^ 0b101010000010010
    fb = [(fmt>>(14-i))&1 for i in range(15)]

    fi=0
    for i in [0,1,2,3,4,5,7,8]: M[i][8]=fb[fi]; fi+=1
    fi=0
    for i in [8,7,5,4,3,2,1,0]: M[8][i]=fb[fi]; fi+=1
    for i in range(7): M[n-1-i][8]=fb[i]
    for i in range(8): M[8][n-8+i]=fb[7+i]

    return M


def generate_svg(text: str, module_px: int = 6, quiet: int = 4) -> str:
    """Return an SVG string containing the QR code for *text*."""
    data = text.encode('iso-8859-1', errors='replace')

    version = dc = ec = blocks = None
    for v, d, e, bl in _QR_TABLE:
        if len(data) + 2 <= d:
            version, dc, ec, blocks = v, d, e, bl
            break
    if version is None:
        raise ValueError("Text too long for QR version ≤ 10")

    encoded = _encode_data(text, dc)
    codewords = _interleave(encoded, ec, blocks)
    mat = _make_matrix(version, codewords)
    n = len(mat)

    sz = (n + 2*quiet) * module_px
    rects = []
    for r in range(n):
        for c in range(n):
            if mat[r][c] == 1:
                x = (c+quiet)*module_px
                y = (r+quiet)*module_px
                rects.append(f'<rect x="{x}" y="{y}" width="{module_px}" height="{module_px}"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {sz} {sz}" width="{sz}" height="{sz}" '
            f'style="display:block;background:#ffffff;border-radius:8px">'
            f'<g fill="#000000">{"".join(rects)}</g>'
            f'</svg>')
