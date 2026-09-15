"""NWChem official-input subset; the executable is not available for a live run.

Inputs: https://nwchemgit.github.io/Getting-Started.html
Outputs: https://nwchemgit.github.io/Sample.html
"""

import pytest

from tests.conftest import cfg_for, water_spec
from adit.analysis.readers import HARTREE_EV, load_run
from adit.analysis.report import run_analysis
from adit.cli import main as generate_main
from adit.config import save_config
from adit.convert import retarget_spec
from adit.project import ProjectError, build_project
from adit.results import summarize_run
from adit.spec import AtomsData, CalculationSpec, NwchemMethod, OrcaMethod, Runtime, Structure, Task


def _spec(method, **kwargs):
    return water_spec(method=method, task=Task(type="single_point"), runtime=Runtime(profile="local"), **kwargs)


def test_nwchem_dft_single_point_has_explicit_method_and_geometry(sk_root, tmp_path):
    method = NwchemMethod(theory="dft", basis="cc-pvdz", xc="b3lyp")
    spec = _spec(method)
    spec.save(tmp_path / "spec.json")
    loaded = CalculationSpec.load(tmp_path / "spec.json")
    assert loaded.method == method
    files = build_project(loaded, cfg_for(sk_root))
    inp = files.texts["nwchem.nw"]
    assert "geometry units angstroms noautosym nocenter noautoz\n" in inp
    assert inp.count("\n  O ") == 1 and inp.count("\n  H ") == 2
    assert "charge 0\nbasis\n  * library cc-pvdz\nend\ndft\n  xc b3lyp\n  mult 1\nend\ntask dft energy\n" in inp
    assert "nwchem nwchem.nw > output.log 2>&1" in files.texts["submit.sh"]
    assert "NWChem" in files.texts["README.txt"]


def test_nwchem_scf_closed_shell_and_dft_open_shell(sk_root):
    scf = build_project(_spec(NwchemMethod(theory="scf", basis="cc-pvdz")), cfg_for(sk_root)).texts["nwchem.nw"]
    assert "scf\n  singlet\nend\ntask scf energy" in scf
    spec = _spec(NwchemMethod(theory="dft", basis="cc-pvdz", xc="b3lyp"))
    spec.structure.charge = 1
    spec.structure.multiplicity = 2
    inp = build_project(spec, cfg_for(sk_root)).texts["nwchem.nw"]
    assert "charge 1" in inp and "  mult 2" in inp


@pytest.mark.parametrize("method", [NwchemMethod(), NwchemMethod(theory="dft", basis="cc-pvdz"),
                                     NwchemMethod(theory="scf", basis="cc-pvdz", xc="b3lyp"),
                                     NwchemMethod(theory="dft", basis="cc-pvdz\ntask dft energy", xc="b3lyp")])
def test_nwchem_missing_or_injected_settings_stop(sk_root, method):
    with pytest.raises(ProjectError):
        build_project(_spec(method), cfg_for(sk_root))


def test_nwchem_rejects_unmapped_tasks_periodicity_and_constraints(sk_root):
    m = NwchemMethod(theory="dft", basis="cc-pvdz", xc="b3lyp")
    with pytest.raises(ProjectError) as ex:
        build_project(water_spec(method=m, task=Task(type="geometry_optimization")), cfg_for(sk_root))
    assert any(e.location == "task.type" for e in ex.value.errors)
    spec = _spec(m)
    spec.structure.fixed_atoms = [0]
    with pytest.raises(ProjectError) as ex:
        build_project(spec, cfg_for(sk_root))
    assert any(e.location == "structure.fixed_atoms" for e in ex.value.errors)
    spec = _spec(m)
    st = spec.structure
    atoms = AtomsData(**{**st.atoms.model_dump(), "cell": [(10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0)], "pbc": (True, True, True)})
    spec = spec.model_copy(update={"structure": Structure(**{**st.model_dump(), "atoms": atoms})})
    with pytest.raises(ProjectError) as ex:
        build_project(spec, cfg_for(sk_root))
    assert any(e.location == "structure.atoms" for e in ex.value.errors)


def test_nwchem_parallel_needs_explicit_launch_command(sk_root):
    m = NwchemMethod(theory="scf", basis="cc-pvdz")
    spec = water_spec(method=m, task=Task(type="single_point"), runtime=Runtime(profile="local", mpiprocs=2))
    with pytest.raises(ProjectError) as ex:
        build_project(spec, cfg_for(sk_root))
    assert any(e.location == "runtime.profile" for e in ex.value.errors)


def test_nwchem_reader_uses_total_energy_only(tmp_path):
    (tmp_path / "nwchem.nw").write_text("task dft energy\n", encoding="utf-8")
    (tmp_path / "output.log").write_text(" Total DFT energy = -76.123456\nOne electron energy = -120.0\n", encoding="utf-8")
    data = load_run(tmp_path)
    assert data.code == "nwchem" and data.energies_ev == pytest.approx([-76.123456 * HARTREE_EV])
    assert not data.frames and data.notes
    result = run_analysis(tmp_path)
    assert result.code == "nwchem" and (tmp_path / "analysis" / "summary.json").is_file()
    summary = summarize_run(tmp_path)
    assert summary.mermin_energy_hartree is None
    assert summary.finished is None and not summary.converged
    assert "未判定" in summary.status_line()


def test_nwchem_cli_generates_without_running(sk_root, tmp_path):
    cfg_path = tmp_path / "cluster.toml"
    save_config(cfg_for(sk_root), cfg_path)
    spec_path = tmp_path / "spec.json"
    _spec(NwchemMethod(theory="scf", basis="cc-pvdz")).save(spec_path)
    out = tmp_path / "nwchem_run"
    assert generate_main([str(spec_path), str(out), "--config", str(cfg_path)]) == 0
    assert (out / "nwchem.nw").is_file() and (out / "submit.sh").is_file()
    assert not (out / "output.log").exists()


def test_orca_to_nwchem_uses_explicit_target_method(sk_root):
    source = water_spec(method=OrcaMethod(method="B3LYP", basis="def2-SVP"),
                        task=Task(type="single_point"), runtime=Runtime(profile="local"))
    target = _spec(NwchemMethod(theory="dft", basis="cc-pvdz", xc="b3lyp"))
    converted, report = retarget_spec(source, target)
    assert converted.structure == source.structure and converted.task == source.task
    assert converted.method == target.method
    assert report["source_code"] == "orca" and report["target_code"] == "nwchem"
    assert "* library cc-pvdz" in build_project(converted, cfg_for(sk_root)).texts["nwchem.nw"]
