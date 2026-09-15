import json
from pathlib import Path

import pytest

from adit.native_verify import verify_generated_bundle


def make_bundle(tmp_path, code="vasp"):
    from ase import Atoms
    from adit.spec import AtomsData, CalculationSpec, EspressoMethod, KPoints, Structure, VaspMethod
    from adit.codes.vasp import VaspGenerator
    from adit.codes.espresso import EspressoGenerator
    method = VaspMethod(encut=400, ediff=1e-8) if code == "vasp" else EspressoMethod(ecutwfc=40, pseudo={"Si": "Si.UPF", "H": "H.UPF"})
    source = CalculationSpec(structure=Structure(source="file", source_ref="fixture", atoms=AtomsData.from_ase(
        Atoms("SiHSi", positions=[[0, 0, 0], [1, 1, 1], [2, 2, 2]], cell=[5, 5, 5], pbc=True))), method=method, kpoints=KPoints())
    source.save(tmp_path / "spec.json")
    if code == "vasp":
        gen = VaspGenerator()
        texts = {"INCAR": gen.incar(source, None), "POSCAR": gen.poscar(source), "KPOINTS": gen.kpoints(source)}
    else:
        texts = {"pw.in": EspressoGenerator().pw_in(source, None)}
    for name, text in texts.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return source


@pytest.mark.parametrize("code", ["vasp", "espresso"])
def test_mapped_fields_and_atom_order_are_preserved(tmp_path, code):
    make_bundle(tmp_path, code)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = verify_generated_bundle(tmp_path)
    assert not result.mismatched, result.report()
    names = {x["field"] for x in result.preserved}
    assert {"structure.atoms.positions", "structure.atoms.symbols", "kpoints.mesh", "task.type"} <= names
    assert result.unverifiable  # never claim whole-calculation equivalence
    assert "equivalence" not in result.report()  # not a blanket boolean
    json.dumps(result.report())
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_changed_tiny_scf_threshold_is_detected(tmp_path):
    make_bundle(tmp_path)
    path = tmp_path / "INCAR"
    path.write_text(path.read_text(encoding="utf-8").replace("EDIFF = 1e-08", "EDIFF = 2e-08"), encoding="utf-8")
    result = verify_generated_bundle(tmp_path)
    assert any(x["field"] == "method.ediff" for x in result.mismatched), result.report()


def test_changed_position_is_detected(tmp_path):
    make_bundle(tmp_path)
    path = tmp_path / "POSCAR"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[8] = "0.1 0.0 0.0"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = verify_generated_bundle(tmp_path)
    assert any(x["field"] == "structure.atoms.positions" for x in result.mismatched)


def test_unknown_keyword_is_unverifiable_not_success(tmp_path):
    make_bundle(tmp_path)
    path = tmp_path / "INCAR"
    path.write_text(path.read_text(encoding="utf-8") + "UNMAPPED_FEATURE = 1\n", encoding="utf-8")
    result = verify_generated_bundle(tmp_path)
    assert any(x.get("text") == "UNMAPPED_FEATURE = 1" for x in result.unverifiable)
    assert not any(x["field"] == "structure.atoms.positions" for x in result.preserved)


@pytest.mark.parametrize("units", ["metal", "real"])
def test_lammps_md_units_and_seed_verification(tmp_path, units):
    from tests.test_native_import import generated_lammps_md
    source = generated_lammps_md(tmp_path, units=units)
    source.save(tmp_path / "spec.json")
    result = verify_generated_bundle(tmp_path)
    assert not result.mismatched, result.report()
    names = {x["field"] for x in result.preserved}
    assert {"task.md.timestep_fs", "task.md.coupling_time_fs", "method.seed"} <= names


def test_external_lammps_coordinates_are_unverifiable(tmp_path):
    from tests.test_native_import import generated_lammps_md
    source = generated_lammps_md(tmp_path)
    source.method.data_file = str(tmp_path / "data.lammps")
    source.save(tmp_path / "spec.json")
    result = verify_generated_bundle(tmp_path)
    assert any(x["field"] == "structure.atoms" for x in result.unverifiable)
    assert not any(x["field"] == "structure.atoms.positions" for x in result.preserved)


def test_missing_spec_reports_unverifiable(tmp_path):
    result = verify_generated_bundle(tmp_path)
    assert not result.preserved and not result.mismatched
    assert result.unverifiable[0]["field"] == "bundle"


def test_qe_multistage_example_does_not_report_false_task_or_pseudo_mismatch():
    bundle = Path(__file__).parents[1] / "examples" / "qe_si_phonon_generated"
    result = verify_generated_bundle(bundle)
    assert not any(x["field"] in {"task.type", "method.pseudo"} for x in result.mismatched)
    assert {"task.type", "method.pseudo"} <= {x["field"] for x in result.unverifiable}
