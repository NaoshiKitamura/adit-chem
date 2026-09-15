
from __future__ import annotations

from dataclasses import dataclass

from adit.lang import L

OTHER = "other"


@dataclass(frozen=True)
class Choice:
    path: str
    label: str
    example: str
    purpose: str


def choices_for(code: str, periodic: bool) -> list[Choice]:
    raise_cut = L("カットオフを上げていき、エネルギーがほとんど変わらなくなる所を探します。",
                  "Raise the cutoff step by step and find where the energy stops changing.")
    out: list[Choice] = []
    if code == "espresso":
        out.append(Choice("method.ecutwfc", L("カットオフ (ecutwfc) [Ry]", "Cutoff energy (ecutwfc) [Ry]"),
                          L("例 30, 40, 50, 60", "e.g. 30, 40, 50, 60"), raise_cut))
    elif code == "vasp":
        out.append(Choice("method.encut", L("カットオフ (ENCUT) [eV]", "Cutoff energy (ENCUT) [eV]"),
                          L("例 300, 400, 500, 600", "e.g. 300, 400, 500, 600"), raise_cut))
    if periodic:
        out.append(Choice("kpoints.mesh", L("k 点の分割数", "k-point mesh"),
                          L("例 4x4x4, 6x6x6, 8x8x8", "e.g. 4x4x4, 6x6x6, 8x8x8"),
                          L("k 点を細かくしていき、エネルギーがほとんど変わらなくなる所を探します。3 方向の分割数を 4x4x4 の形で書きます。",
                            "Use finer k-point meshes and find where the energy stops changing. Write each mesh as 4x4x4.")))
        out.append(Choice("kpoints.density", L("k 点の密度 [点/Å⁻¹]", "k-point density [points/Å⁻¹]"),
                          L("例 2, 3, 4, 5", "e.g. 2, 3, 4, 5"),
                          L("k 点の密度を上げていき、エネルギーがほとんど変わらなくなる所を探します。分割数はセルの形に合わせて決まります。",
                            "Increase the k-point density and find where the energy stops changing. The mesh follows the shape of the cell.")))
        out.append(Choice("scale", L("格子の大きさ (セルの伸び縮み)", "Lattice size (cell scaling)"),
                          L("例 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03", "e.g. 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03"),
                          L("セルと原子の位置を同じ倍率で伸び縮みさせます (1.00 がいまの構造)。5 点以上あると状態方程式を当てはめ、"
                            "平衡の格子定数と体積弾性率を求めます。",
                            "Scales the cell and atom positions by the same factor (1.00 is the current structure). With five or more points, "
                            "ADIT fits an equation of state to give the equilibrium lattice constant and bulk modulus.")))
    out.append(Choice(OTHER, L("その他 (項目の場所を書く)", "Other (type the setting path)"),
                      L("例 1e-5, 1e-6, 1e-7", "e.g. 1e-5, 1e-6, 1e-7"),
                      L("計算設定 (spec.json) の中の項目を、ドットでつないだ場所で指定します。",
                        "Name any setting in the calculation settings (spec.json) by its dotted path.")))
    return out


def all_choices() -> list[tuple[Choice, str, bool]]:
    seen: dict[str, tuple[Choice, str, bool]] = {}
    for code in ("espresso", "vasp", "dftbplus"):
        for periodic in (False, True):
            for c in choices_for(code, periodic):
                if c.path in seen:
                    continue
                only_code = code if c.path.startswith("method.") else ""
                seen[c.path] = (c, only_code, periodic and c.path != OTHER)
    order = ["method.ecutwfc", "method.encut", "kpoints.mesh", "kpoints.density", "scale", OTHER]
    return [seen[p] for p in order]
