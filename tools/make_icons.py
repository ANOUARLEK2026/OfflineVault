#!/usr/bin/env python3
"""
Vault icon generator  --  "Abyss & Aurora"

Draws the launcher icon procedurally (signed-distance fields, so every density is
rendered natively and stays razor sharp instead of being down-scaled from one PNG).

    python3 tools/make_icons.py          # needs: numpy, scipy, pillow

Writes into icons/ :
  icon-1024.png                                  store / preview icon
  res/mipmap-*/ic_launcher.png                   legacy square icon   (Android < 8)
  res/mipmap-*/ic_launcher_round.png             legacy round icon
  res/mipmap-*/vault_bg.png / vault_fg.png       adaptive icon layers (Android 8+)
  res/mipmap-*/vault_mono.png                    themed-icon layer    (Android 13+)
  res/drawable-nodpi/vault_splash_logo.png       launch-screen logo

Change the palette in the CONFIG block and re-run.
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

# ----------------------------------------------------------------- CONFIG
TEAL   = np.array([52, 229, 208], np.float32)    # #34E5D0  signal
BLUE   = np.array([90, 162, 255], np.float32)    # #5AA2FF  refraction
VIOLET = np.array([165, 139, 255], np.float32)   # #A58BFF  depth
GLOW   = np.array([34, 230, 208], np.float32)    # keyhole light
GLOW2  = np.array([124, 92, 255], np.float32)    # wide violet bloom
BG_TOP = np.array([15, 22, 48], np.float32)      # #0F1630
BG_BOT = np.array([5, 8, 20], np.float32)        # #050814

C = 512.0                                        # canvas is 1024 world units
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "icons")


# ----------------------------------------------------------------- helpers
def grid(size, span=1024.0, origin=0.0):
    px = span / size
    ax = origin + (np.arange(size, dtype=np.float32) + 0.5) * px
    X, Y = np.meshgrid(ax, ax)
    return X, Y, px


def cov(d, px):
    """signed distance (world units) -> anti-aliased coverage 0..1"""
    return np.clip(0.5 - d / px, 0.0, 1.0).astype(np.float32)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def seg_dist(X, Y, a, b):
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    t = np.clip(((X - ax) * vx + (Y - ay) * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(X - (ax + t * vx), Y - (ay + t * vy))


def convex_poly_sdf(X, Y, pts):
    """exact SDF of a convex polygon given counter-clockwise-or-clockwise pts"""
    n = len(pts)
    d = np.full(X.shape, 1e9, np.float32)
    inside = np.ones(X.shape, bool)
    # orientation
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        d = np.minimum(d, seg_dist(X, Y, a, b))
        cross = (b[0] - a[0]) * (Y - a[1]) - (b[1] - a[1]) * (X - a[0])
        inside &= (sgn * cross) >= 0
    return np.where(inside, -d, d)


def grad3(t):
    """teal -> blue -> violet, t in 0..1 (array) -> (...,3)"""
    t = np.clip(t, 0, 1)[..., None]
    lo = TEAL + (BLUE - TEAL) * np.clip(t * 2, 0, 1)
    hi = BLUE + (VIOLET - BLUE) * np.clip(t * 2 - 1, 0, 1)
    return np.where(t < 0.5, lo, hi)


class Canvas:
    """premultiplied-alpha float canvas"""

    def __init__(self, n):
        self.rgb = np.zeros((n, n, 3), np.float32)
        self.a = np.zeros((n, n), np.float32)

    def over(self, color, alpha):
        alpha = np.clip(alpha, 0, 1).astype(np.float32)
        color = np.broadcast_to(np.asarray(color, np.float32), self.rgb.shape)
        self.rgb = color * alpha[..., None] + self.rgb * (1 - alpha[..., None])
        self.a = alpha + self.a * (1 - alpha)

    def composite_on(self, other):
        """self over other -> new Canvas"""
        out = Canvas(self.a.shape[0])
        out.rgb = self.rgb + other.rgb * (1 - self.a[..., None])
        out.a = self.a + other.a * (1 - self.a)
        return out

    def to_image(self):
        a = np.clip(self.a, 1e-6, 1)[..., None]
        rgb = np.clip(self.rgb / a, 0, 255)
        out = np.dstack([rgb, np.clip(self.a, 0, 1)[..., None] * 255])
        return Image.fromarray(np.round(out).astype(np.uint8), "RGBA")


# ----------------------------------------------------------------- layers
def background(size, span=1024.0, origin=0.0):
    X, Y, px = grid(size, span, origin)
    t = np.clip(Y / 1024.0, 0, 1)[..., None]
    base = BG_TOP + (BG_BOT - BG_TOP) * t
    cv = Canvas(size)
    cv.rgb = base.astype(np.float32)
    cv.a[:] = 1.0

    def blob(cx, cy, r, col, amt):
        d = np.hypot(X - cx, Y - cy) / r
        a = np.clip(1 - d, 0, 1) ** 2 * amt
        cv.rgb = np.array(col, np.float32) * a[..., None] + cv.rgb * (1 - a[..., None])

    blob(820, 210, 560, GLOW2, 0.62)     # violet, upper right
    blob(210, 850, 560, GLOW, 0.46)      # teal,   lower left
    blob(512, 512, 430, (60, 90, 190), 0.20)  # lift behind the lens
    rng = np.random.default_rng(7)       # tiny dither: no banding in the dark gradient
    cv.rgb += rng.uniform(-0.6, 0.6, cv.rgb.shape).astype(np.float32)
    return cv


def mark(size, span=1024.0, origin=0.0, scale=1.0, mono=False):
    """the vault dial: gradient ring + bead, frosted lens, glowing keyhole"""
    X, Y, px = grid(size, span, origin)
    # scale the mark about the canvas centre
    X = C + (X - C) / scale
    Y = C + (Y - C) / scale
    px = px / scale
    cv = Canvas(size)
    dx, dy = X - C, Y - C
    r = np.hypot(dx, dy)

    RING_R, RING_T = 268.0, 40.0
    ring_d = np.abs(r - RING_R) - RING_T / 2
    ring = cov(ring_d, px)
    u = (dx + dy) / np.sqrt(2)
    tg = (u / RING_R + 1) / 2
    ring_col = grad3(tg)

    # bead on the ring at 12 o'clock
    bead_d = np.hypot(X - C, Y - (C - RING_R)) - 25
    bead = cov(bead_d, px)

    # keyhole (circle + tapered stem, smooth-unioned)
    KCY, KR = 447.0, 58.0
    circ = np.hypot(X - C, Y - KCY) - KR
    rr = 9.0
    stem = convex_poly_sdf(X, Y, [(C - 22, KCY), (C + 22, KCY), (C + 47, 626 - rr), (C - 47, 626 - rr)]) - rr
    key_d = smin(circ, stem, 26.0)
    key = cov(key_d, px)

    if mono:
        # themed icon: one flat shape set, the system tints it
        a = np.maximum.reduce([ring, bead, key])
        cv.over((255, 255, 255), a)
        return cv

    sg = lambda m, s: gaussian_filter(m, s / px)

    # soft halo around the ring
    cv.over(BLUE, sg(ring, 36) * 0.30)

    # frosted lens: cool-tinted glass, lit from the inside by the keyhole
    DISC_R = 206.0
    disc = cov(r - DISC_R, px)
    tdisc = np.clip((u / DISC_R + 1) / 2, 0, 1)
    GLASS = (178, 208, 255)
    cv.over(GLASS, disc * (0.17 - 0.11 * tdisc))
    lit = np.clip(1 - np.hypot(X - C, Y - 500) / 230.0, 0, 1) ** 1.6
    cv.over(GLOW, disc * lit * 0.30)
    rim = cov(np.abs(r - DISC_R) - 2.2, px)
    cv.over((235, 244, 255), rim * (0.62 - 0.50 * tdisc))
    # crescent highlight, top-left (feathered)
    inner = cov(r - (DISC_R - 14), px)
    off = cov(np.hypot(X - (C + 26), Y - (C + 34)) - (DISC_R - 14), px)
    cres = gaussian_filter(np.clip(inner - off, 0, 1), 2.2 / px)
    cv.over((255, 255, 255), cres * 0.22)

    # light leaking out of the keyhole
    cv.over(GLOW2, sg(key, 95) * 0.60)
    cv.over(GLOW, sg(key, 40) * 1.0)
    cv.over(GLOW, sg(key, 14) * 0.60)

    # keyhole body: white-hot core fading to aqua
    ty = np.clip((Y - (KCY - KR)) / (626 - (KCY - KR)), 0, 1)[..., None]
    top, mid, bot = np.array([246, 255, 253], np.float32), np.array([150, 250, 236], np.float32), np.array([52, 224, 205], np.float32)
    kcol = np.where(ty < 0.45, top + (mid - top) * (ty / 0.45), mid + (bot - mid) * ((ty - 0.45) / 0.55))
    cv.over(kcol, key)

    # ticks between ring and lens (fine dial scale)
    N = 48
    th = np.arctan2(dy, dx)
    step = 2 * np.pi / N
    k = np.round(th / step)
    thl = th - k * step
    q0 = r * np.cos(thl) - 232.0
    q1 = r * np.sin(thl)
    half_len, wid = 8.0, 2.6
    tick_d = np.hypot(np.maximum(np.abs(q0) - (half_len - wid), 0), q1) - wid
    cv.over(ring_col, cov(tick_d, px) * 0.55)

    # ring + bead on top
    cv.over(ring_col, ring)
    cv.over(GLOW, sg(bead, 20) * 0.85)
    cv.over((255, 255, 255), bead)
    return cv



# ----------------------------------------------------------------- shapes / export
def rounded_square_mask(size, radius_frac=0.2237):
    X, Y, px = grid(size)
    h = 512.0
    rr = radius_frac * 1024
    qx, qy = np.abs(X - C) - (h - rr), np.abs(Y - C) - (h - rr)
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rr
    return cov(d, px)


def circle_mask(size):
    X, Y, px = grid(size)
    return cov(np.hypot(X - C, Y - C) - 512.0, px)


def legacy(size, shape, scale):
    bg = background(size)
    fg = mark(size, scale=scale)
    cv = fg.composite_on(bg)
    mask = rounded_square_mask(size) if shape == "square" else circle_mask(size)
    cv.rgb *= mask[..., None]
    cv.a = cv.a * mask
    # inner hairline
    X, Y, px = grid(size)
    if shape == "square":
        h, rr = 512.0, 0.2237 * 1024
        qx, qy = np.abs(X - C) - (h - rr), np.abs(Y - C) - (h - rr)
        d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rr
    else:
        d = np.hypot(X - C, Y - C) - 512.0
    ln = cov(np.abs(d + 3.5) - 1.6, px) * mask
    top_bias = np.clip(1.2 - Y / 700.0, 0.15, 1.0)
    cv.over((255, 255, 255), ln * 0.16 * top_bias)
    return cv.to_image()


def main():
    dens = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}
    for name, m in dens.items():
        d = os.path.join(OUT, "res", f"mipmap-{name}")
        os.makedirs(d, exist_ok=True)
        s_leg, s_ad = int(round(48 * m)), int(round(108 * m))
        legacy(s_leg, "square", 1.10).save(os.path.join(d, "ic_launcher.png"))
        legacy(s_leg, "round", 0.98).save(os.path.join(d, "ic_launcher_round.png"))
        # adaptive layers cover 108dp; the safe zone is the centre 66dp, mark fits inside it
        background(s_ad).to_image().convert("RGB").save(os.path.join(d, "vault_bg.png"))
        mark(s_ad, scale=0.98).to_image().save(os.path.join(d, "vault_fg.png"))
        mark(s_ad, scale=0.98, mono=True).to_image().save(os.path.join(d, "vault_mono.png"))
        print("mipmap-" + name, s_leg, s_ad)
    # store / preview
    legacy(1024, "square", 1.10).save(os.path.join(OUT, "icon-1024.png"))
    # launch-screen logo: just the mark, framed tight, single density
    nd = os.path.join(OUT, "res", "drawable-nodpi")
    os.makedirs(nd, exist_ok=True)
    mark(512, span=760.0, origin=C - 380.0).to_image().save(os.path.join(nd, "vault_splash_logo.png"))
    print("done")


if __name__ == "__main__":
    main()
