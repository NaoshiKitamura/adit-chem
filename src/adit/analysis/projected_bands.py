"""Projected (fat) band structure from the filproj file of Quantum ESPRESSO projwfc.x."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Projection:
    iwfc: int
    atom_index: int
    element: str
    label: str
    l: int
    m: int
    weights: np.ndarray


@dataclass
class ProjectedBands:
    projections: list[Projection]
    n_kpoints: int
    n_bands: int

    def by_atom(self, atom_index: int) -> np.ndarray:
        parts = [p.weights for p in self.projections if p.atom_index == atom_index]
        if not parts:
            raise ValueError(f"原子 {atom_index} の射影がありません")
        return np.sum(parts, axis=0)

    def by_element(self, element: str) -> np.ndarray:
        parts = [p.weights for p in self.projections if p.element.lower() == element.lower()]
        if not parts:
            raise ValueError(f"元素 {element} の射影がありません")
        return np.sum(parts, axis=0)

    def by_angular_momentum(self, l: int) -> np.ndarray:
        parts = [p.weights for p in self.projections if p.l == l]
        if not parts:
            raise ValueError(f"l = {l} の射影がありません")
        return np.sum(parts, axis=0)

    def total(self) -> np.ndarray:
        return np.sum([p.weights for p in self.projections], axis=0)


_HEADER = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s*$")
_WFC = re.compile(r"^\s*(\d+)\s+(\d+)\s+([A-Za-z]{1,2})\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$")


def read_filproj(path: Path) -> ProjectedBands:
    """Read a projwfc.x filproj file (*.projwfc_up)."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    start = None
    for i, line in enumerate(lines):
        m = _HEADER.match(line)
        if m and i + 1 < len(lines) and re.fullmatch(r"\s*[TF]\s+[TF]\s*", lines[i + 1]):
            start = i
            natomwfc, nk, nbnd = (int(x) for x in m.groups())
            break
    if start is None:
        raise ValueError(f"{Path(path).name} に projwfc の見出し (natomwfc nkstot nbnd) が見つかりません")
    pos = start + 2
    projections: list[Projection] = []
    for _ in range(natomwfc):
        head = _WFC.match(lines[pos])
        if head is None:
            raise ValueError(f"{Path(path).name} の {pos + 1} 行目を軌道の見出しとして読めません: {lines[pos]!r}")
        iwfc, iatom, element, label, _n, l, m_index = head.groups()
        block = lines[pos + 1: pos + 1 + nk * nbnd]
        if len(block) < nk * nbnd:
            raise ValueError(f"{Path(path).name} の軌道 {iwfc} の重みが {nk * nbnd} 行ありません")
        vals = np.fromstring(" ".join(block), sep=" ").reshape(nk * nbnd, 3)[:, 2]
        projections.append(Projection(int(iwfc), int(iatom), element, label, int(l), int(m_index),
                                      vals.reshape(nk, nbnd)))
        pos += 1 + nk * nbnd
    return ProjectedBands(projections, nk, nbnd)


def find_filproj(run_dir: Path) -> Path | None:
    for pattern in ("*.projwfc_up", "*.proj.projwfc_up", "bands/*.projwfc_up"):
        hits = sorted(Path(run_dir).glob(pattern))
        if hits:
            return hits[0]
    return None


def summary_lines(pb: ProjectedBands) -> list[str]:
    total = pb.total()
    elements = sorted({p.element for p in pb.projections})
    lines = [f"射影バンド: {pb.n_kpoints} k 点 × {pb.n_bands} バンド、原子軌道 {len(pb.projections)} 個"]
    for el in elements:
        w = pb.by_element(el)
        lines.append(f"  {el}: 重みの平均 {w.mean():.3f} (帯・k 点で平均)")
    lines.append(f"  全射影の和の平均 {total.mean():.3f} "
                 "(1 に足りない分は、原子軌道で表しきれない成分です)")
    return lines
