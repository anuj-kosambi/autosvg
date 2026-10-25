"""Mask image -> SVG of predicted Bézier paths.

    uv run python -m bezier_net.predict mask.png -o out.svg [--refine 30]
    uv run python -m bezier_net.predict --demo 8 -o demo/   # synthetic samples: GT vs predicted
"""
import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from skimage.measure import find_contours

from .data import contour_to_input, resample, make_sample, render_noisy, random_path, signed_area, to_svg_d, trace
from .model import BezierNet, assemble


def predict_contour(model, contour, refine=0, tol=1.0):
    """Pixel-space contour (m,2) -> pixel-space anchors, out, inn as numpy.

    refine=0: raw network output. refine>0: the network anchors plus detected corners become
    breakpoints; each piece gets a least-squares cubic, split at its worst point until within tol,
    then anchors that are not needed are merged away.
    """
    if signed_area(contour) < 0:  # model trained on positive-area contours; evenodd fill ignores direction
        contour = contour[::-1]
    feats, center, extent = contour_to_input(contour)
    x = torch.from_numpy(feats)[None]
    with torch.no_grad():
        pred = {k: v[0] for k, v in model(x).items()}
    A, O, I = (t.numpy() for t in assemble(pred, x[0, :, :2]))
    A, O, I = A * extent + center, O * extent, I * extent
    if not refine:
        return A, O, I

    X = resample(contour, max(256, len(contour)))  # ~1px spacing
    corners = find_corners(X)
    X = smooth_between(X, corners, sigma=2.0)  # removes pixel staircase, keeps corners sharp
    M = len(X)
    net = np.linalg.norm(A[:, None] - X[None], axis=2).argmin(1)
    near_corner = lambda i: len(corners) and np.min(np.minimum((corners - i) % M, (i - corners) % M)) <= 3
    breaks = np.unique(np.concatenate([corners, [i for i in net if not near_corner(i)]])).astype(int)

    # rotate so the first breakpoint is index 0; R stays cyclic, Xe closes the loop
    b0 = breaks[0]
    R = np.roll(X, -b0, 0)
    corner_set = set(((np.asarray(corners, dtype=int) - b0) % M).tolist())
    return fit_loop(R, (breaks - b0) % M, corner_set, tol)


def tangent(R, i, k=3):
    M = len(R)
    return unit(R[(i + k) % M] - R[(i - k) % M])


def fit_loop(R, breaks, corner_set, tol):
    """Fit every breakpoint-to-breakpoint piece of the closed contour R, then merge unneeded anchors."""
    M = len(R)
    Xe = np.concatenate([R, R[:1]])
    segs = []
    ends = list(breaks[1:]) + [M]
    for a, b in zip(breaks, ends):
        t0 = None if a in corner_set else tangent(R, a)
        tb = tangent(R, b % M)
        t3 = None if (b % M) in corner_set or tb is None else -tb
        fit_piece(Xe, R, a, b, t0, t3, tol, segs)
    idx = np.array([s[0] for s in segs])
    A = Xe[idx]
    O = np.array([s[1] for s in segs]) - A
    p2 = np.array([s[2] for s in segs])
    I = p2 - np.roll(A, -1, 0)  # p2 of segment k belongs to anchor k+1
    I = np.roll(I, 1, 0)
    keep = np.array([i in corner_set for i in idx])
    return merge_anchors(A, O, I, R, idx, keep, tol)


def fit_piece(Xe, R, i0, i1, t0, t3, tol, out):
    """Recursive cubic fit of Xe[i0..i1]; splits at the worst point with a shared (G1) tangent."""
    pts = Xe[i0 : i1 + 1]
    p0, p3 = Xe[i0], Xe[i1]
    if len(pts) < 4:
        out.append((i0, p0 + (p3 - p0) / 3, p3 - (p3 - p0) / 3))
        return
    p1, p2, err, worst = fit_cubic(pts, p0, p3, t0, t3)
    ok = well_formed(p0, p1, p2, p3)
    if (err <= tol and ok) or len(pts) < 8:
        if not ok:  # tiny piece that still loops: straight segment
            p1, p2 = p0 + (p3 - p0) / 3, p3 - (p3 - p0) / 3
        out.append((i0, p1, p2))
        return
    s = i0 + int(np.clip(worst, 3, len(pts) - 4))
    ts = tangent(R, s % len(R))
    fit_piece(Xe, R, i0, s, t0, None if ts is None else -ts, tol, out)
    fit_piece(Xe, R, s, i1, ts, t3, tol, out)


def smooth_closed(pts, sigma):
    """Circular Gaussian smoothing of a closed polyline."""
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    padded = np.concatenate([pts[-r:], pts, pts[:r]])
    return np.stack([np.convolve(padded[:, d], k, mode="valid") for d in range(2)], 1)


def find_corners(X, scales=(3, 6, 12), min_angle=45):
    """Union of corners found at several window sizes; small features need small windows."""
    found = np.concatenate([corners_at_scale(X, k, min_angle) for k in scales])
    if not len(found):
        return found
    found = np.unique(found)
    return found[np.concatenate([[True], np.diff(found) > 3])]


def corners_at_scale(X, k, min_angle):
    """Indices of sharp corners on a ~1px-spaced closed contour: turning angle over +-k points, local maxima."""
    v1 = X - np.roll(X, k, 0)
    v2 = np.roll(X, -k, 0) - X
    cos = (v1 * v2).sum(1) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1) + 1e-9)
    ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    windows = np.stack([np.roll(ang, s) for s in range(-k, k + 1)])
    peak = (ang >= windows.max(0)) & (ang > min_angle)
    idx = np.flatnonzero(peak)
    # plateaus can mark neighbours; keep the first of each run
    return idx[np.concatenate([[True], np.diff(idx) > k])] if len(idx) else idx


def smooth_between(X, corners, sigma):
    """Gaussian-smooth each corner-to-corner stretch separately; corner points stay fixed."""
    if len(corners) == 0:
        return smooth_closed(X, sigma)
    out = X.copy()
    r = int(3 * sigma)
    kern = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    kern /= kern.sum()
    M = len(X)
    for a, b in zip(corners, np.roll(corners, -1)):
        ids = (a + np.arange((b - a) % M or M) ) % M
        ids = np.append(ids, b)
        piece = X[ids]
        if len(piece) < r + 2:  # too short to smooth
            continue
        # odd reflection about the endpoints keeps them fixed and preserves end tangents
        pre = 2 * piece[0] - piece[1 : r + 1][::-1]
        post = 2 * piece[-1] - piece[-r - 1 : -1][::-1]
        padded = np.concatenate([pre, piece, post])
        sm = np.stack([np.convolve(padded[:, d], kern, mode="valid") for d in range(2)], 1)
        out[ids[1:-1]] = sm[1:-1]
    return out


def well_formed(p0, p1, p2, p3):
    """Handles point forward along the chord and are not longer than it (no loops/cusps)."""
    c = p3 - p0
    L = np.linalg.norm(c)
    return (
        np.dot(p1 - p0, c) >= 0 and np.dot(p2 - p3, -c) >= 0
        and np.linalg.norm(p1 - p0) <= L and np.linalg.norm(p2 - p3) <= L
    )


def fit_cubic(pts, p0, p3, t0=None, t3=None):
    """Least-squares inner control points for a cubic with fixed endpoints. Returns p1, p2, max error, worst index.

    If a unit tangent t0/t3 is given, that handle is restricted to p0 + a*t0 / p3 + b*t3 (keeps G1).
    """
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    t = np.concatenate([[0], np.cumsum(seg)]) / max(seg.sum(), 1e-9)
    for _ in range(3):  # fit, then re-project t onto the curve
        b = np.stack([(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3], 1)
        p1, p2 = solve_handles(pts, b, p0, p3, t0, t3)
        tt = np.linspace(0, 1, 129)[:, None]
        curve = (1 - tt) ** 3 * p0 + 3 * (1 - tt) ** 2 * tt * p1 + 3 * (1 - tt) * tt**2 * p2 + tt**3 * p3
        t = tt[np.linalg.norm(pts[:, None] - curve[None], axis=2).argmin(1), 0]
    d = np.linalg.norm(pts[:, None] - curve[None], axis=2).min(1)
    return p1, p2, d.max(), int(d.argmax())


def solve_handles(pts, b, p0, p3, t0, t3):
    """Linear least squares over the free handle parameters (2 per free handle, 1 per tangent-fixed one)."""
    rhs = (pts - np.outer(b[:, 0] + b[:, 1], p0) - np.outer(b[:, 2] + b[:, 3], p3)).reshape(-1)
    cols = []
    e = np.eye(2)
    h1 = [t0] if t0 is not None else [e[0], e[1]]
    h2 = [t3] if t3 is not None else [e[0], e[1]]
    for v in h1:
        cols.append(np.outer(b[:, 1], v).reshape(-1))
    for v in h2:
        cols.append(np.outer(b[:, 2], v).reshape(-1))
    coef, *_ = np.linalg.lstsq(np.stack(cols, 1), rhs, rcond=None)
    n1 = len(h1)
    p1 = p0 + sum(c * v for c, v in zip(coef[:n1], h1))
    p2 = p3 + sum(c * v for c, v in zip(coef[n1:], h2))
    return p1, p2


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else None


def merge_anchors(A, O, I, R, idx, keep, tol):
    """Greedily drop anchors whose two neighbouring segments can be replaced by one cubic within tol."""
    M = len(R)
    changed = True
    while changed and len(A) > 3:
        changed, k = False, 0
        while k < len(A) and len(A) > 3:
            a, b = (k - 1) % len(A), (k + 1) % len(A)
            if keep[k]:
                k += 1
                continue
            span = (idx[b] - idx[a]) % M or M
            pts = R[(idx[a] + np.arange(span + 1)) % M]
            # smooth endpoints keep their tangent so the merge cannot break G1
            t0 = None if keep[a] else (unit(O[a]) if unit(O[a]) is not None else unit(-I[a]))
            t3 = None if keep[b] else (unit(I[b]) if unit(I[b]) is not None else unit(-O[b]))
            p1, p2, err, _ = fit_cubic(pts, A[a], A[b], t0, t3)
            if err < tol and well_formed(A[a], p1, p2, A[b]):
                O[a], I[b] = p1 - A[a], p2 - A[b]
                A, O, I, idx, keep = (np.delete(v, k, 0) for v in (A, O, I, idx, keep))
                changed = True
            k += 1
    return A, O, I


def mask_contours(mask, min_len=16):
    """All contours (outer + holes) of a binary mask, in xy pixel coords."""
    cs = find_contours(np.pad(mask.astype(float), 1), 0.5)
    return [c[:, ::-1] - 1 for c in cs if len(c) >= min_len]


def load_model(path):
    model = BezierNet()
    model.load_state_dict(torch.load(path, map_location="cpu"))
    return model.eval()


def svg_doc(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n{body}\n</svg>\n'


def run_mask(model, path, out, refine, tol):
    mask = np.asarray(Image.open(path).convert("L")) > 127
    border = np.concatenate([mask[0], mask[-1], mask[:, 0], mask[:, -1]])
    if border.mean() > 0.5:  # light background -> shape is the dark part
        mask = ~mask
    h, w = mask.shape
    paths = [to_svg_d(*predict_contour(model, c, refine, tol)) for c in mask_contours(mask)]
    out.write_text(svg_doc(w, h, f'<path fill="black" fill-rule="evenodd" d="{" ".join(paths)}"/>'))
    print(f"{len(paths)} paths -> {out}")


def run_demo(model, n, out_dir, refine, tol):
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(777)
    for i in range(n):
        P, O, I = random_path(rng)
        mask, scale, off = render_noisy(P, O, I, rng)
        c = trace(mask)
        if c is None:
            continue
        A, PO, PI = predict_contour(model, c, refine, tol)
        size = mask.shape[0]
        Image.fromarray(mask.astype(np.uint8) * 255).save(out_dir / f"{i}_mask.png")
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in c)
        dots = "".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size/120:.2f}" fill="red"/>' for x, y in A)
        body = (
            f'<polygon points="{pts}" fill="#ddd"/>'
            f'<path d="{to_svg_d(P * scale + off, O * scale, I * scale)}" fill="none" stroke="green" stroke-width="{size/200:.2f}"/>'
            f'<path d="{to_svg_d(A, PO, PI)}" fill="none" stroke="blue" stroke-width="{size/200:.2f}"/>{dots}'
        )
        (out_dir / f"{i}_compare.svg").write_text(svg_doc(size, size, body))
        print(f"{i}: gt segments={len(P)} predicted={len(A)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mask", nargs="?", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--model", type=Path, default=Path("checkpoints/bezier_net.pt"))
    ap.add_argument("--refine", type=int, default=0, help=">0 enables fitting: network anchors + corners as breakpoints, split/merge to --tol")
    ap.add_argument("--tol", type=float, default=1.0, help="max px error per segment (with --refine)")
    ap.add_argument("--demo", type=int, help="render N synthetic GT-vs-predicted comparisons")
    args = ap.parse_args()
    model = load_model(args.model)
    if args.demo:
        run_demo(model, args.demo, args.out, args.refine, args.tol)
    else:
        run_mask(model, args.mask, args.out, args.refine, args.tol)


if __name__ == "__main__":
    main()
