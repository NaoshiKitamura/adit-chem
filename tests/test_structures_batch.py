
import csv
from pathlib import Path

import pytest
from ase.build import molecule
from ase.io import write

from adit.cli import main as gen_main
from adit.config import save_config
from adit.report import load_run_report, results_csv
from adit.structures_batch import StructuresError, load_structures, write_structures
from adit.spec import Task
from tests.conftest import cfg_for, water_spec


@pytest.fixture
def mols(tmp_path) -> Path:
    d = tmp_path / "mols"
    d.mkdir()
    for name in ("H2O", "NH3"):
        write(d / f"{name}.xyz", molecule(name))
    return d


def spec_for(**kw):
    return water_spec(task=Task(type="single_point"), **kw)


def test_one_directory_per_structure(mols, sk_root, tmp_path):
    out = tmp_path / "batch"
    dirs = write_structures(spec_for(), cfg_for(sk_root), out, [str(mols / "*.xyz")])
    assert sorted(d.name for d in dirs) == ["H2O", "NH3"]
    assert (out / "structures.json").is_file() and (out / "README.txt").is_file()
    from adit.spec import CalculationSpec
    nh3 = CalculationSpec.load(out / "NH3" / "spec.json")
    assert nh3.atoms.get_chemical_formula() == "H3N" and nh3.method.sk_set == "fake-1-0"
    assert nh3.structure.source == "file" and nh3.structure.source_ref.endswith("NH3.xyz")


def test_multi_frame_file_becomes_several_runs(tmp_path, sk_root):
    path = tmp_path / "conformers.xyz"
    write(path, [molecule("H2O"), molecule("H2O")], format="extxyz")
    loaded = load_structures([str(path)])
    assert [x.name for x in loaded] == ["conformers_001", "conformers_002"]
    dirs = write_structures(spec_for(), cfg_for(sk_root), tmp_path / "out", [str(path)])
    assert len(dirs) == 2


def test_missing_or_unreadable_files_stop_before_writing(tmp_path, sk_root, mols):
    out = tmp_path / "batch"
    with pytest.raises(StructuresError):
        write_structures(spec_for(), cfg_for(sk_root), out, [str(tmp_path / "nope*.xyz")])
    assert not out.exists()
    broken = tmp_path / "broken.xyz"
    broken.write_text("これは構造ではありません\n", encoding="utf-8")
    with pytest.raises(StructuresError):
        write_structures(spec_for(), cfg_for(sk_root), out, [str(broken)])


def test_same_directory_name_is_refused(tmp_path, sk_root):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    write(a / "mol.xyz", molecule("H2O"))
    write(b / "mol.xyz", molecule("NH3"))
    with pytest.raises(StructuresError):
        load_structures([str(a / "mol.xyz"), str(b / "mol.xyz")])


def test_cli_generates_the_batch(mols, sk_root, tmp_path):
    cfg_path = tmp_path / "cluster.toml"
    save_config(cfg_for(sk_root), cfg_path)
    spec_path = tmp_path / "spec.json"
    spec_for().save(spec_path)
    out = tmp_path / "batch"
    assert gen_main([str(spec_path), str(out), "--structures", str(mols / "*.xyz"), "--config", str(cfg_path)]) == 0
    assert (out / "H2O" / "dftb_in.hsd").is_file() and (out / "NH3" / "dftb_in.hsd").is_file()


def test_results_csv_says_what_it_could_not_read(mols, sk_root, tmp_path):
    out = tmp_path / "batch"
    dirs = write_structures(spec_for(), cfg_for(sk_root), out, [str(mols / "*.xyz")])
    rows = list(csv.DictReader(results_csv([load_run_report(d) for d in dirs]).splitlines()))
    assert [r["state"] for r in rows] == ["not_run", "not_run"]
    assert all(r["final_energy_ev"] == "" for r in rows)
    (dirs[0] / "output.log").write_text("Total Energy:  -4.0 H\n", encoding="utf-8")
    rows = list(csv.DictReader(results_csv([load_run_report(d) for d in dirs]).splitlines()))
    assert rows[0]["state"] == "read" and rows[1]["state"] == "not_run"
