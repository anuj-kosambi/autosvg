"""Train BezierNet on synthetic paths.  uv run python -m bezier_net.train --steps 20000"""
import argparse
import time
from pathlib import Path

import numpy as np
import torch

from .data import SyntheticPaths, collate, make_sample
from .loss import chamfer, compute_loss, sample_bezier
from .model import BezierNet, assemble


@torch.no_grad()
def evaluate(model, val, device):
    """Inference-mode metrics: chamfer of assembled path to contour (normalized units), segment-count accuracy."""
    model.eval()
    x = torch.from_numpy(np.stack([s["x"] for s in val])).to(device)
    pred = model(x)
    dists, exact = [], 0
    for b, s in enumerate(val):
        p = {k: v[b] for k, v in pred.items()}
        A, O, I = assemble(p, x[b, :, :2])
        dists.append(chamfer(sample_bezier(A, O, I), x[b, :, :2]).item())
        exact += len(A) == len(s["anchors"])
    model.train()
    return float(np.mean(dists)), exact / len(val)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--out", type=Path, default=Path("checkpoints/bezier_net.pt"))
    args = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    loader = torch.utils.data.DataLoader(
        SyntheticPaths(seed=0), batch_size=args.batch, collate_fn=collate, num_workers=8, persistent_workers=True
    )
    rng = np.random.default_rng(12345)
    val = [make_sample(rng) for _ in range(512)]

    model = BezierNet().to(device)
    print(f"params: {sum(p.numel() for p in model.parameters()) / 1e3:.0f}k, device: {device}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, args.lr, total_steps=args.steps, pct_start=0.05)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    for step, (x, gt) in enumerate(loader, 1):
        x = x.to(device)
        loss, parts = compute_loss(model(x), gt, x[..., :2])
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        if step % 200 == 0:
            msg = " ".join(f"{k}={v.item():.4f}" for k, v in parts.items())
            print(f"step {step} loss={loss.item():.4f} {msg} ({time.time() - t0:.0f}s)", flush=True)
        if step % 2000 == 0 or step == args.steps:
            dist, acc = evaluate(model, val, device)
            print(f"  val chamfer={dist:.4f} count_acc={acc:.2%}", flush=True)
            torch.save(model.state_dict(), args.out)
        if step == args.steps:
            break


if __name__ == "__main__":
    main()
