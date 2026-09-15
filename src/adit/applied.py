
from __future__ import annotations

from adit.lang import L
from adit.spec import CalculationSpec

_OPT_FIELDS = ("task.optimizer", "task.force_tolerance_ev_per_ang", "task.max_steps")
_USES_OPTIMIZER = ("cp2k", "lammps", "mlip")
_MD_PRESSURE_FIELDS = ("pressure_bar", "barostat_time_fs")
_EXTERNAL_TOPOLOGY_CODES = ("amber", "namd", "openmm", "gromacs", "lammps")


def _add(out: dict, path: str, value, reason: str) -> None:
    out[path] = {"value": value, "reason": reason}


def code_specific_unapplied(spec: CalculationSpec) -> dict[str, dict]:
    out: dict[str, dict] = {}
    code, task, structure = spec.method.code, spec.task, spec.structure
    limited = L("この限定生成器には対応する入力項目がありません。",
                "This limited generator has no corresponding input setting.")
    if task.type == "geometry_optimization":
        if code not in _USES_OPTIMIZER and "task.optimizer" not in out:
            _add(out, "task.optimizer", task.optimizer, L(
                f"{code} の生成器は、共通の「最適化の方法」を入力へ写しません (そのコード自身の方法で最適化します)。",
                f"the {code} generator does not write the shared optimizer choice; the code's own optimizer is used."))
        if code in ("grrm", "amber"):
            fields = ["task.optimizer", "task.force_tolerance_ev_per_ang"] + (["task.max_steps"] if code == "grrm" else [])
            for path in fields:
                _add(out, path, getattr(task, path.removeprefix("task.")), limited)
        if code == "psi4":
            for path in ("task.optimizer", "task.force_tolerance_ev_per_ang"):
                _add(out, path, getattr(task, path.removeprefix("task.")), L(
                    "Psi4 の optimize() には最適化の方法と力の閾値を渡していません (Psi4 の既定で動きます。書くのは geom_maxiter だけ)。",
                    "optimize() is called without an optimizer or force threshold, so Psi4's own defaults apply; only geom_maxiter is written."))
        if code == "abinit":
            _add(out, "task.optimizer", task.optimizer, L(
                "この ABINIT 生成器は ionmov 2 (Broyden) に固定しています。",
                "this ABINIT generator always uses ionmov 2 (Broyden)."))
        if code == "openmm":
            _add(out, "task.optimizer", task.optimizer, L(
                "OpenMM の LocalEnergyMinimizer に最適化の方法の選択はありません。",
                "OpenMM's LocalEnergyMinimizer offers no choice of optimizer."))
    if task.type == "molecular_dynamics":
        md = task.md
        if code in ("namd", "openmm") and md.ensemble == "NVE":
            for field in ("thermostat", "coupling_time_fs") + _MD_PRESSURE_FIELDS:
                _add(out, f"task.md.{field}", getattr(md, field),
                     L("NVE ではこの項目を使いません。", "NVE does not use this setting."))
        if code == "openmm" and md.ensemble == "NPT":
            _add(out, "task.md.barostat_time_fs", md.barostat_time_fs, L(
                "OpenMM の圧力浴 (MonteCarloBarostat) は体積を試す間隔 (ステップ数) で指定するので、時定数を機械的に換算できません。",
                "The OpenMM barostat (MonteCarloBarostat) takes a volume-move interval in steps, so a coupling time cannot be converted mechanically."))
        if code == "vasp":
            from adit.codes.vasp import md_unapplied_settings

            out.update(md_unapplied_settings(spec))
    if code in ("amber", "namd", "openmm"):
        _add(out, "structure.charge", structure.charge, L(
            "原子電荷は外部トポロジーから読み、Spec の全電荷は入力へ書きません。",
            "Atomic charges come from the external topology; the spec's total charge is not written."))
        _add(out, "structure.multiplicity", structure.multiplicity, L(
            "古典力場の入力にスピン多重度はありません。", "A classical force-field input has no spin multiplicity."))
    return out


def unapplied_settings(spec: CalculationSpec) -> dict[str, dict]:
    out = code_specific_unapplied(spec)
    code, task, structure = spec.method.code, spec.task, spec.structure
    if task.type != "geometry_optimization":
        for path in _OPT_FIELDS:
            if path == "task.max_steps" and task.type == "molecular_dynamics":
                continue
            _add(out, path, getattr(task, path.removeprefix("task.")), L(
                "構造を動かさない計算では使いません。", "not used by a task that does not move the atoms."))
    if task.type == "molecular_dynamics":
        md = task.md
        _add(out, "task.max_steps", task.max_steps, L(
            "MD のステップ数は task.md.steps です。この欄は入力に書かれません。",
            "the number of MD steps is task.md.steps; this field is not written into the input."))
        if md.ensemble == "NVE":
            for field in ("thermostat", "coupling_time_fs") + _MD_PRESSURE_FIELDS:
                out.setdefault(f"task.md.{field}", {"value": getattr(md, field),
                                                    "reason": L("NVE ではこの項目を使いません。",
                                                                "NVE does not use this setting.")})
        elif md.ensemble == "NVT":
            for field in _MD_PRESSURE_FIELDS:
                out.setdefault(f"task.md.{field}", {"value": getattr(md, field),
                                                    "reason": L("NVT では圧力の項目を使いません。",
                                                                "NVT does not use the pressure settings.")})
    if not any(structure.atoms.pbc):
        _add(out, "task.relax_cell", task.relax_cell, L(
            "非周期系にセルはありません。", "a nonperiodic system has no cell to relax."))
    if code in _EXTERNAL_TOPOLOGY_CODES or code == "mlip":
        reason_charge = (L("原子電荷は外部のトポロジー・力場から読み、Spec の全電荷は入力へ書きません。",
                           "Atomic charges come from the external topology or force field; the spec's total charge is not written.")
                         if code != "mlip" else
                         L("この機械学習ポテンシャルは全電荷を入力に取りません。",
                           "this machine-learning potential takes no total charge."))
        out.setdefault("structure.charge", {"value": structure.charge, "reason": reason_charge})
        out.setdefault("structure.multiplicity", {"value": structure.multiplicity, "reason": L(
            "古典力場・機械学習ポテンシャルの入力にスピン多重度はありません。",
            "a classical force field or machine-learning potential input has no spin multiplicity.")})
    return out
