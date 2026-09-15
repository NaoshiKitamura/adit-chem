
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ase import Atoms


@dataclass
class KPath:
    kpts: np.ndarray
    labels: list[tuple[int, str]]
    path: str

    def segments(self) -> list[tuple[str, np.ndarray, np.ndarray, int]]:
        out = []
        for (i0, l0), (i1, l1) in zip(self.labels[:-1], self.labels[1:]):
            if i1 > i0:
                out.append((f"{l0}-{l1}", self.kpts[i0], self.kpts[i1], i1 - i0))
        return out


def band_path(atoms: Atoms, path: str = "", npoints: int = 60) -> KPath:
    bp = atoms.cell.bandpath(path or None, npoints=npoints)
    x, X, labels = bp.get_linear_kpoint_axis()
    idx = [int(np.argmin(np.abs(x - xi))) for xi in X]
    return KPath(kpts=np.asarray(bp.kpts), labels=list(zip(idx, labels)), path=bp.path)


KPATH_FILE = "kpath.json"


def kpath_json(kp: KPath, atoms: Atoms) -> str:
    import json
    return json.dumps({"path": kp.path, "kpts": kp.kpts.tolist(), "labels": [[i, l] for i, l in kp.labels],
                       "cell": atoms.cell.tolist()}, indent=1)


def dftb_klines(kp: KPath) -> list[str]:
    out = ["  KPointsAndWeights = Klines {"]
    first_i, first_l = kp.labels[0]
    k = kp.kpts[first_i]
    out.append(f"    1  {k[0]:.6f} {k[1]:.6f} {k[2]:.6f}   # {first_l}")
    for name, k0, k1, n in kp.segments():
        out.append(f"    {n}  {k1[0]:.6f} {k1[1]:.6f} {k1[2]:.6f}   # {name.split('-')[1]}")
    out.append("  }")
    return out


def vasp_line_mode(kp: KPath, points_per_line: int) -> str:
    lines = ["k points along high symmetry lines (adit)", f" {points_per_line}   ! number of points per line", "Line-mode", "fractional"]
    for name, k0, k1, n in kp.segments():
        a, b = name.split("-")
        lines.append(f" {k0[0]:.6f} {k0[1]:.6f} {k0[2]:.6f}  {a}")
        lines.append(f" {k1[0]:.6f} {k1[1]:.6f} {k1[2]:.6f}  {b}")
        lines.append("")
    return "\n".join(lines) + "\n"


def qe_crystal_b(kp: KPath) -> str:
    segs = kp.segments()
    verts = []
    for i, (name, k0, k1, n) in enumerate(segs):
        if i == 0:
            verts.append((k0, n))
        elif not np.allclose(k0, verts[-1][0]):
            verts[-1] = (verts[-1][0], 1)
            verts.append((k0, n))
        else:
            verts[-1] = (verts[-1][0], n)
        verts.append((k1, 1))
    lines = ["K_POINTS crystal_b", f"{len(verts)}"]
    for k, n in verts:
        lines.append(f"  {k[0]:.6f} {k[1]:.6f} {k[2]:.6f} {n}")
    return "\n".join(lines) + "\n"
