
from __future__ import annotations

from adit.errors import AditValueError
import re
from pathlib import Path

import numpy as np

from adit.lang import L

from adit.spec import (EV_PER_ANG3_IN_GPA as EV_ANG3_TO_GPA, HARTREE_PER_BOHR3_IN_GPA as HARTREE_BOHR3_TO_GPA,
                        HARTREE_PER_BOHR_IN_EV_PER_ANG as HARTREE_BOHR_TO_EV_ANG, RY_PER_BOHR_IN_EV_PER_ANG as RY_BOHR_TO_EV_ANG)
CODES = ("dftbplus", "espresso", "vasp")
_F = r"(-?\d+\.\d*(?:[EeDd][-+]?\d+)?)"


class OutputError(AditValueError):
    pass


def _text(p: Path) -> str:
    if not p.is_file():
        raise OutputError(L(f"{p} がありません (まだ計算していないかもしれません)", f"{p} not found (perhaps not run yet)"))
    return p.read_text(encoding="utf-8", errors="replace")


def _spec(d: Path):
    from adit.project import load_project

    return load_project(d)


def read_forces(d: Path | str) -> np.ndarray:
    d = Path(d)
    spec = _spec(d)
    n, code = len(spec.structure.atoms.symbols), spec.method.code
    if code == "dftbplus":
        t = _text(d / "detailed.out")
        if "Total Forces" not in t:
            raise OutputError(L(f"{d}/detailed.out に Total Forces がありません", f"no Total Forces in {d}/detailed.out"))
        block = t.split("Total Forces", 1)[1].split("\n\n", 1)[0]
        rows = re.findall(rf"^\s*(\d+)\s+{_F}\s+{_F}\s+{_F}\s*$", block, re.M)
        f = np.zeros((n, 3))
        for r in rows:
            i = int(r[0]) - 1
            if 0 <= i < n:
                f[i] = [float(x.replace("D", "E").replace("d", "e")) for x in r[1:]]
        if len(rows) != n:
            raise OutputError(L(f"{d}/detailed.out の力の行が {len(rows)} 行で、原子数 {n} と違います", f"{len(rows)} force rows in {d}/detailed.out for {n} atoms"))
        return f * HARTREE_BOHR_TO_EV_ANG
    if code == "espresso":
        t = _text(d / "output.log")
        if "Forces acting on atoms" not in t:
            raise OutputError(L(f"{d}/output.log に Forces acting on atoms がありません (tprnfor)", f"no 'Forces acting on atoms' in {d}/output.log (tprnfor)"))
        block = t.rsplit("Forces acting on atoms", 1)[1]
        rows = re.findall(r"atom\s+(\d+)\s+type\s+\d+\s+force\s+=\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", block)[:n]
        if len(rows) != n or sorted(int(r[0]) for r in rows) != list(range(1, n + 1)):
            raise OutputError(L(f"{d}/output.log の力の行が原子数 {n} とそろいません", f"force rows in {d}/output.log do not match {n} atoms"))
        f = np.zeros((n, 3))
        for r in rows:
            f[int(r[0]) - 1] = [float(x) for x in r[1:]]
        return f * RY_BOHR_TO_EV_ANG
    if code == "vasp":
        from ase.io import read

        from adit.codes.vasp import VaspGenerator
        p = d / "vasprun.xml"
        if not p.is_file():
            raise OutputError(L(f"{p} がありません", f"{p} not found"))
        fp = read(str(p), index=-1).get_forces()
        _, order = VaspGenerator._ordered_atoms(spec)
        if len(fp) != n:
            raise OutputError(L(f"{p} の原子数 {len(fp)} が spec.json の {n} と違います", f"{p} has {len(fp)} atoms but spec.json has {n}"))
        f = np.zeros((n, 3))
        for k, i in enumerate(order):
            f[i] = fp[k]
        return f
    raise OutputError(L(f"{code} の出力の力はまだ読めません (読めるのは {', '.join(CODES)})", f"forces of {code} output cannot be read yet ({', '.join(CODES)})"))


def read_stress(d: Path | str) -> np.ndarray:
    d = Path(d)
    spec = _spec(d)
    code = spec.method.code
    if code == "dftbplus":
        t = _text(d / "detailed.out")
        if "Total stress tensor" not in t:
            raise OutputError(L(f"{d}/detailed.out に Total stress tensor がありません (周期系だけ出ます)", f"no Total stress tensor in {d}/detailed.out (periodic systems only)"))
        block = t.split("Total stress tensor", 1)[1].strip().splitlines()[:3]
        s = np.array([[float(x.replace("D", "E")) for x in line.split()[:3]] for line in block]) * HARTREE_BOHR3_TO_GPA
        m = re.findall(r"^Pressure:\s*(-?[\d.]+(?:[Ee][-+]?\d+)?)\s+au", t, re.M)
        if not m:
            raise OutputError(L(f"{d}/detailed.out に Pressure の行が無く、応力の符号の向きを確かめられません", f"no Pressure line in {d}/detailed.out; cannot check the sign of the stress"))
        p = float(m[-1]) * HARTREE_BOHR3_TO_GPA
        tr3 = float(np.trace(s)) / 3
        tol = 1e-4 * max(abs(p), abs(tr3)) + 1e-6
        plus, minus = abs(p - tr3) <= tol, abs(p + tr3) <= tol
        if plus and minus:
            return -s
        if plus:
            return -s
        if minus:
            return s
        raise OutputError(L(f"{d}/detailed.out の Pressure ({p:.6g} GPa) と応力の対角の平均 ({tr3:.6g} GPa) の関係が合いません",
                            f"Pressure ({p:.6g} GPa) and the mean diagonal stress ({tr3:.6g} GPa) in {d}/detailed.out do not match"))
    if code == "espresso":
        t = _text(d / "output.log")
        if "total   stress" not in t:
            raise OutputError(L(f"{d}/output.log に total stress がありません (tstress)", f"no total stress in {d}/output.log (tstress)"))
        block = t.rsplit("total   stress", 1)[1].splitlines()[1:4]
        kbar = np.array([[float(x) for x in line.split()[3:6]] for line in block])
        return -kbar / 10.0
    if code == "vasp":
        from ase.io import read
        p = d / "vasprun.xml"
        if not p.is_file():
            raise OutputError(L(f"{p} がありません", f"{p} not found"))
        return read(str(p), index=-1).get_stress(voigt=False) * EV_ANG3_TO_GPA
    raise OutputError(L(f"{code} の出力の応力はまだ読めません (読めるのは {', '.join(CODES)})", f"stress of {code} output cannot be read yet ({', '.join(CODES)})"))


__all__ = ["OutputError", "read_forces", "read_stress", "CODES"]
