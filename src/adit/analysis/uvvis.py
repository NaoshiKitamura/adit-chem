
from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np

from adit.lang import L
from adit.analysis import plotstyle

TITLE = "ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS"
CM1_PER_EV = 8065.543937  # CODATA 2018
HC_EV_NM = 1239.841984    # hc [eV nm]
SHAPES = ("gauss", "lorentz")
_ROW = re.compile(r"^\s*(\S+\s*->\s*\S+|\d+)\s+(-?[\d.]+(?:[Ee][-+]?\d+)?(?:\s+-?[\d.]+(?:[Ee][-+]?\d+)?)*)\s*$")


def read_orca_absorption(path: Path) -> dict | None:
    if not Path(path).is_file():
        return None
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    tables = []
    i = 0
    while i < len(lines):
        if lines[i].strip() != TITLE:
            i += 1
            continue
        start = i + 1
        j = i + 1
        units = None
        rows = []
        while j < len(lines) and j < start + 8 and units is None:
            if "(nm)" in lines[j]:
                units = re.findall(r"\(([^)]*)\)", lines[j])
            j += 1
        if units is None:
            i = j
            continue
        while j < len(lines) and lines[j].strip().startswith("-"):
            j += 1
        while j < len(lines):
            m = _ROW.match(lines[j])
            if not m:
                break
            v = [float(x) for x in m.group(2).split()]
            if units[0] == "eV":
                ev, cm, nm, f = v[0], v[1], v[2], v[3]
            else:
                cm, nm, f = v[0], v[1], v[2]
                ev = cm / CM1_PER_EV
            rows.append({"label": re.sub(r"\s+", " ", m.group(1)), "energy_ev": ev, "energy_cm1": cm, "wavelength_nm": nm, "fosc": f, "line": j + 1})
            j += 1
        tables.append({"rows": rows, "line": start, "units": units})
        i = j
    if not tables or not tables[-1]["rows"]:
        return None
    t = tables[-1]
    return {"transitions": t["rows"], "line": f"{Path(path).name}:{t['line']}", "n_tables": len(tables), "units": t["units"],
            "format": "eV cm-1 nm fosc" if t["units"][0] == "eV" else "cm-1 nm fosc"}


def broaden(e_ev, fosc, fwhm_ev: float, shape: str, grid) -> np.ndarray:
    x = np.asarray(grid)[:, None] - np.asarray(e_ev)[None, :]
    if shape == "gauss":
        s = fwhm_ev / (2 * np.sqrt(2 * np.log(2)))
        g = np.exp(-0.5 * (x / s) ** 2) / (s * np.sqrt(2 * np.pi))
    elif shape == "lorentz":
        gam = fwhm_ev / 2
        g = (gam / np.pi) / (x ** 2 + gam ** 2)
    else:
        raise ValueError(L(f"広げる形は {' / '.join(SHAPES)}: {shape!r}", f"shape must be {' / '.join(SHAPES)}: {shape!r}"))
    return g @ np.asarray(fosc, dtype=float)


def analyze_uvvis(run_dir: Path, out_dir: Path, broadening: tuple[str, float] | None) -> dict | None:
    t = read_orca_absorption(Path(run_dir) / "output.log")
    if t is None:
        return None
    out_dir = Path(out_dir)
    tr = t["transitions"]
    with open(out_dir / "uvvis_transitions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["transition", "energy_ev", "energy_cm1", "wavelength_nm", "fosc", "line"])
        for r in tr:
            w.writerow([r["label"], r["energy_ev"], r["energy_cm1"], r["wavelength_nm"], r["fosc"], f"output.log:{r['line']}"])
    res = {"source": t["line"], "n_tables": t["n_tables"], "format": t["format"], "n_transitions": len(tr),
           "transitions": [{k: r[k] for k in ("label", "energy_ev", "wavelength_nm", "fosc")} for r in tr],
           "file_transitions": str(out_dir / "uvvis_transitions.csv"), "broadening": None, "reasons": []}
    e = np.array([r["energy_ev"] for r in tr]); f = np.array([r["fosc"] for r in tr])
    grid = y = None
    if broadening is not None:
        shape, fwhm = broadening
        if shape not in SHAPES or not fwhm or fwhm <= 0:
            res["reasons"].append(L(f"広げ方の指定が読めません ({shape}, {fwhm})。形は gauss / lorentz、幅は正の数 [eV]", f"cannot use the broadening ({shape}, {fwhm}); shape gauss / lorentz, width positive [eV]"))
        else:
            lo, hi = max(1e-3, float(e.min()) - 5 * fwhm), float(e.max()) + 5 * fwhm
            grid = np.linspace(lo, hi, 2000)
            y = broaden(e, f, fwhm, shape, grid)
            with open(out_dir / "uvvis_spectrum.csv", "w", newline="", encoding="utf-8") as fp:
                w = csv.writer(fp); w.writerow(["energy_ev", "wavelength_nm", "epsilon_per_ev"])
                for a, b in zip(grid, y):
                    w.writerow([f"{a:.6f}", f"{HC_EV_NM / a:.4f}", f"{b:.6g}"])
            res.update(broadening={"shape": shape, "fwhm_ev": float(fwhm)}, file_spectrum=str(out_dir / "uvvis_spectrum.csv"),
                       spectrum_unit=L("振動子強度 / eV (各遷移の面積が f)", "oscillator strength per eV (each transition has area f)"))
    else:
        res["reasons"].append(L("幅と形を指定していないので、遷移の棒だけを描きました (--uvvis gauss:0.3 のように指定すると広げます)",
                                "no width and shape given, so only the transition sticks are drawn (e.g. --uvvis gauss:0.3 to broaden)"))
    if t["n_tables"] > 1:
        res["reasons"].append(L(f"吸収の表が {t['n_tables']} 個あり、最後の表を使いました", f"{t['n_tables']} absorption tables found; the last one is used"))
    _plot(e, f, grid, y, out_dir / "uvvis.png")
    res["figure"] = str(out_dir / "uvvis.png")
    return res


def _plot(e, f, grid, y, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6, 5.2))
    for ax, xs, xg, xl in ((a1, e, grid, "E [eV]"), (a2, HC_EV_NM / e, None if grid is None else HC_EV_NM / grid, "wavelength [nm]")):
        axs = ax.twinx() if y is not None else ax
        axs.vlines(xs, 0, f, color="tab:red", lw=1.2)
        axs.set_ylabel("oscillator strength f")
        if y is not None:
            ax.plot(xg, y, color="k", lw=1.2)
            ax.set_ylabel("f per eV")
        ax.set_xlabel(xl); plotstyle.grid(ax)
    fig.tight_layout(); fig.savefig(path, dpi=110, bbox_inches="tight"); plt.close(fig)


def summary_lines(t: dict) -> list[str]:
    top = sorted(t["transitions"], key=lambda r: -r["fosc"])[:5]
    b = t.get("broadening")
    bs = L(f"、{b['shape']} で半値全幅 {b['fwhm_ev']:g} eV に広げた", f", broadened with {b['shape']} FWHM {b['fwhm_ev']:g} eV") if b else ""
    s = [L(f"UV-Vis ({t['source']}): 遷移 {t['n_transitions']} 本{bs}。振動子強度の大きい順: ", f"UV-Vis ({t['source']}): {t['n_transitions']} transitions{bs}; largest oscillator strengths: ")
         + ", ".join(f"{r['energy_ev']:.3f} eV / {r['wavelength_nm']:.1f} nm (f = {r['fosc']:.4f})" for r in top)]
    return s + ["  " + r for r in t.get("reasons", [])]


__all__ = ["read_orca_absorption", "broaden", "analyze_uvvis", "summary_lines", "SHAPES"]
