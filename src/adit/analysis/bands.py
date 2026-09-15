
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RY_EV = 13.605693122994


@dataclass
class BandData:
    kpts_frac: np.ndarray
    energies_ev: np.ndarray  # (nk, nbands)
    cell: np.ndarray  # (3, 3) Å
    labels: list[tuple[int, str]] = field(default_factory=list)
    fermi_ev: float | None = None

    def x_axis(self) -> np.ndarray:
        rec = 2 * np.pi * np.linalg.inv(self.cell).T
        kc = self.kpts_frac @ rec
        d = np.linalg.norm(np.diff(kc, axis=0), axis=1)
        return np.concatenate([[0.0], np.cumsum(d)])


def gap_details(energies_ev: np.ndarray, fermi_ev: float | None, kpts_frac=None, labels=None) -> dict | None:
    if fermi_ev is None or energies_ev.size == 0:
        return None
    e = np.asarray(energies_ev, dtype=float)
    occupied = e <= fermi_ev
    if not occupied.any() or occupied.all():
        return None
    vb = np.where(occupied, e, -np.inf)
    cb = np.where(~occupied, e, np.inf)
    vbm_k = int(np.argmax(vb.max(axis=1)))
    cbm_k = int(np.argmin(cb.min(axis=1)))
    vbm = float(vb[vbm_k].max())
    cbm = float(cb[cbm_k].min())
    direct_per_k = cb.min(axis=1) - vb.max(axis=1)
    direct_k = int(np.argmin(direct_per_k))
    name = dict(labels or {})
    out = {"gap_ev": cbm - vbm, "vbm_ev": vbm, "cbm_ev": cbm,
           "vbm_kpoint_index": vbm_k, "cbm_kpoint_index": cbm_k,
           "vbm_label": name.get(vbm_k, ""), "cbm_label": name.get(cbm_k, ""),
           "direct": vbm_k == cbm_k,
           "direct_gap_ev": float(direct_per_k[direct_k]), "direct_gap_kpoint_index": direct_k,
           "direct_gap_label": name.get(direct_k, ""),
           "note": ("VBM と CBM が同じ k 点にあるかどうかを「直接」と書いています (機械的な事実)。"
                    "k 点は与えた経路の中での番号で、経路の外により低い CBM があるかどうかは分かりません。")}
    if kpts_frac is not None:
        k = np.asarray(kpts_frac, dtype=float)
        out["vbm_kpoint_frac"] = k[vbm_k].tolist()
        out["cbm_kpoint_frac"] = k[cbm_k].tolist()
    return out


def load_bands(run_dir: Path, code: str, fermi_ev: float | None) -> BandData | None:
    bd = run_dir / "bands"
    if not (bd / "kpath.json").is_file():
        return None
    kp = json.loads((bd / "kpath.json").read_text(encoding="utf-8"))
    kpts = np.array(kp["kpts"]); labels = [(int(i), str(l)) for i, l in kp["labels"]]; cell = np.array(kp["cell"])
    if code == "dftbplus":
        e = _dftb_band_out(bd / "band.out")
    elif code == "espresso":
        e = _qe_bands_out(bd / "output.log")
    elif code == "vasp":
        e = _vasp_eigenval(bd / "EIGENVAL")
    else:
        return None
    if e is None or len(e) == 0:
        return None
    n = min(len(e), len(kpts))
    return BandData(kpts_frac=kpts[:n], energies_ev=np.array(e[:n]), cell=cell, labels=[(i, l) for i, l in labels if i < n], fermi_ev=fermi_ev)


def _dftb_band_out(p: Path):
    if not p.is_file():
        return None
    blocks, cur = [], None
    for l in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if l.startswith(" KPT") or l.startswith("KPT"):
            cur = []; blocks.append(cur)
        elif cur is not None:
            w = l.split()
            if len(w) == 3:
                cur.append(float(w[1]))
    return [b for b in blocks if b]


def _qe_bands_out(p: Path):
    if not p.is_file():
        return None
    txt = p.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"\n\s+k =.*?bands \(ev\):\s*\n", txt)[1:]
    out = []
    for part in parts:
        vals = []
        for l in part.splitlines():
            if not l.strip():
                if vals:
                    break
                continue
            if l.strip().startswith(("occupation", "highest", "Writing", "the Fermi")):
                break
            try:
                vals += [float(x) for x in re.findall(r"-?\d+\.\d+", l)]
            except ValueError:
                break
        if vals:
            out.append(vals)
    return out


def _vasp_eigenval(p: Path):
    if not p.is_file():
        return None
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        _, nk, nb = [int(x) for x in lines[5].split()[:3]]
    except (ValueError, IndexError):
        return None
    out, i = [], 6
    for _ in range(nk):
        while i < len(lines) and not lines[i].strip():
            i += 1
        i += 1
        vals = []
        for _b in range(nb):
            w = lines[i].split(); i += 1
            vals.append(float(w[1]))
        out.append(vals)
    return out


def plot_bands(bd: BandData, path_png: Path, window_ev: float = 10.0) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = bd.x_axis()
    e = bd.energies_ev - (bd.fermi_ev or 0.0)
    fig, ax = plt.subplots(figsize=(6, 4))
    for b in range(e.shape[1]):
        ax.plot(x, e[:, b], lw=1.0, color="C0")
    for i, l in bd.labels:
        ax.axvline(x[i], color="gray", lw=0.6)
    ax.set_xticks([x[i] for i, _ in bd.labels]); ax.set_xticklabels([l.replace("G", "Γ") for _, l in bd.labels])
    if bd.fermi_ev is not None:
        ax.axhline(0, color="gray", ls="--", lw=0.8); ax.set_ylabel("E − E$_F$ [eV]")
        ax.set_ylim(-window_ev, window_ev)
    else:
        ax.set_ylabel("E [eV]")
    ax.set_xlim(x[0], x[-1]); ax.grid(alpha=0.2)
    fig.savefig(path_png, dpi=110, bbox_inches="tight"); plt.close(fig)
