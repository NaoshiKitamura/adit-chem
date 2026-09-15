
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from adit.lang import L
from adit.analysis import plotstyle


def _find(run_dir: Path, name: str) -> Path | None:
    for d in (run_dir, run_dir / "phonopy"):
        if (d / name).is_file():
            return d / name
    return None


def read_band_yaml(path: Path) -> dict:
    nq = npath = None
    seg, labels = [], []
    dist, freqs = [], []
    cur: list[float] | None = None
    section = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            if not line.startswith((" ", "-")):
                key = line.split(":", 1)[0].strip()
                section = key
                if key == "nqpoint":
                    nq = int(line.split(":", 1)[1])
                elif key == "npath":
                    npath = int(line.split(":", 1)[1])
                continue
            if section == "segment_nqpoint":
                m = re.match(r"^-\s*(\d+)", line)
                if m:
                    seg.append(int(m.group(1)))
            elif section == "labels":
                m = re.match(r"^-\s*\[\s*'([^']*)'\s*,\s*'([^']*)'\s*\]", line)
                if m:
                    labels.append((m.group(1), m.group(2)))
            elif section == "phonon":
                if line.startswith("- q-position:"):
                    if cur is not None:
                        freqs.append(cur)
                    cur = []
                elif line.startswith("  distance:"):
                    dist.append(float(line.split(":", 1)[1]))
                elif line.lstrip().startswith("frequency:") and cur is not None:
                    cur.append(float(line.split(":", 1)[1]))
    if cur is not None:
        freqs.append(cur)
    if not freqs or len(dist) != len(freqs) or len({len(x) for x in freqs}) != 1:
        raise ValueError(L(f"{path.name} の q 点と振動数の数が揃いません", f"q-points and frequencies in {path.name} do not line up"))
    return {"nqpoint": nq, "npath": npath, "segment_nqpoint": seg, "labels": labels, "distance": np.array(dist), "frequency": np.array(freqs)}


def read_total_dos(path: Path) -> tuple[np.ndarray, np.ndarray, str]:
    comment, rows = "", []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lstrip().startswith("#"):
            comment = comment or line.lstrip("# ").strip()
            continue
        w = line.split()
        if len(w) >= 2:
            rows.append((float(w[0]), float(w[1])))
    a = np.array(rows).reshape(-1, 2)
    return a[:, 0], a[:, 1], comment


def _ticks(b: dict) -> list[tuple[float, str]]:
    seg, labels, d = b["segment_nqpoint"], b["labels"], b["distance"]
    if not seg or sum(seg) != len(d):
        return []
    out, k = [], 0
    for i, n in enumerate(seg):
        a, z = (labels[i] if i < len(labels) else ("", ""))
        s, e = d[k], d[k + n - 1]
        if out and abs(out[-1][0] - s) < 1e-9:
            if out[-1][1] != a and a:
                out[-1] = (s, f"{out[-1][1]}|{a}")
        else:
            out.append((float(s), a))
        out.append((float(e), z))
        k += n
    return out


def analyze_phonopy(run_dir: Path, out_dir: Path) -> dict | None:
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    bp, dp = _find(run_dir, "band.yaml"), _find(run_dir, "total_dos.dat")
    if bp is None and dp is None:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = {"unit": L("phonopy の出力の単位 (既定 THz)", "unit of the phonopy output (THz by default)"), "reasons": []}
    band = dos = None
    if bp is not None:
        try:
            band = read_band_yaml(bp)
        except Exception as ex:
            t["reasons"].append(L(f"band.yaml を読めません: {ex}", f"cannot read band.yaml: {ex}"))
    if dp is not None:
        try:
            dos = read_total_dos(dp)
        except Exception as ex:
            t["reasons"].append(L(f"total_dos.dat を読めません: {ex}", f"cannot read total_dos.dat: {ex}"))
    if band is not None:
        fr = band["frequency"]
        ticks = _ticks(band)
        t.update(band_file=str(bp), n_qpoints=int(fr.shape[0]), n_bands=int(fr.shape[1]), npath=band["npath"],
                 labels=[l for _, l in ticks], min_frequency=float(fr.min()), max_frequency=float(fr.max()),
                 n_negative_values=int((fr < 0).sum()))
        if dos is not None:
            fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7, 3.8), sharey=True, gridspec_kw={"width_ratios": [3, 1]})
        else:
            fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(band["distance"], fr, color="k", lw=1.0)
        for x, _ in ticks:
            ax.axvline(x, color="gray", lw=0.6)
        if ticks:
            ax.set_xticks([x for x, _ in ticks]); ax.set_xticklabels([("Γ" if l in ("G", "GAMMA", "Gamma") else l) for _, l in ticks])
        ax.axhline(0, color="gray", lw=0.6, ls="--")
        ax.set_xlim(band["distance"][0], band["distance"][-1]); ax.set_ylabel("frequency (phonopy unit, THz by default)")
        if dos is not None:
            ax2.plot(dos[1], dos[0], color="k", lw=1.0); ax2.set_xlabel("DOS"); plotstyle.grid(ax2)
        p = out_dir / "phonon_bands.png"; fig.savefig(p, dpi=110, bbox_inches="tight"); plt.close(fig)
        t["figure_bands"] = str(p)
    if dos is not None:
        t.update(dos_file=str(dp), dos_points=int(len(dos[0])), dos_comment=dos[2])
        if band is None:
            fig, ax = plt.subplots(figsize=(6, 3.2))
            ax.plot(dos[0], dos[1], color="k", lw=1.0); ax.set_xlabel("frequency (phonopy unit, THz by default)"); ax.set_ylabel("DOS"); plotstyle.grid(ax)
            p = out_dir / "phonon_dos.png"; fig.savefig(p, dpi=110, bbox_inches="tight"); plt.close(fig)
            t["figure_dos"] = str(p)
    return t


def summary_lines(t: dict) -> list[str]:
    s = []
    if "band_file" in t:
        s.append(L(f"フォノン分散 (phonopy の band.yaml): q 点 {t['n_qpoints']} 個 × {t['n_bands']} 本、経路 {' '.join(t['labels'])}、"
                   f"振動数 {t['min_frequency']:.4g}〜{t['max_frequency']:.4g} ({t['unit']})、負の値 {t['n_negative_values']} 個",
                   f"phonon dispersion (phonopy band.yaml): {t['n_qpoints']} q-points x {t['n_bands']} bands, path {' '.join(t['labels'])}, "
                   f"frequencies {t['min_frequency']:.4g} to {t['max_frequency']:.4g} ({t['unit']}), {t['n_negative_values']} negative values"))
    if "dos_file" in t:
        s.append(L(f"フォノンの状態密度 (total_dos.dat): {t['dos_points']} 点", f"phonon DOS (total_dos.dat): {t['dos_points']} points"))
    return s + ["  " + r for r in t.get("reasons", [])]


__all__ = ["read_band_yaml", "read_total_dos", "analyze_phonopy", "summary_lines"]
