
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from adit.lang import L
from adit.analysis import plotstyle

_LORB = {3: "spd", 4: "spdf", 9: "sppp" + "d" * 5, 16: "sppp" + "d" * 5 + "f" * 7}
_QE_FILE = re.compile(r"\.pdos_atm#(\d+)\(([A-Za-z]+)\)_wfc#(\d+)\(([spdf])[^)]*\)$")


def _noncollinear(incar: str) -> bool:
    return re.search(r"^\s*(LNONCOLLINEAR|LSORBIT)\s*=\s*\.?T", incar, re.M | re.I) is not None


def read_doscar(run_dir: Path) -> dict:
    from ase.io import read

    p = run_dir / "DOSCAR"
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 7:
        return {"reasons": [L("DOSCAR が短すぎます", "DOSCAR is too short")]}
    head = lines[0].split()
    nions, partial = int(head[0]), int(head[2])
    emax, emin, nedos, ef = [float(x) for x in lines[5].split()[:4]]
    nedos = int(nedos)
    tot = np.array([[float(x) for x in l.split()] for l in lines[6:6 + nedos]])
    spin = 2 if tot.shape[1] == 5 else 1
    total = {"up": tot[:, 1], "down": tot[:, 2]} if spin == 2 else {"": tot[:, 1]}
    out = {"source": "DOSCAR", "energy_ev": tot[:, 0], "fermi_ev": ef, "spin": spin, "total": total, "channels": {}}
    if partial != 1 or len(lines) < 6 + nedos + nions * (nedos + 1):
        out["reasons"] = [L("DOSCAR に原子ごとの DOS がありません (1 行目の 3 つ目が 0。VASP は LORBIT を指定した計算で書きます)",
                            "DOSCAR has no per-atom DOS (third number on line 1 is 0; VASP writes it when LORBIT is set)")]
        return out
    syms = None
    for name in ("CONTCAR", "POSCAR"):
        q = run_dir / name
        if q.is_file() and q.stat().st_size > 0:
            try:
                syms = read(str(q), format="vasp").get_chemical_symbols(); break
            except Exception:
                pass
    if syms is None or len(syms) != nions:
        out["reasons"] = [L(f"原子の元素が分かりません (CONTCAR / POSCAR が読めないか、原子数が DOSCAR の {nions} と違う)",
                            f"cannot tell the element of each atom (CONTCAR / POSCAR unreadable or atom count differs from DOSCAR's {nions})")]
        return out
    ncl = _noncollinear((run_dir / "INCAR").read_text(encoding="utf-8", errors="replace") if (run_dir / "INCAR").is_file() else "")
    comps = 4 if ncl else spin
    ch: dict = defaultdict(lambda: defaultdict(lambda: 0.0))
    at = 6 + nedos
    for i in range(nions):
        blk = np.array([[float(x) for x in l.split()] for l in lines[at + 1: at + 1 + nedos]])
        at += 1 + nedos
        ncol = blk.shape[1] - 1
        norb = ncol // comps if ncol % comps == 0 else None
        if norb not in _LORB:
            out["reasons"] = [L(f"原子 {i + 1} の列の数 {ncol} を軌道に分けられません (成分 {comps} 個あたり 3・4・9・16 軌道のどれでもない)",
                                f"cannot split the {ncol} columns of atom {i + 1} into orbitals (not 3, 4, 9 or 16 orbitals of {comps} components)")]
            out["channels"] = {}
            return out
        for k, l in enumerate(_LORB[norb]):
            if ncl:
                ch[(syms[i], l)][""] = ch[(syms[i], l)][""] + blk[:, 1 + 4 * k]
            elif spin == 2:
                ch[(syms[i], l)]["up"] = ch[(syms[i], l)]["up"] + blk[:, 1 + 2 * k]
                ch[(syms[i], l)]["down"] = ch[(syms[i], l)]["down"] + blk[:, 2 + 2 * k]
            else:
                ch[(syms[i], l)][""] = ch[(syms[i], l)][""] + blk[:, 1 + k]
    out["channels"] = {k: dict(v) for k, v in ch.items()}
    out["noncollinear"] = ncl
    out["orbitals_per_atom"] = int(norb)
    return out


def _qe_files(run_dir: Path) -> tuple[list[Path], list[Path]]:
    cands = [run_dir] + [p for p in run_dir.iterdir() if p.is_dir()]
    atm, tot = [], []
    for d in cands:
        atm += [p for p in d.iterdir() if p.is_file() and _QE_FILE.search(p.name)]
        tot += [p for p in d.iterdir() if p.is_file() and p.name.endswith(".pdos_tot")]
    return sorted(atm), sorted(tot)


def _qe_table(p: Path) -> tuple[np.ndarray, bool]:
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    head = next((l for l in lines if l.lstrip().startswith("#")), "")
    names = re.sub(r"^\s*#\s*E\s*\(eV\)", "", head).split()
    spin = bool(names) and (names[0].lower().startswith("ldosup") or names[0].lower().startswith("dosup"))
    data = np.array([[float(x) for x in l.split()] for l in lines if l.strip() and not l.lstrip().startswith("#")])
    return data, spin


def read_projwfc(run_dir: Path, fermi_ev: float | None) -> dict | None:
    atm, tot = _qe_files(run_dir)
    if not atm:
        return None
    ch: dict = defaultdict(lambda: defaultdict(lambda: 0.0))
    energy, spin_any = None, None
    for p in atm:
        m = _QE_FILE.search(p.name)
        el, l = m.group(2), m.group(4)
        d, spin = _qe_table(p)
        if energy is None:
            energy, spin_any = d[:, 0], spin
        elif len(d) != len(energy) or spin != spin_any:
            return {"reasons": [L(f"projwfc.x のファイルどうしでエネルギーの点の数かスピンの形が違います ({p.name})", f"projwfc.x files differ in energy grid or spin layout ({p.name})")]}
        if spin:
            ch[(el, l)]["up"] = ch[(el, l)]["up"] + d[:, 1]
            ch[(el, l)]["down"] = ch[(el, l)]["down"] + d[:, 2]
        else:
            ch[(el, l)][""] = ch[(el, l)][""] + d[:, 1]
    out = {"source": f"projwfc.x ({len(atm)} files, {atm[0].parent.name}/)", "energy_ev": energy, "fermi_ev": fermi_ev, "spin": 2 if spin_any else 1,
           "channels": {k: dict(v) for k, v in ch.items()}, "reasons": []}
    if tot:
        d, spin = _qe_table(tot[0])
        out["total"] = {"up": d[:, 1], "down": d[:, 2]} if spin else {"": d[:, 1]}
        out["total_source"] = tot[0].name
    else:
        s = defaultdict(lambda: 0.0)
        for v in out["channels"].values():
            for k, arr in v.items():
                s[k] = s[k] + arr
        out["total"] = dict(s)
        out["total_source"] = L("pdos_tot が無いので、各原子の LDOS の和", "sum of per-atom LDOS (no pdos_tot)")
    return out


def analyze_pdos(run_dir: Path, code: str, fermi_ev: float | None, out_dir: Path) -> dict | None:
    run_dir = Path(run_dir)
    if code == "vasp" and (run_dir / "DOSCAR").is_file():
        d = read_doscar(run_dir)
    elif code == "espresso":
        d = read_projwfc(run_dir, fermi_ev)
        if d is None:
            return None
    else:
        return None
    if d.get("energy_ev") is None or not d.get("channels"):
        return {"source": d.get("source"), "reasons": d.get("reasons", [])}
    e = np.asarray(d["energy_ev"])
    ef = d.get("fermi_ev")
    x = e - ef if ef is not None else e
    cols = {"energy_minus_ef_ev" if ef is not None else "energy_ev": x}
    for k, v in d["total"].items():
        cols[f"total{'_' + k if k else ''}"] = v
    for (el, l), v in sorted(d["channels"].items()):
        for k, arr in v.items():
            cols[f"{el}_{l}{'_' + k if k else ''}"] = arr
    out_dir = Path(out_dir)
    with open(out_dir / "pdos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(list(cols))
        for row in zip(*cols.values()):
            w.writerow([f"{v:.6g}" for v in row])
    _plot(x, d, ef is not None, out_dir / "pdos.png")
    reasons = list(d.get("reasons", []))
    if ef is None:
        reasons.append(L("フェルミ準位が読めないので、横軸はエネルギーそのもの (0 にずらしていません)", "the Fermi level cannot be read, so the energy axis is not shifted"))
    return {"source": d["source"], "fermi_ev": ef, "shifted_to_fermi": ef is not None, "spin": d["spin"], "n_points": int(len(e)),
            "elements": sorted({el for el, _ in d["channels"]}), "channels": [f"{el}_{l}" for el, l in sorted(d["channels"])],
            "columns": list(cols), "file": str(out_dir / "pdos.csv"), "figure": str(out_dir / "pdos.png"),
            "unit": L("states/eV (出力の値のまま。元素・軌道ごとに原子と m を足した値)", "states/eV (as written by the code; summed over atoms and m for each element and orbital)"),
            "reasons": reasons, "total_source": d.get("total_source", "DOSCAR")}


def _plot(x, d: dict, shifted: bool, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    sign = {"": 1.0, "up": 1.0, "down": -1.0}
    for k, v in d["total"].items():
        ax.fill_between(x, 0, sign[k] * np.asarray(v), color="0.85", lw=0, label="total" if k in ("", "up") else None)
    cmap = plt.get_cmap("tab10")
    for n, ((el, l), v) in enumerate(sorted(d["channels"].items())):
        for k, arr in v.items():
            ax.plot(x, sign[k] * np.asarray(arr), lw=1.0, color=cmap(n % 10), label=f"{el} {l}" if k in ("", "up") else None)
    ax.axvline(0 if shifted else (d.get("fermi_ev") or 0), color="gray", ls="--", lw=0.8)
    if d["spin"] == 2:
        ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("E - E$_F$ [eV]" if shifted else "E [eV]"); ax.set_ylabel("PDOS [states/eV]" + (" (down < 0)" if d["spin"] == 2 else ""))
    plotstyle.grid(ax); ax.legend(fontsize=7, ncol=2)
    fig.savefig(path, dpi=110, bbox_inches="tight"); plt.close(fig)


def summary_lines(t: dict) -> list[str]:
    if "channels" not in t:
        return [L("PDOS: ", "PDOS: ") + " ".join(t.get("reasons", []))]
    ef = L(f"フェルミ準位 {t['fermi_ev']:.4f} eV を 0 に", f"Fermi level {t['fermi_ev']:.4f} eV set to 0") if t["shifted_to_fermi"] else L("フェルミ準位なし", "no Fermi level")
    s = [L(f"PDOS ({t['source']}): {', '.join(t['channels'])}、{t['n_points']} 点、スピン {t['spin']}、{ef} (pdos.csv)",
           f"PDOS ({t['source']}): {', '.join(t['channels'])}, {t['n_points']} points, spin {t['spin']}, {ef} (pdos.csv)")]
    return s + ["  " + r for r in t.get("reasons", [])]


__all__ = ["read_doscar", "read_projwfc", "analyze_pdos", "summary_lines"]
