
from __future__ import annotations

from ase import Atoms

from adit.lang import L

DEFAULT_SYMPRECS = (1e-5, 1e-3, 1e-1)


def spacegroup(atoms: Atoms | None, symprecs=DEFAULT_SYMPRECS) -> dict | None:
    if atoms is None or not all(atoms.pbc) or atoms.cell.rank < 3:
        return None
    try:
        import spglib
    except ImportError:
        return {"reason": L("spglib が入っていないので空間群を出していません (pip install spglib、または pip install adit-chem[analysis])",
                            "spglib is not installed, so no space group is given (pip install spglib, or pip install adit-chem[analysis])")}
    cell = (atoms.cell[:], atoms.get_scaled_positions(wrap=True), atoms.get_atomic_numbers())
    res = []
    for sp in symprecs:
        ds = spglib.get_symmetry_dataset(cell, symprec=float(sp))
        if ds is None:
            res.append({"symprec_A": float(sp), "international": None, "number": None, "hall": None, "pointgroup": None}); continue
        g = (lambda k: getattr(ds, k)) if hasattr(ds, "international") else (lambda k: ds[k])
        res.append({"symprec_A": float(sp), "international": g("international"), "number": int(g("number")), "hall": g("hall"),
                    "pointgroup": g("pointgroup")})
    return {"results": res, "spglib": getattr(spglib, "__version__", "?"), "structure": L("最終構造", "final structure"),
            "angle_tolerance": L("spglib の既定", "spglib default")}


def summary_lines(t: dict) -> list[str]:
    if "results" not in t:
        return []
    parts = [f"{r['international'] or '?'} (No. {r['number'] if r['number'] is not None else '?'}, symprec {r['symprec_A']:g} Å)" for r in t["results"]]
    return [L(f"空間群 ({t['structure']}、spglib {t['spglib']}): ", f"space group ({t['structure']}, spglib {t['spglib']}): ") + ", ".join(parts)]


__all__ = ["spacegroup", "summary_lines", "DEFAULT_SYMPRECS"]
