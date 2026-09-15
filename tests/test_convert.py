
from __future__ import annotations

import json

from ase.io import read, write
from ase import Atoms
import numpy as np
import pytest

from adit.convert import ConversionError, StructureDataLossWarning, combine_xyz, convert_structure, convert_with_openbabel, main, retarget_spec, write_spec_structure
from adit.spec import AtomsData, CalculationSpec, KPoints, LammpsMethod, MDSettings, Task, VaspMethod
from adit.templates import save_template
from tests.conftest import cfg_for, water_spec


def test_structure_conversion_xyz_to_poscar(tmp_path):
    source = tmp_path / "water.xyz"
    target = tmp_path / "POSCAR"
    atoms = water_spec().atoms
    write(source, atoms)
    convert_structure(source, target, output_format="vasp", cell=(18.0, 18.0, 18.0))
    back = read(target, format="vasp")
    assert back.get_chemical_symbols() == atoms.get_chemical_symbols()
    assert len(back) == len(atoms)
    try:
        convert_structure(source, target, output_format="vasp", cell=(18.0, 18.0, 18.0))
    except ConversionError as ex:
        assert "上書き" in str(ex)
    else:
        raise AssertionError("an existing output must not be overwritten silently")


def test_openbabel_backend_is_explicit_and_never_overwrites_implicitly(tmp_path, monkeypatch):
    from subprocess import CompletedProcess
    from adit import convert

    source, target = tmp_path / "source.sdf", tmp_path / "target.mol2"
    source.write_text("test\n", encoding="utf-8")
    seen = []
    monkeypatch.setattr(convert.shutil, "which", lambda name: "/usr/bin/obabel")

    def fake_run(command, **kwargs):
        seen.append(command)
        (tmp_path / command[-1]).write_text("converted\n", encoding="utf-8")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(convert.subprocess, "run", fake_run)
    assert convert_with_openbabel(source, target, input_format="sdf", output_format="mol2") == target
    assert len(seen) == 1
    assert seen[0][:6] == ["/usr/bin/obabel", "-i", "sdf", str(source), "-o", "mol2"]
    assert seen[0][6] == "-O" and seen[0][7].endswith(".mol2")
    with pytest.raises(ConversionError, match="上書きしません|not overwritten"):
        convert_with_openbabel(source, target)
    assert len(seen) == 1
    with pytest.raises(ConversionError, match="同じファイル|the same file"):
        convert_with_openbabel(source, source, overwrite=True)


def test_openbabel_failure_preserves_existing_output(tmp_path, monkeypatch):
    from subprocess import CompletedProcess
    from adit import convert

    source, target = tmp_path / "source.sdf", tmp_path / "target.mol2"
    source.write_text("source\n", encoding="utf-8")
    target.write_text("original\n", encoding="utf-8")
    monkeypatch.setattr(convert.shutil, "which", lambda name: "/usr/bin/obabel")

    def failed_run(command, **kwargs):
        (tmp_path / command[-1]).write_text("partial\n", encoding="utf-8")
        return CompletedProcess(command, 1, "", "invalid input")

    monkeypatch.setattr(convert.subprocess, "run", failed_run)
    with pytest.raises(ConversionError, match="途中ファイル|Staged file"):
        convert_with_openbabel(source, target, overwrite=True)
    assert target.read_text(encoding="utf-8") == "original\n"


@pytest.mark.parametrize("language", ["ja", "en"])
def test_combine_xyz_preserves_order_and_positions_without_overwriting(tmp_path, monkeypatch, capsys, language):
    from adit import lang

    monkeypatch.setattr(lang, "LANGUAGE", language)
    first, second, out = (tmp_path / name for name in ("first.xyz", "second.xyz", "joined.xyz"))
    a = Atoms("OH", positions=[(0, 0, 0), (0, 0, 1.0)])
    b = Atoms("LiF", positions=[(4, 0, 0), (5, 0, 0)])
    write(first, a, format="xyz")
    write(second, b, format="xyz")
    assert main(["combine", str(first), str(second), str(out)]) == 0
    joined = read(out, format="xyz")
    assert joined.get_chemical_symbols() == ["O", "H", "Li", "F"]
    np.testing.assert_allclose(joined.positions, np.vstack([a.positions, b.positions]))
    original = out.read_bytes()
    assert main(["combine", str(first), str(second), str(out)]) == 1
    assert out.read_bytes() == original
    assert ("上書きしません" if language == "ja" else "not overwritten") in capsys.readouterr().err


def test_combine_xyz_rejects_multiframe_and_source_output_alias(tmp_path):
    first, second, out = (tmp_path / name for name in ("first.xyz", "second.xyz", "out.xyz"))
    write(first, Atoms("H", positions=[(0, 0, 0)]), format="xyz")
    write(second, Atoms("O", positions=[(2, 0, 0)]), format="xyz")
    with first.open("a", encoding="utf-8") as stream:
        stream.write(second.read_text(encoding="utf-8"))
    with pytest.raises(ConversionError, match="複数フレーム|multiple frames"):
        combine_xyz([first, second], out)
    assert not out.exists()
    with pytest.raises(ConversionError, match="同じファイル|must not be one"):
        combine_xyz([first, second], first, overwrite=True)


def test_combine_xyz_rejects_declared_oversized_input_before_reading(tmp_path):
    first, second, out = (tmp_path / name for name in ("large.xyz", "second.xyz", "out.xyz"))
    first.write_text("50001\nheader only\n", encoding="utf-8")
    write(second, Atoms("H", positions=[(0, 0, 0)]), format="xyz")
    with pytest.raises(ConversionError, match="上限|limit"):
        combine_xyz([first, second], out)
    assert not out.exists()


def test_combine_xyz_rejects_extended_metadata_in_xyz_named_file(tmp_path):
    first, second, out = (tmp_path / name for name in ("periodic.xyz", "plain.xyz", "out.xyz"))
    write(first, Atoms("H", positions=[(0, 0, 0)], cell=[10, 10, 10], pbc=True), format="extxyz")
    write(second, Atoms("H", positions=[(1, 0, 0)]), format="xyz")
    with pytest.raises(ConversionError, match="拡張 XYZ|extended XYZ"):
        combine_xyz([first, second], out)
    assert not out.exists()


@pytest.mark.parametrize("language,invalid,message", [
    ("ja", "nan", "有限で 0 より大きい"),
    ("en", "inf", "finite and greater than zero"),
    ("ja", "abc", "数値を指定"),
    ("en", "abc", "requires numeric values"),
])
def test_structure_cli_rejects_invalid_cell_lengths_before_writing(tmp_path, monkeypatch, capsys, language, invalid, message):
    from adit import lang

    monkeypatch.setattr(lang, "LANGUAGE", language)
    source = tmp_path / "water.xyz"
    target = tmp_path / "POSCAR"
    write(source, water_spec().atoms)
    assert main(["structure", str(source), str(target), "--cell", invalid]) == 1
    assert message in capsys.readouterr().err
    assert not target.exists()


def test_save_current_spec_structure_is_non_destructive(tmp_path):
    out = tmp_path / "water.extxyz"
    base = water_spec()
    spec = base.model_copy(update={"structure": base.structure.model_copy(update={
        "fixed_atoms": [0], "fixed_axes": {"1": (False, True, False)}})})
    assert write_spec_structure(spec, out) == out
    saved = read(out)
    assert saved.get_chemical_symbols() == ["O", "H", "H"]
    masks = {int(c.index[0]): tuple(bool(x) for x in c.mask) for c in saved.constraints}
    assert masks[0] == (True, True, True) and masks[1] == (True, False, True)
    with pytest.raises(ConversionError, match="上書きしません|not overwritten"):
        write_spec_structure(water_spec(), out)
    with pytest.raises(ConversionError, match="保存先|output file"):
        write_spec_structure(water_spec(), "")


@pytest.mark.parametrize("via_spec_file", [False, True])
def test_spec_export_preserves_velocities_even_on_fixed_axes(tmp_path, via_spec_file):
    from ase.units import fs

    spec = water_spec()
    spec.structure.fixed_atoms = [0]
    spec.structure.fixed_axes = {"0": (True, False, True), "1": (False, True, False)}
    spec.structure.velocities = [(0.1, -0.2, 0.3), (-0.04, 0.05, 0.06), (0.007, -0.008, 0.009)]
    before = spec.model_dump()
    out = tmp_path / "saved.extxyz"
    if via_spec_file:
        spec.save(tmp_path / "spec.json")
        convert_structure(tmp_path, out)
    else:
        write_spec_structure(spec, out)
    saved = read(out)
    assert saved.has("momenta")
    np.testing.assert_allclose(saved.get_velocities() * fs, spec.structure.velocities, atol=1e-9)
    masks = {int(c.index[0]): tuple(bool(x) for x in c.mask) for c in saved.constraints}
    assert masks[0] == (True, True, True)  # full fixation dominates overlapping axes
    assert masks[1] == (True, False, True)
    assert spec.model_dump() == before


def test_structure_export_without_velocities_does_not_invent_zero_velocities(tmp_path):
    target = tmp_path / "saved.extxyz"
    write_spec_structure(water_spec(), target)
    assert not read(target).has("momenta")


@pytest.mark.parametrize("source_kind", ["spec", "extxyz"])
@pytest.mark.parametrize("cell,movable,expected", [
    ([(12, 0, 0), (0, 13, 0), (0, 0, 14)], (False, True, False), ["F", "T", "F"]),
    ([(0, 13, 0), (-12, 0, 0), (0, 0, 14)], (False, True, False), ["T", "F", "F"]),
    ([(12, 0, 0), (3, 13, 0), (0, 0, 14)], (True, True, False), ["T", "T", "F"]),
])
def test_poscar_export_preserves_cartesian_constraints(tmp_path, source_kind, cell, movable, expected):
    spec = water_spec()
    spec.structure.atoms.cell = cell
    spec.structure.atoms.pbc = (True, True, True)
    spec.structure.fixed_atoms = [0]
    spec.structure.fixed_axes = {"0": (True, False, True), "1": movable}
    before = spec.model_dump()
    source = tmp_path / ("spec.json" if source_kind == "spec" else "source.extxyz")
    if source_kind == "spec":
        spec.save(source)
    else:
        write_spec_structure(spec, source)
    target = tmp_path / "POSCAR"
    assert main(["structure", str(source), str(target)]) == 0
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[7].lower().startswith("selective")
    assert [line.split()[3:] for line in lines[9:12]] == [["F"] * 3, expected, ["T"] * 3]
    restored = read(target)
    np.testing.assert_allclose(restored.cell, cell)
    np.testing.assert_allclose(restored.positions, spec.atoms.positions)
    assert spec.model_dump() == before


@pytest.mark.parametrize("language", ["ja", "en"])
@pytest.mark.parametrize("cell", [
    [(12, 0, 0), (3, 13, 0), (0, 0, 14)],
    [(8, 8, 0), (-8, 8, 0), (0, 0, 14)],
])
def test_poscar_export_rejects_nonrepresentable_axes_before_writing(tmp_path, capsys, monkeypatch, language, cell):
    from adit import lang

    monkeypatch.setattr(lang, "LANGUAGE", language)
    spec = water_spec()
    spec.structure.atoms.cell = cell
    spec.structure.fixed_axes = {"1": (False, True, False)}
    source = tmp_path / "spec.json"
    spec.save(source)
    target = tmp_path / "POSCAR"
    assert main(["structure", str(source), str(target)]) == 1
    error = capsys.readouterr().err
    assert "Cartesian" in error and "Selective dynamics" in error
    assert not target.exists()
    target.write_text("existing structure\n", encoding="utf-8")
    assert main(["structure", str(source), str(target), "--overwrite"]) == 1
    assert target.read_text(encoding="utf-8") == "existing structure\n"


def test_poscar_to_poscar_keeps_native_scaled_constraints_on_skew_cell(tmp_path):
    from ase.constraints import FixAtoms, FixScaled

    atoms = water_spec().atoms
    atoms.set_cell([(12, 0, 0), (3, 13, 0), (0, 0, 14)])
    atoms.set_constraint([FixAtoms([0]), FixScaled(1, mask=(True, False, True))])
    source = tmp_path / "POSCAR"
    write(source, atoms, format="vasp")
    target = tmp_path / "CONTCAR"
    convert_structure(source, target)
    assert [line.split()[3:] for line in target.read_text(encoding="utf-8").splitlines()[9:12]] == [
        ["F", "F", "F"], ["F", "T", "F"], ["T", "T", "T"]]


def test_poscar_export_merges_overlapping_axes_without_losing_velocities(tmp_path):
    from ase.constraints import FixAtoms, FixCartesian
    from ase.units import fs

    atoms = water_spec().atoms
    atoms.set_cell([12, 13, 14])
    velocities = np.asarray([(0.1, 0.2, 0.3)] * 3)
    atoms.set_velocities(velocities / fs)
    atoms.set_constraint([FixAtoms([0]), FixCartesian([0, 1], mask=(True, False, False)),
                          FixCartesian(1, mask=(False, False, True))])
    source = tmp_path / "source.traj"
    write(source, atoms)
    target = tmp_path / "POSCAR"
    convert_structure(source, target)
    lines = target.read_text(encoding="utf-8").splitlines()
    assert [line.split()[3:] for line in lines[9:12]] == [["F"] * 3, ["F", "T", "F"], ["T"] * 3]
    np.testing.assert_allclose(np.asarray([line.split() for line in lines[-3:]], dtype=float), velocities)


@pytest.mark.parametrize("kind,expected", [("plane", ["T", "T", "F"]), ("line", ["F", "F", "T"])])
def test_poscar_export_preserves_line_and_plane_on_skew_cell(tmp_path, kind, expected):
    from ase.constraints import FixedLine, FixedPlane

    atoms = water_spec().atoms
    atoms.set_cell([(12, 0, 0), (3, 13, 0), (0, 0, 14)])
    atoms.set_constraint((FixedPlane if kind == "plane" else FixedLine)(1, (0, 0, 1)))
    source = tmp_path / "source.traj"
    write(source, atoms)
    target = tmp_path / "POSCAR"
    convert_structure(source, target)
    assert target.read_text(encoding="utf-8").splitlines()[10].split()[3:] == expected


def test_poscar_export_rejects_unhandled_constraints(tmp_path):
    from ase.constraints import FixBondLength

    atoms = water_spec().atoms
    atoms.set_cell([12, 13, 14])
    atoms.set_constraint(FixBondLength(0, 1))
    source = tmp_path / "source.traj"
    write(source, atoms)
    target = tmp_path / "POSCAR"
    with pytest.raises(ConversionError, match="FixBondLengths"):
        convert_structure(source, target)
    assert not target.exists()


@pytest.mark.parametrize("language", ["ja", "en"])
@pytest.mark.parametrize("filename", ["saved.cif", "saved.data"])
def test_cli_reports_constraint_loss_and_preserves_supported_velocities(tmp_path, capsys, monkeypatch, language, filename):
    from ase.units import fs
    from adit import lang

    monkeypatch.setattr(lang, "LANGUAGE", language)
    spec = water_spec()
    spec.structure.atoms.cell = [(12, 0, 0), (0, 12, 0), (0, 0, 12)]
    spec.structure.atoms.pbc = (True, True, True)
    spec.structure.fixed_atoms = [0]
    spec.structure.fixed_axes = {"1": (False, True, False)}
    spec.structure.velocities = [(0.1, 0.2, 0.3)] * 3
    source = write_spec_structure(spec, tmp_path / "source.extxyz")
    target = tmp_path / filename
    assert main(["structure", str(source), str(target)]) == 0
    err = capsys.readouterr().err
    assert ("固定原子・軸固定" if language == "ja" else "fixed-atom / fixed-axis constraints") in err
    assert ".extxyz" in err
    if filename.endswith("data"):
        back = read(target, format="lammps-data")
        np.testing.assert_allclose(back.get_velocities() * fs, spec.structure.velocities, atol=1e-9)
        assert not back.constraints
    else:
        assert ("初速度" if language == "ja" else "initial velocities") in err


def test_structure_conversion_api_reports_known_loss(tmp_path):
    from ase.constraints import FixAtoms

    source = tmp_path / "source.extxyz"
    atoms = water_spec().atoms
    atoms.set_constraint(FixAtoms(indices=[0]))
    write(source, atoms)
    with pytest.warns(StructureDataLossWarning, match="extxyz"):
        convert_structure(source, tmp_path / "plain.xyz", output_format="xyz")


@pytest.mark.parametrize("language", ["ja", "en"])
def test_espresso_structure_output_explains_missing_calculation_settings(tmp_path, capsys, monkeypatch, language):
    from adit import lang

    monkeypatch.setattr(lang, "LANGUAGE", language)
    source = write_spec_structure(water_spec(), tmp_path / "source.extxyz")
    target = tmp_path / "pw.in"
    assert main(["structure", str(source), str(target), "--output-format", "espresso-in"]) == 1
    err = capsys.readouterr().err
    assert ("擬ポテンシャル" if language == "ja" else "pseudopotentials") in err
    assert "adit-convert calculation" in err and "adit-gen" in err
    assert not target.exists()


@pytest.mark.parametrize("filename", ["data.lammps", "structure.data"])
def test_structure_conversion_lammps_data_to_cif(tmp_path, filename):
    source = tmp_path / filename
    target = tmp_path / "structure.cif"
    atoms = Atoms("Cu2", positions=[(0, 0, 0), (1.8, 1.8, 1.8)], cell=[3.6, 3.6, 3.6], pbc=True)
    write(source, atoms, format="lammps-data", masses=True, atom_style="atomic")
    convert_structure(source, target)
    back = read(target)
    assert back.get_chemical_symbols() == ["Cu", "Cu"]
    assert back.cell.lengths().tolist() == atoms.cell.lengths().tolist()


@pytest.mark.parametrize("filename", ["H2O.data", "data.lammps", "H2O.data.gz"])
def test_structure_cli_lammps_output_preserves_elements_and_geometry(tmp_path, filename):
    source = tmp_path / "POSCAR"
    atoms = water_spec().atoms
    atoms.set_cell([12.0, 13.0, 14.0])
    atoms.center()
    atoms.pbc = True
    write(source, atoms, format="vasp")
    target = tmp_path / filename
    assert main(["structure", str(source), str(target)]) == 0
    back = read(target, format="lammps-data")
    assert back.get_chemical_symbols() == atoms.get_chemical_symbols()
    assert np.allclose(back.positions, atoms.positions)
    assert np.allclose(back.cell, atoms.cell)
    # The ordinary CLI reverse conversion must also recognize its own output.
    restored = tmp_path / "restored.extxyz"
    assert main(["structure", str(target), str(restored)]) == 0
    assert read(restored).get_chemical_symbols() == atoms.get_chemical_symbols()


def test_explicit_lammps_output_also_writes_masses(tmp_path):
    source = tmp_path / "H2O.extxyz"
    atoms = water_spec().atoms
    atoms.set_cell([12.0, 12.0, 12.0])
    write(source, atoms)
    target = tmp_path / "arbitrary.txt"
    convert_structure(source, target, output_format="lammps-data")
    assert read(target, format="lammps-data").get_chemical_symbols() == atoms.get_chemical_symbols()


def test_data_extension_allows_explicit_runner_and_preserves_input_detection(tmp_path):
    source = tmp_path / "H2O.extxyz"
    atoms = water_spec().atoms
    write(source, atoms)
    target = tmp_path / "input.data"
    convert_structure(source, target, output_format="runnerdata")
    assert target.read_text(encoding="utf-8").startswith("begin")
    restored = tmp_path / "restored.extxyz"
    convert_structure(target, restored)
    assert read(restored).get_chemical_symbols() == atoms.get_chemical_symbols()


def test_lammps_extension_preserves_dump_content_detection(tmp_path):
    source = tmp_path / "trajectory.lammps"
    source.write_text(
        "ITEM: TIMESTEP\n0\nITEM: NUMBER OF ATOMS\n1\n"
        "ITEM: BOX BOUNDS pp pp pp\n0 5\n0 5\n0 5\n"
        "ITEM: ATOMS id element x y z\n1 Cu 1 2 3\n"
    , encoding="utf-8")
    target = tmp_path / "Cu.extxyz"
    convert_structure(source, target)
    assert read(target).get_chemical_symbols() == ["Cu"]


def test_retarget_preserves_shared_conditions_and_uses_target_method():
    source = water_spec(method=LammpsMethod(units="real", pair_style="zero 10.0", pair_coeff="* *"))
    source = source.model_copy(update={
        "task": source.task.model_copy(update={
            "type": "molecular_dynamics",
            "md": source.task.md.model_copy(update={"ensemble": "NVE", "temperature_k": 425.0,
                                                       "timestep_fs": 0.25, "steps": 2400, "dump_interval": 12}),
        })
    })
    target_conditions = water_spec(method=VaspMethod(encut=520.0))
    target_conditions = target_conditions.model_copy(update={"kpoints": None})
    converted, report = retarget_spec(source, target_conditions)
    assert converted.structure == source.structure
    assert converted.task == source.task
    assert converted.runtime == source.runtime
    assert converted.method == target_conditions.method
    assert converted.kpoints == target_conditions.kpoints
    assert converted.handoff is None
    assert report["preserved"] == ["structure", "task", "runtime"]
    assert report["not_translated"] == ["method (lammps -> vasp)"]


def test_retarget_rejects_the_same_code():
    spec = water_spec(method=VaspMethod())
    try:
        retarget_spec(spec, spec)
    except ConversionError as ex:
        assert "どちらも vasp" in str(ex)
    else:
        raise AssertionError("retargeting to the same code must be rejected")


def test_calculation_cli_writes_target_input_and_report(tmp_path):
    from adit.config import save_config

    source = water_spec(method=LammpsMethod(units="real", pair_style="zero 10.0", pair_coeff="* *"))
    atoms = source.atoms
    atoms.set_cell([14.0, 14.0, 14.0]); atoms.center(); atoms.pbc = True
    source = source.model_copy(update={
        "structure": source.structure.model_copy(update={"atoms": AtomsData.from_ase(atoms)}),
        "task": source.task.model_copy(update={"type": "molecular_dynamics", "md": source.task.md.model_copy(update={"ensemble": "NVE"})}),
    })
    target = water_spec(method=VaspMethod(encut=520.0), kpoints=KPoints(mode="gamma"))
    source_file = tmp_path / "source.json"; source.save(source_file)
    template = save_template(target, "vasp-md", directory=tmp_path)
    config = tmp_path / "config.toml"; save_config(cfg_for(None), config)
    output = tmp_path / "converted"
    assert main(["calculation", str(source_file), str(template), str(output), "--config", str(config)]) == 0
    assert (output / "POSCAR").is_file() and (output / "INCAR").is_file()
    report = (output / "conversion.json").read_text(encoding="utf-8")
    assert '"source_code": "lammps"' in report and '"target_code": "vasp"' in report
    made = (output / "spec.json").read_text(encoding="utf-8")
    assert '"temperature_k": 300.0' in made and '"encut": 520.0' in made


def test_retarget_requires_explicit_thermostat_change_and_keeps_shared_md_values():
    source = water_spec(method=LammpsMethod(), task=Task(type="molecular_dynamics", md=MDSettings(
        ensemble="NPT", thermostat="nose_hoover", temperature_k=425, timestep_fs=0.25,
        steps=24, dump_interval=3, coupling_time_fs=75, pressure_bar=2, barostat_time_fs=750)))
    source.structure.velocities = [(0.1, 0.2, 0.3)] * 3
    target = water_spec(method=VaspMethod(), task=Task(md=MDSettings(thermostat="langevin")))
    unchanged, _ = retarget_spec(source, target)
    assert unchanged.task == source.task
    assert unchanged.structure.velocities == source.structure.velocities
    converted, report = retarget_spec(source, target, use_target_thermostat=True, no_velocities=True)
    expected_md = source.task.md.model_dump() | {"thermostat": "langevin"}
    assert converted.task.md.model_dump() == expected_md
    assert converted.structure.velocities is None
    assert source.structure.velocities is not None and source.task.md.thermostat == "nose_hoover"
    assert report["changes"]["task.md.thermostat"] == {"source": "nose_hoover", "target": "langevin"}
    assert report["omitted"] == ["structure.velocities"]
    assert "task.md.coupling_time_fs" in report["preserved"]
    assert "task.md.thermostat" not in report["preserved"]
    assert "structure.velocities" not in report["preserved"]


@pytest.mark.parametrize("task", [Task(), Task(type="molecular_dynamics", md=MDSettings(ensemble="NVE"))])
def test_retarget_thermostat_option_rejects_non_thermostatted_tasks(task):
    with pytest.raises(ConversionError, match="NVT"):
        retarget_spec(water_spec(task=task), water_spec(method=VaspMethod()), use_target_thermostat=True)


def test_retarget_does_not_choose_an_implicit_default_thermostat():
    source = water_spec(task=Task(type="molecular_dynamics"))
    with pytest.raises(ConversionError, match="task.md.thermostat"):
        retarget_spec(source, water_spec(method=VaspMethod()), use_target_thermostat=True)


@pytest.mark.parametrize("language", ["ja", "en"])
def test_calculation_cli_qe_nvt_requires_explicit_changes_and_records_them(tmp_path, monkeypatch, capsys, language):
    from adit import lang
    from adit.config import save_config
    from tests.test_espresso import make_fake_upf, si_spec

    monkeypatch.setattr(lang, "LANGUAGE", language)
    monkeypatch.setenv("ADIT_LANG", language)
    source = si_spec(method=LammpsMethod(), task=Task(type="molecular_dynamics", md=MDSettings(
        thermostat="nose_hoover", temperature_k=425, timestep_fs=0.25, steps=24,
        dump_interval=3, coupling_time_fs=75)))
    source.structure.velocities = [(0.1, 0.2, 0.3)] * len(source.atoms)
    source_file = tmp_path / "source.json"
    source.save(source_file)
    target = si_spec(task=Task(type="molecular_dynamics", md=MDSettings(thermostat="csvr")))
    template = save_template(target, "qe-md", directory=tmp_path)
    cfg = cfg_for(None)
    cfg.pseudo_root = str(make_fake_upf(tmp_path / "pseudo"))
    config = tmp_path / "config.toml"
    save_config(cfg, config)
    output = tmp_path / "converted"
    args = ["calculation", str(source_file), str(template), str(output), "--config", str(config)]
    assert main(args) == 1
    error = capsys.readouterr().err
    assert "--use-target-thermostat" in error and "--no-velocities" in error
    assert not output.exists()
    assert main(args + ["--use-target-thermostat", "--no-velocities"]) == 0
    converted = CalculationSpec.load(output / "spec.json")
    assert converted.task.md.model_dump() == source.task.md.model_dump() | {"thermostat": "csvr"}
    assert converted.structure.velocities is None
    report = json.loads((output / "conversion.json").read_text(encoding="utf-8"))
    assert report["changes"]["task.md.thermostat"] == {"source": "nose_hoover", "target": "csvr"}
    assert report["omitted"] == ["structure.velocities"]
    readme = (output / "README.txt").read_text(encoding="utf-8")
    assert "nose_hoover → csvr" in readme
    assert ("初速度を引き継いでいません" if language == "ja" else "Initial velocities were omitted") in readme
    inp = (output / "pw.in").read_text(encoding="utf-8")
    assert "ion_temperature  = 'svr'" in inp
    assert "tempw            = 425" in inp and "nraise           = 300" in inp
    assert "iprint           = 3" in inp
    assert CalculationSpec.load(source_file).structure.velocities == source.structure.velocities


@pytest.mark.parametrize("language", ["ja", "en"])
@pytest.mark.parametrize("ensemble,thermostat,extra,unused", [
    ("NVT", "nose_hoover", {"SMASS": 2}, "coupling_time_fs"),
    ("NPT", "langevin", {"PMASS": 800, "LANGEVIN_GAMMA_L": 4}, "barostat_time_fs"),
])
def test_vasp_conversion_records_unapplied_coupling_times(tmp_path, monkeypatch, language, ensemble, thermostat, extra, unused):
    from adit import lang
    from adit.config import save_config
    from adit.project import build_project
    from tests.test_vasp import si_spec

    monkeypatch.setattr(lang, "LANGUAGE", language)
    monkeypatch.setenv("ADIT_LANG", language)
    source = si_spec(method=LammpsMethod(), task=Task(type="molecular_dynamics", md=MDSettings(
        ensemble=ensemble, thermostat=thermostat, coupling_time_fs=75, barostat_time_fs=750, dump_interval=3)))
    target = si_spec(method=VaspMethod(extra_incar=extra))
    source_file = tmp_path / "source.json"
    source.save(source_file)
    template = save_template(target, "vasp-md", directory=tmp_path)
    cfg = cfg_for(None)
    config = tmp_path / "config.toml"
    save_config(cfg, config)
    output = tmp_path / "converted"
    assert main(["calculation", str(source_file), str(template), str(output), "--config", str(config)]) == 0
    converted = CalculationSpec.load(output / "spec.json")
    assert converted.task.md == source.task.md
    report = json.loads((output / "conversion.json").read_text(encoding="utf-8"))
    path = "task.md." + unused
    assert report["not_applied_by_target"][path]["value"] == getattr(source.task.md, unused)
    assert report["not_applied_by_target"][path]["incar_parameters"] == extra
    assert path not in report["preserved"] and "task" not in report["preserved"]
    assert report["preserved_in_spec_only"] == [path]
    for text in [(output / "README.txt").read_text(encoding="utf-8"), build_project(converted, cfg).texts["README.txt"]]:
        assert path in text
        assert ("適用されません" if language == "ja" else "not applied") in text
    conversion_readme = (output / "README.txt").read_text(encoding="utf-8")
    assert ("変換先の雛形" if language == "ja" else "target template") in conversion_readme
    incar = (output / "INCAR").read_text(encoding="utf-8")
    assert "NBLOCK = 3" in incar
    for key, value in extra.items():
        assert f"{key} = {value}" in incar
    if ensemble == "NPT":
        assert "task.md.coupling_time_fs" in report["preserved"]
        assert "LANGEVIN_GAMMA = 13.3333" in incar
