"""Principal component analysis and k-means clustering of trajectory frames."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adit.analysis.geometry_series import kabsch_rmsd


@dataclass
class PcaResult:
    components: np.ndarray       # (n_components, 3 * n_atoms)
    projections: np.ndarray      # (n_frames, n_components)
    variance: np.ndarray
    explained: np.ndarray
    mean: np.ndarray


@dataclass
class ClusterResult:
    labels: np.ndarray
    sizes: np.ndarray
    centers: np.ndarray
    representative: np.ndarray
    inertia: float


def _aligned(coords: np.ndarray) -> np.ndarray:
    ref = coords[0]
    center = ref.mean(axis=0)
    out = np.empty_like(coords)
    out[0] = ref - center
    for i in range(1, coords.shape[0]):
        _, rotated = kabsch_rmsd(ref, coords[i])
        out[i] = rotated - center
    return out


def pca(coords, n_components: int = 3, align: bool = True) -> PcaResult:
    """Principal components of coordinates with shape (frames, atoms, 3)."""
    x = np.asarray(coords, dtype=float)
    if x.ndim != 3 or x.shape[2] != 3:
        raise ValueError("coords は (フレーム, 原子, 3) にしてください")
    if x.shape[0] < 3:
        raise ValueError("主成分分析には 3 フレーム以上が要ります")
    if align:
        x = _aligned(x)
    flat = x.reshape(x.shape[0], -1)
    mean = flat.mean(axis=0)
    centered = flat - mean
    n_components = min(n_components, min(centered.shape) - 1)
    if n_components < 1:
        raise ValueError("成分の数が 1 未満になります (フレームか原子が少なすぎます)")
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    var = s ** 2 / (centered.shape[0] - 1)
    return PcaResult(vt[:n_components], (u[:, :n_components] * s[:n_components]),
                     var[:n_components], var[:n_components] / var.sum(), mean)


def kmeans(points, k: int, iterations: int = 100, seed: int = 0) -> ClusterResult:
    x = np.asarray(points, dtype=float)
    if x.ndim != 2:
        raise ValueError("points は (点, 次元) にしてください")
    if not 1 <= k <= x.shape[0]:
        raise ValueError(f"群の数 k は 1 以上 {x.shape[0]} 以下にしてください")
    rng = np.random.default_rng(seed)
    centers = x[rng.choice(x.shape[0], size=k, replace=False)].copy()
    labels = np.zeros(x.shape[0], dtype=int)
    for _ in range(iterations):
        d = np.linalg.norm(x[:, None, :] - centers[None, :, :], axis=2)
        new_labels = np.argmin(d, axis=1)
        if np.array_equal(new_labels, labels) and _ > 0:
            break
        labels = new_labels
        for c in range(k):
            if np.any(labels == c):
                centers[c] = x[labels == c].mean(axis=0)
    d = np.linalg.norm(x - centers[labels], axis=1)
    rep = np.array([int(np.nonzero(labels == c)[0][np.argmin(d[labels == c])]) if np.any(labels == c) else -1
                    for c in range(k)])
    sizes = np.array([int((labels == c).sum()) for c in range(k)])
    return ClusterResult(labels, sizes, centers, rep, float((d ** 2).sum()))


def summary_lines(res: PcaResult, cl: ClusterResult | None = None) -> list[str]:
    lines = [f"主成分分析 (成分 {res.explained.size} 個): 寄与率 "
             + ", ".join(f"{v * 100:.1f} %" for v in res.explained)
             + f" (合わせて {res.explained.sum() * 100:.1f} %)"]
    if cl is not None:
        lines.append(f"  分類 (k-means、群 {cl.sizes.size} 個): 大きさ "
                     + ", ".join(str(int(s)) for s in cl.sizes)
                     + "、中心に近いフレーム " + ", ".join(str(int(i) + 1) for i in cl.representative))
        lines.append("  群の数は利用者が決めた値です。いくつが正しいかは判定しません。")
    return lines
