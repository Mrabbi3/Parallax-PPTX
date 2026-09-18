#!/usr/bin/env python3
"""
generate_layers.py — build the three parallax planes for a deck.

Outputs into --out:
    pano.jpg    far plane   : colour panorama (pans slowly)
    mid.png     mid plane   : translucent botanical/abstract shapes (pans faster)
    bloom.png   near plane  : 3D-shaded cut-out subject (moves most)

The near plane is a real shaded render, not line art: every petal is a
parametric surface, meshed into quads, lit with diffuse + specular +
back-lit translucency + rim light, then depth-sorted and painted.

Usage
-----
    python3 generate_layers.py --out layers/
    python3 generate_layers.py --out layers/ --palette-from reference.jpg
    python3 generate_layers.py --out layers/ \
        --hues "0B4A5C,10635F,164C7E,32387E,5A2E7E,8A2C6A,AC3A58" \
        --bloom-in FFD868 --bloom-out F04C2E --petals 6

If --cutout is given, that PNG (must have alpha) is used as the near plane
instead of a generated bloom — use it when the person supplies a reference
image you have already cut out.
"""
import argparse, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def hex2rgb(h):
    h = h.strip().lstrip("#")
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        sys.exit("not a 6-digit hex colour: %r (expected e.g. 0B2E4F)" % h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n else v


def ramp(stops, n):
    xs = np.linspace(0, 1, n)
    out = np.zeros((n, 3))
    for c in range(3):
        out[:, c] = np.interp(xs, [s[0] for s in stops], [s[1][c] for s in stops])
    return out


def palette_from_image(path, k=7):
    """Pull an ordered colour ramp out of a reference image.

    Colours are sorted by hue so the panorama sweeps through them smoothly
    rather than jumping around."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((400, 400))
    q = im.quantize(colors=k * 3, method=Image.MEDIANCUT).convert("RGB")
    arr = np.asarray(q).reshape(-1, 3)
    cols, counts = np.unique(arr, axis=0, return_counts=True)
    order = np.argsort(-counts)
    picked = []
    for i in order:
        c = cols[i].astype(float)
        if c.max() < 26:                       # skip near-black
            continue
        if all(np.linalg.norm(c - np.array(p)) > 42 for p in picked):
            picked.append(tuple(c))
        if len(picked) == k:
            break
    while len(picked) < k:
        picked.append(picked[-1] if picked else (40, 70, 100))

    def hue(c):
        r, g, b = [x / 255.0 for x in c]
        mx, mn = max(r, g, b), min(r, g, b)
        d = mx - mn
        if d == 0:
            return 0.0
        if mx == r:
            return ((g - b) / d % 6) / 6
        if mx == g:
            return ((b - r) / d + 2) / 6
        return ((r - g) / d + 4) / 6

    picked.sort(key=hue)
    # deepen so cream type stays legible on top
    out = []
    for c in picked:
        c = np.array(c) * 0.62
        out.append(tuple(float(x) for x in np.clip(c, 8, 190)))
    return out


DEFAULT_HUES = ["0C485C", "106364", "164C7E", "323882", "5A2E7E", "8A2C6A", "AC3A58"]


# ----------------------------------------------------------------------
# far plane
# ----------------------------------------------------------------------
def build_pano(hues, W, H, seed=11):
    stops = [(i / (len(hues) - 1), c) for i, c in enumerate(hues)]
    base = ramp(stops, W)
    yy = np.linspace(0, 1, H)[:, None]
    field = np.repeat(base[None, :, :], H, axis=0)

    lift = ((1.0 - yy) ** 2.1 * 0.55)[:, :, None]
    deep = ((yy ** 2.6) * 0.44)[:, :, None]
    field = field * (1 - deep) + 255 * lift * 0.30
    field = field + (np.array([255, 214, 150]) - field) * (lift * 0.22)

    band = np.exp(-((yy - 0.46) ** 2) / (2 * 0.055 ** 2))[:, :, None]
    field = field + (np.array([255, 236, 205]) - field) * (band * 0.15)

    xg = np.arange(W)[None, :]
    ygp = np.arange(H)[:, None]
    rng = np.random.default_rng(seed)
    glow_cols = [(255, 196, 110), (255, 228, 176), (150, 214, 255),
                 (255, 176, 150), (255, 150, 176)]
    for i in range(5):
        cx = W * (0.11 + 0.195 * i)
        cy = H * float(rng.uniform(0.18, 0.40) + 0.1 * (i % 2))
        r = W * float(rng.uniform(0.09, 0.14))
        d = np.sqrt(((xg - cx) / r) ** 2 + ((ygp - cy) / (r * 0.75)) ** 2)
        g = (np.clip(1 - d, 0, 1) ** 2.0)[:, :, None]
        field = field + (np.array(glow_cols[i]) - field) * (g * float(rng.uniform(0.22, 0.40)))

    # slanted light shafts
    shaft = np.zeros((H, W))
    for _ in range(6):
        x0 = float(rng.uniform(0.12, 0.92)) * W
        wdt = float(rng.uniform(0.012, 0.035)) * W
        amp = float(rng.uniform(0.10, 0.20))
        sx = xg + (ygp - H * 0.5) * 0.55
        shaft += amp * np.exp(-((sx - x0) ** 2) / (2.0 * wdt ** 2))
    shaft *= (1.0 - yy * 0.45)
    field = field + (np.array([255, 244, 220]) - field) * np.clip(shaft, 0, 1)[:, :, None]

    field += rng.normal(0, 3.0, field.shape)
    pano = Image.fromarray(np.clip(field, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for i in range(6):
        cx = W * (0.09 + 0.17 * i)
        cy = H * (0.66 if i % 2 else 0.28)
        R = W * float(rng.uniform(0.075, 0.125))
        for k in range(int(rng.integers(6, 10))):
            a = k / 8 * 2 * math.pi + float(rng.uniform(0, 1))
            vd.line(petal_outline(cx, cy, a, R, R * 0.30),
                    fill=(255, 245, 230, int(rng.integers(20, 32))), width=5, joint="curve")
    for _ in range(int(W / 38)):
        bx, by = float(rng.integers(0, W)), float(rng.integers(0, H))
        br = float(rng.integers(5, 30))
        vd.ellipse([bx - br, by - br, bx + br, by + br],
                   fill=(255, 246, 228, int(rng.integers(14, 46))))
    veil = veil.filter(ImageFilter.GaussianBlur(1.6))
    return Image.alpha_composite(pano, veil).convert("RGB")


def petal_outline(cx, cy, ang, length, halfw, steps=54, curl=0.3):
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        w = math.pow(math.sin(math.pow(t, 0.60) * math.pi), 0.52) * halfw
        sweep = curl * math.sin(t * math.pi) * halfw * 0.5
        for side, store in ((-1, left), (1, right)):
            lx, ly = side * w + sweep, length * t
            store.append((cx + lx * math.cos(ang) - ly * math.sin(ang),
                          cy + lx * math.sin(ang) + ly * math.cos(ang)))
    return left + right[::-1] + [left[0]]


# ----------------------------------------------------------------------
# mid plane
# ----------------------------------------------------------------------
def build_mid(W, H, seed=19):
    mid = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    md = ImageDraw.Draw(mid)
    rng = np.random.default_rng(seed)
    n = max(10, int(W / 330))
    for k in range(n):
        cx = 160 + k * (W * 2 / n) + float(rng.integers(-140, 140))
        cy = float(rng.integers(int(H * 0.2), int(H * 1.8)))
        L = float(rng.integers(int(W * 0.13), int(W * 0.29)))
        ang = float(rng.uniform(-0.9, 0.9)) + (math.pi if k % 2 else 0)
        pts = petal_outline(cx, cy, ang, L, L * 0.30, curl=0.5)
        md.polygon(pts, fill=(255, 250, 240, 16))
        md.line(pts, fill=(255, 252, 244, 52), width=6, joint="curve")
    return mid.filter(ImageFilter.GaussianBlur(2.5)).resize((W, H), Image.LANCZOS)


# ----------------------------------------------------------------------
# near plane — shaded 3D bloom
# ----------------------------------------------------------------------
LIGHT = unit(np.array([-0.46, 0.40, 0.79]))
HALF = unit(LIGHT + np.array([0.0, 0.0, 1.0]))


def shade(nx, ny, nz, base_rgb):
    d = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
    diff = np.clip(d, 0, 1)
    back = np.clip(-d, 0, 1)
    spec = np.clip(nx * HALF[0] + ny * HALF[1] + nz * HALF[2], 0, 1) ** 46
    rim = (1.0 - np.clip(np.abs(nz), 0, 1)) ** 2.4
    lit = 0.52 + 0.68 * diff + 0.42 * back
    col = base_rgb * lit[..., None]
    col = col + (np.array([255, 250, 238]) - col) * (rim * 0.26)[..., None]
    col = col + np.array([255, 253, 246]) * (spec * 0.95)[..., None]
    return np.clip(col, 0, 255)


def rotx(P, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = P
    return (x, y * c - z * s, y * s + z * c)


def rotz(P, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = P
    return (x * c - y * s, x * s + y * c, z)


def normals(X, Y, Z):
    dxu, dxv = np.gradient(X)[1], np.gradient(X)[0]
    dyu, dyv = np.gradient(Y)[1], np.gradient(Y)[0]
    dzu, dzv = np.gradient(Z)[1], np.gradient(Z)[0]
    nx = dyu * dzv - dzu * dyv
    ny = dzu * dxv - dxu * dzv
    nz = dxu * dyv - dyu * dxv
    ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2) + 1e-9
    return nx / ln, ny / ln, nz / ln


def petal_surface(S, L, halfw, tilt, az, bend, cup, ruff, rf, twist, nu=50, nv=64):
    u = np.linspace(-1, 1, nu)
    v = np.linspace(0.02, 1.0, nv)
    U, V = np.meshgrid(u, v)
    w = halfw * np.sin(np.pi * V ** 0.60) ** 0.50
    X = U * w
    Y = L * V
    Z = (-bend * L * V ** 2 + cup * (X ** 2) / (halfw * 3.0)
         + ruff * L * np.sin(rf * np.pi * U) * V ** 2.2)
    if twist:
        a = twist * V
        Xr = X * np.cos(a) - Z * np.sin(a)
        Z = X * np.sin(a) + Z * np.cos(a)
        X = Xr
    return rotz(rotx((X, Y, Z), tilt), az)


def build_bloom(inner, outer, tip, petals=5, out_size=2000, S=3200, cam_deg=26):
    bloom = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    BC = S / 2
    CAM = math.radians(cam_deg)
    cells = []

    def emit(P, base_rgb, edge_col, edge_pow):
        X, Y, Z = P
        nx, ny, nz = normals(X, Y, Z)
        c, s = math.cos(CAM), math.sin(CAM)
        Yc, Zc = Y * c + Z * s, -Y * s + Z * c
        nyc, nzc = ny * c + nz * s, -ny * s + nz * c
        nv_, nu_ = X.shape
        Ug = np.linspace(-1, 1, nu_)[None, :] * np.ones((nv_, 1))
        Vg = np.linspace(0, 1, nv_)[:, None] * np.ones((1, nu_))
        m = np.clip(np.abs(Ug) ** edge_pow * 0.92 + Vg * 0.22, 0, 1)
        rgb_field = (np.array(base_rgb)[None, None, :] * (1 - m[..., None])
                     + np.array(edge_col)[None, None, :] * m[..., None])
        col = shade(nx, nyc, nzc, rgb_field)
        streak = (np.cos(8.0 * np.pi * Ug) * 0.5 + 0.5) ** 8
        col = col * (1 - 0.09 * streak)[..., None]
        sx, sy = BC + X, BC - Yc
        for j in range(X.shape[0] - 1):
            for i in range(X.shape[1] - 1):
                quad = [(sx[j, i], sy[j, i]), (sx[j, i + 1], sy[j, i + 1]),
                        (sx[j + 1, i + 1], sy[j + 1, i + 1]), (sx[j + 1, i], sy[j + 1, i])]
                d = (Zc[j, i] + Zc[j, i + 1] + Zc[j + 1, i + 1] + Zc[j + 1, i]) * 0.25
                rgb = (col[j, i] + col[j, i + 1] + col[j + 1, i + 1] + col[j + 1, i]) * 0.25
                cells.append((d, quad, tuple(int(x) for x in rgb)))

    for i in range(petals):
        az = i * (2 * math.pi / petals) + 0.35
        emit(petal_surface(S, S * 0.340, S * 0.132,
                           math.radians(30 + 6 * math.sin(i * 1.7)), az,
                           0.16, 0.30, 0.072, 3.5, 0.22 * (1 if i % 2 else -1)),
             inner, outer, 1.5)
    for i in range(petals):
        az = i * (2 * math.pi / petals) + 0.35 + math.pi / petals
        emit(petal_surface(S, S * 0.205, S * 0.092,
                           math.radians(22 + 5 * math.cos(i * 1.3)), az,
                           0.14, 0.26, 0.058, 4.5, -0.16),
             tuple(np.array(inner) * 0.96 + np.array(outer) * 0.04), tip, 1.9)

    cells.sort(key=lambda c: c[0])
    for _, quad, rgb in cells:
        bd.polygon(quad, fill=rgb + (255,))

    # stamens
    stam = []
    for i in range(petals * 2):
        a = i * (2 * math.pi / (petals * 2)) + 0.18
        reach = S * (0.40 + 0.07 * math.sin(i * 2.3))
        pts = []
        for t in np.linspace(0, 1, 34):
            r = reach * t
            pts.append((BC + math.cos(a) * r,
                        BC - math.sin(a) * r * math.cos(CAM) - math.sin(t * math.pi) * S * 0.055))
        stam.append(pts)
    dark = tuple(int(x * 0.45) for x in outer)
    for pts in stam:
        bd.line(pts, fill=dark + (150,), width=10, joint="curve")
    for pts in stam:
        bd.line(pts, fill=tuple(int(x) for x in outer) + (255,), width=7, joint="curve")
        bd.line([(x, y - 2) for x, y in pts], fill=(255, 148, 120, 190), width=3, joint="curve")
        ax, ay = pts[-1]
        bd.ellipse([ax - 21, ay - 14, ax + 21, ay + 14], fill=dark + (255,))
        bd.ellipse([ax - 13, ay - 9, ax + 6, ay + 2], fill=(226, 172, 96, 235))

    for rr, col, al in [(S * 0.058, (255, 168, 64), 120), (S * 0.038, (255, 212, 110), 215),
                        (S * 0.020, (255, 250, 226), 255)]:
        bd.ellipse([BC - rr, BC - rr * 0.84, BC + rr, BC + rr * 0.84], fill=col + (al,))

    return add_halo(bloom).resize((out_size, out_size), Image.LANCZOS)


def add_halo(layer, blur=30, strength=0.85, rgb=(10, 16, 34)):
    """Dark separation halo so the cut-out reads on any part of the panorama."""
    a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(blur))
    a = a.point(lambda v: min(255, int(v * strength)))
    halo = Image.new("RGBA", layer.size, rgb + (0,))
    halo.putalpha(a)
    return Image.alpha_composite(halo, layer)


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--palette-from", help="reference image; the panorama is built from its colours")
    ap.add_argument("--hues", help="comma-separated hex stops, left to right")
    ap.add_argument("--bloom-in", default="FFD868")
    ap.add_argument("--bloom-out", default="F04C2E")
    ap.add_argument("--bloom-tip", default="D6283A")
    ap.add_argument("--petals", type=int, default=5)
    ap.add_argument("--cutout", help="use this RGBA png as the near plane instead of a bloom")
    ap.add_argument("--pano-width", type=int, default=7200)
    ap.add_argument("--pano-height", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)

    for label, given in (("--palette-from", a.palette_from), ("--cutout", a.cutout)):
        if given and not os.path.exists(given):
            sys.exit("no such file for %s: %s" % (label, given))

    if a.hues:
        hues = [hex2rgb(h) for h in a.hues.split(",")]
    elif a.palette_from:
        hues = palette_from_image(a.palette_from)
        print("palette from image:", ["#%02X%02X%02X" % tuple(int(c) for c in h) for h in hues])
    else:
        hues = [hex2rgb(h) for h in DEFAULT_HUES]

    pano = build_pano(hues, a.pano_width, a.pano_height, a.seed)
    pano.save(os.path.join(a.out, "pano.jpg"), quality=88)
    print("pano", pano.size)

    mid = build_mid(int(a.pano_width * 0.72), a.pano_height, a.seed + 8)
    mid.save(os.path.join(a.out, "mid.png"))
    print("mid", mid.size)

    if a.cutout:
        cut = Image.open(a.cutout).convert("RGBA")
        if cut.getchannel("A").getextrema()[0] == 255:
            print("WARNING: --cutout has no transparency; the near plane will be a rectangle.",
                  file=sys.stderr)
        add_halo(cut).save(os.path.join(a.out, "bloom.png"))
        print("bloom (from cutout)", cut.size)
    else:
        bloom = build_bloom(hex2rgb(a.bloom_in), hex2rgb(a.bloom_out),
                            hex2rgb(a.bloom_tip), petals=a.petals)
        bloom.save(os.path.join(a.out, "bloom.png"))
        print("bloom", bloom.size)

    meta = {"hues": ["#%02X%02X%02X" % tuple(int(c) for c in h) for h in hues],
            "pano": [a.pano_width, a.pano_height]}
    with open(os.path.join(a.out, "layers.json"), "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
