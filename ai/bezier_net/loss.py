"""Hungarian-matched slot loss + chamfer fit of the assembled path to the input contour."""
import torch
import torch.nn.functional as F
from scipy.optimize import linear_sum_assignment

T = torch.linspace(0, 1, 17)[:-1]


def sample_bezier(A, O, I):
    """Closed path from ordered anchors (n,2) -> (n*16, 2) points."""
    nxt, inn_next = A.roll(-1, 0), I.roll(-1, 0)
    t = T.to(A)[:, None, None]
    p = (1 - t) ** 3 * A + 3 * (1 - t) ** 2 * t * (A + O) + 3 * (1 - t) * t**2 * (nxt + inn_next) + t**3 * nxt
    return p.transpose(0, 1).reshape(-1, 2)


def chamfer(a, b):
    d = torch.cdist(a, b)
    return d.min(1).values.mean() + d.min(0).values.mean()


def compute_loss(pred, gt, contours):
    """pred: dict of (B,K,...) tensors; gt: list of dicts; contours: (B,N,2)."""
    B = len(gt)
    l_anchor = l_handle = l_fit = 0.0
    keep_target = torch.zeros_like(pred["keep"])
    for b in range(B):
        g = gt[b]
        ga = g["anchors"].to(pred["anchors"])
        cost = torch.cdist(pred["anchors"][b].detach(), ga).cpu().numpy()
        si, gi = linear_sum_assignment(cost)
        order = torch.as_tensor(gi).argsort()  # slots in GT path order
        si = torch.as_tensor(si)[order]
        keep_target[b, si] = 1
        A, O, I = pred["anchors"][b, si], pred["out"][b, si], pred["inn"][b, si]
        l_anchor = l_anchor + F.l1_loss(A, ga)
        l_handle = l_handle + F.l1_loss(O, g["out"].to(A)) + F.l1_loss(I, g["inn"].to(A))
        l_fit = l_fit + chamfer(sample_bezier(A, O, I), contours[b])
    l_keep = F.binary_cross_entropy_with_logits(pred["keep"], keep_target)
    parts = {"anchor": l_anchor / B, "handle": l_handle / B, "fit": l_fit / B, "keep": l_keep}
    total = 5 * parts["anchor"] + 2 * parts["handle"] + 2 * parts["fit"] + parts["keep"]
    return total, parts
