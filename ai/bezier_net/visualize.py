"""HTML visualizer for the synthetic data and the model.

    uv run python -m bezier_net.visualize -o viz.html [--mask mask.png] [--tol 1]

Sections:
  Data   - one row per noise mode: mask, traced contour, ground-truth path with handles.
  Model  - every slot (opacity = keep probability), raw network path, refined path vs ground truth.
  Mask   - (with --mask) fitted paths over your mask with anchors, handles and corners.
"""
import argparse
import base64
import io
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from .data import NOISE_MODES, contour_to_input, random_path, render_noisy, signed_area, trace
from .model import assemble
from .predict import load_model, mask_contours, predict_contour

GT, RAW, FIT, CONTOUR, HANDLE = "#1a9e4b", "#2b6cff", "#8a2be2", "#e5484d", "#f08c00"


def png_b64(mask):
    buf = io.BytesIO()
    Image.fromarray((~mask).astype(np.uint8) * 255).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def image_layer(mask, opacity=0.25):
    h, w = mask.shape
    return f'<image href="data:image/png;base64,{png_b64(mask)}" width="{w}" height="{h}" opacity="{opacity}"/>'


def contour_layer(c, color=CONTOUR, fill="none", dash=True):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in c)
    d = ' stroke-dasharray="3 3"' if dash else ""
    return f'<polygon points="{pts}" fill="{fill}" stroke="{color}" stroke-width="1"{d} vector-effect="non-scaling-stroke"/>'


def path_d(A, O, I):
    nxt, inn_next = np.roll(A, -1, 0), np.roll(I, -1, 0)
    d = [f"M {A[0,0]:.2f} {A[0,1]:.2f}"]
    for a, b, c in zip(A + O, nxt + inn_next, nxt):
        d.append(f"C {a[0]:.2f} {a[1]:.2f} {b[0]:.2f} {b[1]:.2f} {c[0]:.2f} {c[1]:.2f}")
    return " ".join(d) + " Z"


def corner_flags(O, I, min_angle=20):
    """Anchor is a corner when its in/out handles are not collinear."""
    cos = (O * -I).sum(1) / (np.linalg.norm(O, axis=1) * np.linalg.norm(I, axis=1) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1, 1))) > min_angle


def path_layer(A, O, I, color, r, handles=True, width=2):
    out = [f'<path d="{path_d(A, O, I)}" fill="none" stroke="{color}" stroke-width="{width}" vector-effect="non-scaling-stroke"/>']
    if handles:
        for p, h in [(A, A + O), (A, A + I)]:
            for (x0, y0), (x1, y1) in zip(p, h):
                out.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{HANDLE}" stroke-width="1" vector-effect="non-scaling-stroke"/>')
                out.append(f'<circle cx="{x1:.2f}" cy="{y1:.2f}" r="{r * 0.5:.2f}" fill="{HANDLE}"/>')
    for (x, y), corner in zip(A, corner_flags(O, I)):
        if corner:  # square = corner, circle = smooth anchor
            out.append(f'<rect x="{x - r:.2f}" y="{y - r:.2f}" width="{2 * r:.2f}" height="{2 * r:.2f}" fill="{color}"/>')
        else:
            out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{color}"/>')
    return "".join(out)


def cell(w, h, layers, caption):
    return (
        f'<figure><svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{"".join(layers)}</svg>'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def sample(rng, mode):
    while True:
        P, O, I = random_path(rng)
        mask, scale, off = render_noisy(P, O, I, rng, mode)
        c = trace(mask)
        if c is not None:
            return mask, c, (P * scale + off, O * scale, I * scale)


def data_section(rng, per_row):
    rows = []
    for m, name in enumerate(NOISE_MODES):
        cells = []
        for _ in range(per_row):
            mask, c, gt = sample(rng, m)
            s = mask.shape[0]
            layers = [image_layer(mask), contour_layer(c), path_layer(*gt, GT, s / 90)]
            cells.append(cell(s, s, layers, f"{s}px · {len(gt[0])} segments · {len(c)} contour pts"))
        rows.append(f'<h3>{name}</h3><div class="row">{"".join(cells)}</div>')
    return "".join(rows)


def model_section(model, rng, n, tol):
    blocks = []
    for i in range(n):
        mask, c, gt = sample(rng, i % len(NOISE_MODES))
        s = mask.shape[0]
        r = s / 90
        feats, center, extent = contour_to_input(c)
        x = torch.from_numpy(feats)[None]
        with torch.no_grad():
            pred = {k: v[0] for k, v in model(x).items()}
        keep = torch.sigmoid(pred["keep"]).numpy()
        slots = pred["anchors"].numpy() * extent + center
        dots = []
        for k, ((sx, sy), p) in enumerate(zip(slots, keep)):
            col = RAW if p > 0.5 else "#888"
            dots.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{r * 1.2:.2f}" fill="{col}" opacity="{max(p, 0.15):.2f}"/>')
            dots.append(f'<text x="{sx + r * 1.5:.2f}" y="{sy:.2f}" font-size="{r * 2.2:.2f}" fill="{col}">{k}:{p:.0%}</text>')
        A, O, I = (t.numpy() for t in assemble(pred, x[0, :, :2]))
        raw = (A * extent + center, O * extent, I * extent)
        fit = predict_contour(model, c, 1, tol)
        grey = contour_layer(c, "#bbb", "#f2f2f2", dash=False)
        cells = [
            cell(s, s, [grey, *dots], f"16 slots · opacity = keep · kept {int((keep > 0.5).sum())}"),
            cell(s, s, [grey, path_layer(*gt, GT, r, handles=False), path_layer(*raw, RAW, r)],
                 f"network: {len(raw[0])} segs vs true {len(gt[0])}"),
            cell(s, s, [grey, path_layer(*gt, GT, r, handles=False), path_layer(*fit, FIT, r)],
                 f"refined (tol {tol}px): {len(fit[0])} segs"),
        ]
        blocks.append(f'<h3>sample {i} · {NOISE_MODES[i % len(NOISE_MODES)]}</h3><div class="row">{"".join(cells)}</div>')
    return "".join(blocks)


def mask_section(model, path, tol):
    mask = np.asarray(Image.open(path).convert("L")) > 127
    border = np.concatenate([mask[0], mask[-1], mask[:, 0], mask[:, -1]])
    if border.mean() > 0.5:
        mask = ~mask
    h, w = mask.shape
    r = max(w, h) / 300
    layers, segs, corners = [image_layer(mask, 0.2)], 0, 0
    for c in mask_contours(mask):
        A, O, I = predict_contour(model, c, 1, tol)
        layers.append(path_layer(A, O, I, FIT, r, width=1.5))
        segs += len(A)
        corners += int(corner_flags(O, I).sum())
    caption = f"{path.name} · {segs} segments · {corners} corners · tol {tol}px"
    return f'<div class="big">{cell(w, h, layers, caption)}</div>'


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>BezierNet Visualizer</title>
<style>
:root {{ --bg:#fafafa; --fg:#222; --card:#fff; --muted:#666; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#16161a; --fg:#eee; --card:#222228; --muted:#aaa; }} }}
body {{ font-family: system-ui, sans-serif; background:var(--bg); color:var(--fg); margin:0 auto; padding:16px; max-width:1400px; }}
h2 {{ border-bottom:1px solid var(--muted); padding-bottom:4px; margin-top:32px; }}
h3 {{ margin:16px 0 6px; font-weight:500; color:var(--muted); }}
.row {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:12px; }}
figure {{ margin:0; background:var(--card); border-radius:8px; padding:8px; }}
svg {{ width:100%; height:auto; display:block; background:#fff; border-radius:4px; }}
figcaption {{ font-size:12px; color:var(--muted); margin-top:6px; }}
.big figure {{ max-width:900px; }}
.legend span {{ display:inline-block; margin-right:16px; font-size:13px; }}
.legend i {{ display:inline-block; width:14px; height:4px; vertical-align:middle; margin-right:5px; }}
</style></head><body>
<h1>BezierNet Visualizer</h1>
<div class="legend">
<span><i style="background:{GT}"></i>true path</span><span><i style="background:{RAW}"></i>network</span>
<span><i style="background:{FIT}"></i>refined</span><span><i style="background:{CONTOUR}"></i>traced contour</span>
<span><i style="background:{HANDLE}"></i>handles</span><span>■ corner &nbsp; ● smooth anchor</span>
</div>
{body}
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", type=Path, default=Path("viz.html"))
    ap.add_argument("--model", type=Path, default=Path("checkpoints/bezier_net.pt"))
    ap.add_argument("--mask", type=Path, help="also visualize the fit on this mask image")
    ap.add_argument("--tol", type=float, default=1.0)
    ap.add_argument("--samples", type=int, default=4, help="data samples per noise mode / model samples")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    model = load_model(args.model)
    rng = np.random.default_rng(args.seed)
    body = "<h2>Data · synthetic paths + noise</h2>" + data_section(rng, args.samples)
    body += "<h2>Model · slots → network path → refined path</h2>" + model_section(model, rng, args.samples, args.tol)
    if args.mask:
        body += "<h2>Your mask</h2>" + mask_section(model, args.mask, args.tol)
    args.out.write_text(PAGE.format(body=body, GT=GT, RAW=RAW, FIT=FIT, CONTOUR=CONTOUR, HANDLE=HANDLE))
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
