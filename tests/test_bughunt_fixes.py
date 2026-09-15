
import math

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk

from tests.conftest import cfg_for, pbs_profile, water_spec
from adit.spec import AtomsData, BandSettings, DftbMethod, EspressoMethod, KPoints, MDSettings, Runtime, Structure, Task
from adit.validate import validate


def _si(**kw):
    si = bulk("Si", "diamond", a=5.43)
    base = water_spec(method=DftbMethod(sk_set="fake-1-0"))
    return base.model_copy(update={"structure": Structure(source="bulk", source_ref="Si", atoms=AtomsData.from_ase(si)),
                                   "kpoints": KPoints(mode="mesh", mesh=(2, 2, 2)), **kw})


def _errs(spec, cfg=None):
    return validate(spec, cfg or cfg_for(None))


def test_nan_and_inf_are_stopped_before_anything_else():
    spec = water_spec(method=DftbMethod(sk_set="fake-1-0", scc_tolerance=math.nan))
    errs = _errs(spec)
    assert [e.location for e in errs] == ["method.scc_tolerance"] and "有限" in errs[0].message
    kp = _si(kpoints=KPoints(mode="density", density=math.inf))
    assert [e.location for e in _errs(kp)] == ["kpoints.density"]
    t = water_spec(method=DftbMethod(sk_set="fake-1-0"), task=Task(type="molecular_dynamics", md=MDSettings(temperature_k=math.nan)))
    assert [e.location for e in _errs(t)] == ["task.md.temperature_k"]


def test_unreadable_band_path_is_a_validation_error():
    errs = [e for e in _errs(_si(task=Task(type="band_structure", bands=BandSettings(path="QQQ")))) if e.location == "task.bands.path"]
    assert errs and "G" in errs[0].message
    assert not [e for e in _errs(_si(task=Task(type="band_structure", bands=BandSettings(path="GXL")))) if e.location == "task.bands.path"]
    assert [e for e in _errs(_si(task=Task(type="band_structure", bands=BandSettings(path=",")))) if e.location == "task.bands.path"]


def test_negative_empty_bands_rejected():
    assert "task.bands.empty_bands" in [e.location for e in _errs(_si(task=Task(type="band_structure", bands=BandSettings(empty_bands=-100))))]


def test_job_name_for_cluster_must_be_ascii_without_spaces(sk_root):
    cfg = cfg_for(sk_root); cfg.profiles["cluster"] = pbs_profile()
    for bad in ("水 計算", "my job", "1run"):
        spec = water_spec(method=DftbMethod(sk_set="fake-1-0"), runtime=Runtime(profile="cluster", job_name=bad))
        assert "runtime.job_name" in [e.location for e in _errs(spec, cfg)], bad
    ok = water_spec(method=DftbMethod(sk_set="fake-1-0"), runtime=Runtime(profile="cluster", job_name="water_opt-1"))
    assert "runtime.job_name" not in [e.location for e in _errs(ok, cfg)]
    local = water_spec(method=DftbMethod(sk_set="fake-1-0"), runtime=Runtime(profile="local", job_name="水 計算"))
    assert "runtime.job_name" not in [e.location for e in _errs(local, cfg)]


def test_espresso_extra_names_with_spaces_rejected():
    spec = _si(method=EspressoMethod(pseudo_set="x", ecutwfc=30, extra={"system": {"bad key": 1}}))
    assert "method.extra" in [e.location for e in _errs(spec)]


def test_huge_charge_does_not_add_a_confusing_parity_line():
    spec = water_spec(method=DftbMethod(sk_set="fake-1-0"))
    spec = spec.model_copy(update={"structure": spec.structure.model_copy(update={"charge": 1000})})
    msgs = [e.message for e in _errs(spec)]
    assert any("電子数が負" in m for m in msgs) and not any("不対電子" in m for m in msgs)


def test_empty_smiles_is_a_structure_error():
    pytest.importorskip("rdkit")
    from adit.structure import StructureError, from_smiles
    with pytest.raises(StructureError):
        from_smiles("")


def test_truncated_hessian_gives_a_readable_error():
    from adit.analysis.readers import frequencies_from_hessian
    with pytest.raises(ValueError, match="hessian.out"):
        frequencies_from_hessian(np.zeros(3), Atoms("OHH", positions=[(0, 0, 0), (0, 0, 1), (0, 1, 0)]))


def test_dftb_npt_barostat_in_generated_input(sk_root):
    from adit.project import build_project
    c = bulk("C", "diamond", a=3.567, cubic=True)
    spec = water_spec(method=DftbMethod(sk_set="fake-1-0")).model_copy(update={
        "structure": Structure(source="bulk", source_ref="C", atoms=AtomsData.from_ase(c)), "kpoints": KPoints(mode="mesh", mesh=(1, 1, 1)),
        "task": Task(type="molecular_dynamics", md=MDSettings(ensemble="NPT", thermostat="berendsen", steps=2))})
    hsd = build_project(spec, cfg_for(sk_root)).texts["dftb_in.hsd"]
    assert "Barostat {" in hsd and "Barostat = Berendsen" not in hsd
