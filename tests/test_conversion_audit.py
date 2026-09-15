"""Regression checks for the field-level conversion record."""

from __future__ import annotations

import pytest

from adit.convert import ConversionError, retarget_spec
from adit.spec import GromacsMethod, LammpsMethod, MDSettings, Task, VaspMethod
from tests.conftest import water_spec


def _entries(report):
    return {entry["path"]: entry for entry in report["field_audit"]["entries"]}


def test_audit_never_claims_physical_equivalence():
    source = water_spec(method=LammpsMethod(), task=Task(type="molecular_dynamics", md=MDSettings(
        ensemble="NVT", thermostat="nose_hoover", timestep_fs=0.25, temperature_k=425,
        coupling_time_fs=75)))
    source.structure.velocities = [(0.1, 0.2, 0.3)] * len(source.atoms)
    target = water_spec(method=VaspMethod(extra_incar={"SMASS": 2}), task=Task(md=MDSettings(thermostat="langevin")))
    _, report = retarget_spec(source, target, use_target_thermostat=True, no_velocities=True)
    audit = report["field_audit"]
    rows = _entries(report)
    assert audit["equivalence_claim"] == "none"
    assert rows["task.md.temperature_k"]["status"] == "preserved"
    assert rows["task.md.temperature_k"]["unit"] == "K"
    assert rows["task.md.thermostat"]["status"] == "changed_by_request"
    assert rows["structure.velocities"]["status"] == "omitted_by_request"
    assert rows["task.md.coupling_time_fs"]["status"] == "preserved"
    assert rows["method"]["status"] == "not_translated"
    assert rows["kpoints"]["status"] == "from_target_template"
    assert rows["task.optimizer"]["status"] == "not_used_by_task"


def test_audit_marks_vasp_nose_hoover_time_as_not_applied():
    source = water_spec(method=LammpsMethod(), task=Task(type="molecular_dynamics", md=MDSettings(
        ensemble="NVT", thermostat="nose_hoover", coupling_time_fs=75)))
    target = water_spec(method=VaspMethod(extra_incar={"SMASS": 2}))
    _, report = retarget_spec(source, target)
    assert _entries(report)["task.md.coupling_time_fs"]["status"] == "retained_in_spec_not_input"


def test_audit_is_compact_for_large_structures():
    source = water_spec(method=LammpsMethod())
    source.structure.atoms.positions *= 100
    source.structure.atoms.symbols *= 100
    target = water_spec(method=VaspMethod())
    _, report = retarget_spec(source, target)
    rows = _entries(report)
    assert "source_value" not in rows["structure.atoms.positions"]
    assert "target_value" not in rows["structure.atoms.positions"]


@pytest.mark.parametrize("method", [
    LammpsMethod(data_file="external.data"),
    GromacsMethod(topology_file="external.top", structure_file="external.gro"),
])
def test_external_topology_cannot_be_silently_retargeted(method):
    source = water_spec(method=method)
    target = water_spec(method=VaspMethod())
    with pytest.raises(ConversionError, match="外部|external"):
        retarget_spec(source, target)
