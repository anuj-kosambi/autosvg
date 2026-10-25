"""Synthetic dataset: random closed SVG Bézier paths -> rendered mask -> noise -> traced contour.

Ground truth per anchor k (path is closed, CCW):
    anchor P_k, outgoing handle out_k = C1_k - P_k, incoming handle in_k = C2_{k-1} - P_k
Segment k = (P_k, P_k + out_k, P_{k+1} + in_{k+1}, P_{k+1}).
"""
import numpy as np
import torch
from PIL import Image, ImageFilter
from skimage.measure import find_contours

N_POINTS = 256
K_MAX = 16


def random_path(rng):
    """Random star-shaped closed path. Returns anchors (n,2), out (n,2), inn (n,2)."""
    n = int(rng.integers(3, 13))
    ang = np.sort(rng.uniform(0, 2 * np.pi, n))
    # enforce min angular gap so anchors don't collapse
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False) * 0.6 + ang * 0.4 + rng.uniform(0, 2 * np.pi)
    ang = np.sort(np.mod(ang, 2 * np.pi))
    r = rng.uniform(0.35, 1.0, n)
    P = np.stack([r * np.cos(ang), r * np.sin(ang)], 1) * [rng.uniform(0.6, 1.4), 1.0]

    nxt, prv = np.roll(P, -1, 0), np.roll(P, 1, 0)
    tangent = nxt - prv
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
    smooth = rng.random(n) < 0.5
    is_line = rng.random(n) < 0.3  # segment k (P_k -> P_{k+1}) is straight

    def rot(v, a):
        c, s = np.cos(a), np.sin(a)
        return np.stack([c * v[:, 0] - s * v[:, 1], s * v[:, 0] + c * v[:, 1]], 1)

    chord = nxt - P
    d = np.linalg.norm(chord, axis=1, keepdims=True)
    unit = chord / (d + 1e-9)
    out_dir = np.where(smooth[:, None], tangent, rot(unit, rng.uniform(-1, 1, n)))
    # incoming handle of anchor k+1 points backwards along its tangent
    in_dir_next = np.where(np.roll(smooth, -1)[:, None], -np.roll(tangent, -1, 0), rot(-unit, rng.uniform(-1, 1, n)))
    out = out_dir * d * rng.uniform(0.2, 0.45, (n, 1))
    in_next = in_dir_next * d * rng.uniform(0.2, 0.45, (n, 1))
    out = np.where(is_line[:, None], chord / 3, out)
    in_next = np.where(is_line[:, None], -chord / 3, in_next)
    inn = np.roll(in_next, 1, 0)
    return P, out, inn


def sample_path(P, out, inn, per_seg=64):
    nxt, inn_next = np.roll(P, -1, 0), np.roll(inn, -1, 0)
    t = np.linspace(0, 1, per_seg, endpoint=False)[:, None, None]
    p0, p1, p2, p3 = P, P + out, nxt + inn_next, nxt
    pts = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3
    return pts.transpose(1, 0, 2).reshape(-1, 2)


def to_svg_d(P, out, inn):
    nxt, inn_next = np.roll(P, -1, 0), np.roll(inn, -1, 0)
    d = [f"M {P[0,0]:.2f} {P[0,1]:.2f}"]
    for a, b, c in zip(P + out, nxt + inn_next, nxt):
        d.append(f"C {a[0]:.2f} {a[1]:.2f} {b[0]:.2f} {b[1]:.2f} {c[0]:.2f} {c[1]:.2f}")
    return " ".join(d) + " Z"


NOISE_MODES = ("clean", "blur", "segformer", "morph")


def render_noisy(P, out, inn, rng, mode=None):
    """Rasterize path, apply one noise model (random unless given), return binary mask + (scale, offset) used."""
    size = int(rng.integers(48, 257))
    scale = size * 0.4 / np.abs(np.concatenate([P, sample_path(P, out, inn, 8)])).max()
    ss = 4
    poly = sample_path(P, out, inn) * scale + size / 2
    img = Image.new("L", (size * ss, size * ss), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(img).polygon([tuple(p) for p in poly * ss], fill=255)
    img = img.resize((size, size), Image.LANCZOS)

    mode = rng.integers(0, 4) if mode is None else mode
    if mode == 1:  # soft edges
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.5, 2.0)))
    elif mode == 2:  # SegFormer-style: 1/4 resolution then bilinear upsample
        f = int(rng.integers(3, 6))
        img = img.resize((max(size // f, 4),) * 2, Image.BILINEAR).resize((size, size), Image.BILINEAR)
    elif mode == 3:  # morphological jitter
        img = img.point(lambda v: 255 * (v > 127))
        img = img.filter(ImageFilter.MaxFilter(3) if rng.random() < 0.5 else ImageFilter.MinFilter(3))
    mask = np.asarray(img) > 127
    if rng.random() < 0.3:  # edge pixel flips
        edge = np.asarray(img.filter(ImageFilter.FIND_EDGES)) > 0
        mask = mask ^ (edge & (rng.random(mask.shape) < 0.15))
    return mask, scale, size / 2


def trace(mask):
    """Largest closed contour of mask as (m,2) xy points, CCW (positive area)."""
    padded = np.pad(mask.astype(float), 1)
    cs = find_contours(padded, 0.5)
    if not cs:
        return None
    c = max(cs, key=len)[:, ::-1] - 1  # (row,col) -> (x,y)
    if len(c) < 8:
        return None
    if signed_area(c) < 0:
        c = c[::-1]
    return c


def signed_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def resample(c, n=N_POINTS):
    closed = np.concatenate([c, c[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.stack([np.interp(t, s, closed[:, 0]), np.interp(t, s, closed[:, 1])], 1)


def normalize(c):
    """Return normalized contour and (center, extent) to undo: x = xn * extent + center."""
    center = c.mean(0)
    extent = np.abs(c - center).max() + 1e-9
    return (c - center) / extent, center, extent


def features(pts):
    """(N,2) normalized points -> (N,5): x, y, tangent dx, dy, turning angle."""
    tan = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True) + 1e-9
    a = np.arctan2(tan[:, 1], tan[:, 0])
    turn = np.angle(np.exp(1j * (np.roll(a, -1) - a)))
    return np.concatenate([pts, tan, turn[:, None] * 4], 1).astype(np.float32)


def contour_to_input(contour):
    pts, center, extent = normalize(resample(contour))
    return features(pts), center, extent


def make_sample(rng):
    while True:
        P, out, inn = random_path(rng)
        mask, scale, off = render_noisy(P, out, inn, rng)
        # path drawn directly in pixel coords, so path and traced contour share orientation (positive area)
        c = trace(mask)
        if c is None:
            continue
        feats, center, extent = contour_to_input(c)
        to_n = lambda v: v * scale / extent
        Pn = (P * scale + off - center) / extent
        return {
            "x": feats,
            "anchors": Pn.astype(np.float32),
            "out": to_n(out).astype(np.float32),
            "inn": to_n(inn).astype(np.float32),
        }


class SyntheticPaths(torch.utils.data.IterableDataset):
    def __init__(self, seed=0):
        self.seed = seed

    def __iter__(self):
        info = torch.utils.data.get_worker_info()
        rng = np.random.default_rng([self.seed, info.id if info else 0])
        while True:
            yield make_sample(rng)


def collate(batch):
    x = torch.from_numpy(np.stack([b["x"] for b in batch]))
    gt = [{k: torch.from_numpy(b[k]) for k in ("anchors", "out", "inn")} for b in batch]
    return x, gt
