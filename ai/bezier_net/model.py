"""Contour -> set of K_MAX anchor slots (anchor, out handle, in handle, keep logit)."""
import torch
from torch import nn

from .data import K_MAX


class CircularEncoder(nn.Module):
    def __init__(self, in_ch=5, d=64, layers=6):
        super().__init__()
        self.inp = nn.Conv1d(in_ch, d, 1)
        self.blocks = nn.ModuleList(
            nn.Sequential(
                nn.Conv1d(d, d, 5, padding=2 * 2**i, dilation=2**i, padding_mode="circular"),
                nn.GroupNorm(8, d),
                nn.GELU(),
            )
            for i in range(layers)
        )

    def forward(self, x):  # x: (B, N, C)
        h = self.inp(x.transpose(1, 2))
        for b in self.blocks:
            h = h + b(h)
        return h.transpose(1, 2)  # (B, N, d)


class BezierNet(nn.Module):
    def __init__(self, d=64, k=K_MAX):
        super().__init__()
        self.encoder = CircularEncoder(d=d)
        self.pos = nn.Linear(2, d)  # point xy embedding added to memory
        self.slots = nn.Parameter(torch.randn(k, d) * 0.02)
        layer = nn.TransformerDecoderLayer(d, 4, d * 4, dropout=0.0, batch_first=True, norm_first=True)
        self.decoder = nn.TransformerDecoder(layer, 3)
        self.head = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, 7))

    def forward(self, x):
        mem = self.encoder(x) + self.pos(x[..., :2])
        q = self.slots.expand(x.shape[0], -1, -1)
        o = self.head(self.decoder(q, mem))
        return {"anchors": o[..., 0:2], "out": o[..., 2:4], "inn": o[..., 4:6], "keep": o[..., 6]}


def assemble(pred, contour, threshold=0.5):
    """Pick kept slots of one sample, order them along the contour. Returns anchors, out, inn tensors."""
    keep = torch.sigmoid(pred["keep"]) > threshold
    if keep.sum() < 2:
        keep = torch.sigmoid(pred["keep"]).topk(3).indices
    A, O, I = pred["anchors"][keep], pred["out"][keep], pred["inn"][keep]
    order = torch.cdist(A, contour).argmin(1).argsort()
    return A[order], O[order], I[order]
