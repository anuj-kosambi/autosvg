# BezierNet

Small neural network (330k params) that turns a traced outline into a closed cubic Bézier path,
plus a fitter that snaps anchors to corners and keeps smooth joins G1.

Trained only on synthetic data: random closed SVG paths rendered to masks with noise
(clean / blur / SegFormer-style blocky edges / ±1px morph), traced back to contours.

## Usage

```
cd ai
uv run python -m bezier_net.predict mask.png -o out.svg --refine 1 --tol 1   # mask -> SVG
uv run python -m bezier_net.visualize -o viz.html --mask mask.png            # data + model visualizer
uv run python -m bezier_net.train --steps 20000                              # retrain
```

- Mask polarity is detected from the border (dark shape on light background works).
- `--refine` >0: corners + network anchors become breakpoints, least-squares cubic per piece,
  split at worst point until within `--tol` px, then redundant anchors are merged.
- `checkpoints/bezier_net.pt`: model trained 20k steps × batch 64 (1.28M synthetic samples).

## Files

| file | role |
|---|---|
| `bezier_net/data.py` | synthetic paths, rendering, noise, tracing, features |
| `bezier_net/model.py` | circular dilated Conv1d encoder + 16-slot transformer decoder |
| `bezier_net/loss.py` | Hungarian-matched anchor/handle L1, chamfer fit, keep BCE |
| `bezier_net/train.py` | training loop with periodic validation |
| `bezier_net/predict.py` | inference, corner detection, piecewise fitting, SVG output |
| `bezier_net/visualize.py` | HTML visualizer for data and model |
