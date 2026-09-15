
from pathlib import Path

import numpy as np
import pytest
from ase.build import fcc111
from ase.io.cube import write_cube

from adit.config import load_config, save_config
from adit.scan import Scan, apply_value, parse_scan, write_scan
from adit.spec import CalculationSpec
from adit.structure import StructureError, from_spacegroup
from tests.conftest import cfg_for, water_spec


def test_unknown_config_keys_are_reported(tmp_path):
    from adit.config import unknown_keys_message

    path = tmp_path / "cluster.toml"
    path.write_text('sk_root = "/tmp/sk"\n\n[profiles.local]\nkind = "direct"\n\ntemplates_dir = "/tmp/t"\n', encoding="utf-8")
    cfg = load_config(path)
    assert cfg.unknown_keys == ["profiles.local.templates_dir"]
    message = unknown_keys_message(cfg)
    assert "profiles.local.templates_dir" in message and "TOML" in message


def test_known_config_has_no_warning(tmp_path, sk_root):
    from adit.config import unknown_keys_message

    path = tmp_path / "cluster.toml"
    save_config(cfg_for(sk_root), path)
    assert load_config(path).unknown_keys == []
    assert unknown_keys_message(load_config(path)) == ""


def test_spec_errors_say_which_field_and_what_is_allowed(tmp_path):
    import json

    from adit.cli import main as gen_main

    data = json.loads(water_spec().to_json())
    data["task"]["md"]["thermostat"] = "Langevin"
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception) as ex:
        CalculationSpec.load(path)
    message = CalculationSpec.describe_error(ex.value)
    assert "'Langevin' は使えません" in message and "langevin" in message
    assert "pydantic" not in message and "validation error" not in message
    assert gen_main([str(path), str(tmp_path / "out")]) == 2


def test_broken_json_is_explained(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text('{"structure": ,}', encoding="utf-8")
    with pytest.raises(Exception) as ex:
        CalculationSpec.load(path)
    assert "JSON として壊れています" in CalculationSpec.describe_error(ex.value)


def test_geometry_scan_moves_only_the_named_atom():
    spec = water_spec()
    moved = apply_value(spec, "geom.distance(0,1)", "1.20")
    assert moved.atoms.get_distance(0, 1) == pytest.approx(1.20)
    assert moved.atoms.positions[0] == pytest.approx(spec.atoms.positions[0])
    angle = apply_value(spec, "geom.angle(1,0,2)", "100.0")
    assert angle.atoms.get_angle(1, 0, 2) == pytest.approx(100.0)


def test_geometry_scan_checks_its_arguments():
    spec = water_spec()
    from adit.scan import ScanError

    for path, value in (("geom.distance(0)", "1.0"), ("geom.distance(0,9)", "1.0"), ("geom.distance(0,1)", "-1")):
        with pytest.raises(ScanError):
            apply_value(spec, path, value)


def test_geometry_scan_parses_as_a_path():
    scan = parse_scan("geom.dihedral(0,1,2,3)=0,30,60")
    assert scan.path == "geom.dihedral(0,1,2,3)" and scan.values == ["0", "30", "60"]
    assert scan.dir_name("30") == "dihedral_0_1_2_3_30"


def test_grid_scan_makes_every_combination(tmp_path, sk_root):
    import json

    out = tmp_path / "grid"
    scans = [Scan("method.scc_tolerance", ["1e-5", "1e-6"]), Scan("task.max_steps", ["10", "20"])]
    dirs = write_scan(water_spec(), cfg_for(sk_root), out, scans)
    assert len(dirs) == 4
    names = sorted(d.name for d in dirs)
    assert names[0] == "scc_tolerance_1e-5__max_steps_10"
    meta = json.loads((out / "scan.json").read_text(encoding="utf-8"))
    assert [s["path"] for s in meta["scans"]] == ["method.scc_tolerance", "task.max_steps"]
    assert len(meta["combinations"]) == 4
    assert "path" not in meta


def test_single_scan_keeps_the_old_record(tmp_path, sk_root):
    import json

    out = tmp_path / "one"
    write_scan(water_spec(), cfg_for(sk_root), out, [Scan("task.max_steps", ["10", "20"])])
    meta = json.loads((out / "scan.json").read_text(encoding="utf-8"))
    assert meta["path"] == "task.max_steps" and meta["values"] == ["10", "20"]


def test_grid_scan_table(tmp_path, sk_root):
    from adit.scan import analyze_scan

    out = tmp_path / "grid"
    dirs = write_scan(water_spec(), cfg_for(sk_root), out,
                      [Scan("method.scc_tolerance", ["1e-5", "1e-6"]), Scan("task.max_steps", ["10", "20"])])
    (dirs[0] / "output.log").write_text("Total Energy:  -4.0 H\n", encoding="utf-8")
    result = analyze_scan(out)
    text = (out / "scan_energies.csv").read_text(encoding="utf-8")
    assert "method.scc_tolerance,task.max_steps" in text
    assert "図は項目を 1 つだけ振ったとき" in result.summary_text()


def test_spacegroup_builds_known_structures():
    nacl = from_spacegroup("225 Na:0,0,0 Cl:0.5,0,0 cell=5.64")
    assert nacl.get_chemical_formula() == "Cl4Na4" and len(nacl) == 8
    assert nacl.get_distance(0, 4, mic=True) == pytest.approx(2.82, abs=1e-6)
    silicon = from_spacegroup("227 Si:0,0,0 cell=5.43")
    nearest = min(silicon.get_distance(i, j, mic=True) for i in range(8) for j in range(i + 1, 8))
    assert len(silicon) == 8 and nearest == pytest.approx(2.3512, abs=1e-3)


def test_spacegroup_reports_bad_input():
    for ref in ("225", "225 Na:0,0 cell=5.64", "225 Na:0,0,0", "225 Na-0,0,0 cell=5.64", "225 Na:a,b,c cell=5.64"):
        with pytest.raises(StructureError):
            from_spacegroup(ref)


def test_crystal_cli_writes_a_file(tmp_path):
    from adit.convert import main as convert_main

    out = tmp_path / "nacl.cif"
    assert convert_main(["crystal", "225 Na:0,0,0 Cl:0.5,0,0 cell=5.64", str(out)]) == 0
    assert out.is_file()
    assert convert_main(["crystal", "225 Na:0,0,0 Cl:0.5,0,0 cell=5.64", str(out)]) == 1


@pytest.fixture
def cube(tmp_path):
    atoms = fcc111("Al", size=(1, 1, 4), vacuum=8.0)
    z = np.linspace(0, atoms.cell[2, 2], 40, endpoint=False)
    profile = -8.0 * np.exp(-((z - atoms.positions[:, 2].mean()) ** 2) / 6.0) + 2.5
    path = tmp_path / "potential.cube"
    with open(path, "w", encoding="utf-8") as f:
        write_cube(f, atoms, np.tile(profile, (4, 4, 1)))
    return path


def test_plane_average_of_a_cube(cube):
    from adit.analysis.volumetric import find_files, plane_average, read_grid

    assert find_files(cube.parent) == [cube]
    grid = read_grid(cube)
    positions, mean = plane_average(grid, 2)
    assert len(mean) == 40 and float(mean.max()) == pytest.approx(2.5, abs=1e-3)
    assert positions[-1] < grid.atoms.cell[2, 2]


def test_work_function_needs_ev_and_a_fermi_level(cube):
    from adit.analysis.volumetric import read_grid, work_function

    result = work_function(read_grid(cube), -3.0, 2)
    assert result["work_function_ev"] is None and "eV ではありません" in result["note"]


def test_work_function_from_a_locpot(tmp_path):
    from ase.io import write

    from adit.analysis.volumetric import read_grid, work_function

    atoms = fcc111("Al", size=(1, 1, 4), vacuum=8.0)
    path = tmp_path / "LOCPOT"
    write(path, atoms, format="vasp", direct=True)
    n = (4, 4, 32)
    z = np.linspace(0, atoms.cell[2, 2], n[2], endpoint=False)
    profile = -8.0 * np.exp(-((z - atoms.positions[:, 2].mean()) ** 2) / 6.0) + 2.5
    values = np.tile(profile, (n[0], n[1], 1))
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n%d %d %d\n" % n)
        flat = values.transpose(2, 1, 0).ravel()
        for i in range(0, flat.size, 5):
            f.write(" ".join("%.6E" % v for v in flat[i:i + 5]) + "\n")
    grid = read_grid(path)
    assert grid.unit == "eV" and float(grid.values.max()) == pytest.approx(2.5, abs=1e-4)
    result = work_function(grid, -3.0, 2)
    assert result["work_function_ev"] == pytest.approx(5.5, abs=1e-3)


def test_dftb_writes_a_random_seed(tmp_path, sk_root):
    from adit.project import ProjectError, build_project, write_project
    from adit.spec import MDSettings, Task

    out = tmp_path / "md"
    spec = water_spec(task=Task(type="molecular_dynamics",
                                md=MDSettings(ensemble="NVT", thermostat="berendsen", temperature_k=300.0,
                                              timestep_fs=1.0, steps=10, dump_interval=5)))
    write_project(spec, cfg_for(sk_root), out)
    text = (out / "dftb_in.hsd").read_text(encoding="utf-8")
    assert "RandomSeed = 12345" in text and text.count("\nOptions {") == 1
    bad = spec.model_copy(update={"method": spec.method.model_copy(update={"seed": 0})})
    with pytest.raises(ProjectError) as ex:
        build_project(bad, cfg_for(sk_root))
    assert any(e.location == "method.seed" for e in ex.value.errors)


def test_green_kubo_matches_the_formula():
    from adit.analysis.transport import BOLTZMANN_J_PER_K, green_kubo_viscosity

    times = np.arange(0.0, 100.0, 1.0)          # fs
    pressure = np.full_like(times, 2.0)          # bar
    result = green_kubo_viscosity(times, [pressure], volume_ang3=1000.0, temperature_k=300.0, pressure_unit="bar")
    lag = result.times_fs[-1] * 1e-15
    expected = 1000.0 * 1e-30 / (BOLTZMANN_J_PER_K * 300.0) * (2.0 * 1e5) ** 2 * lag
    assert result.running_pa_s[-1] == pytest.approx(expected, rel=1e-6)
    assert "収束しているかは判定していません" in result.note


def test_green_kubo_refuses_uneven_times():
    from adit.analysis.transport import TransportError, green_kubo_viscosity

    times = [0.0, 1.0, 2.0, 4.0]
    with pytest.raises(TransportError):
        green_kubo_viscosity(times, [[1.0, 1.0, 1.0, 1.0]], 1000.0, 300.0)
    with pytest.raises(TransportError):
        green_kubo_viscosity([0.0, 1.0, 2.0, 3.0], [None], 1000.0, 300.0)


def test_lammps_writes_the_pressure_tensor_when_asked(tmp_path, sk_root):
    from ase.build import bulk

    from adit.project import write_project
    from adit.spec import AtomsData, CalculationSpec, LammpsMethod, MDSettings, Runtime, Structure, Task

    atoms = bulk("Cu", "fcc", a=3.615, cubic=True)
    spec = CalculationSpec(
        structure=Structure(source="bulk", source_ref="Cu", atoms=AtomsData.from_ase(atoms)),
        method=LammpsMethod(units="metal", atom_style="atomic", pair_style="eam", pair_coeff="* * Cu_u3.eam",
                            potential_files=[str(Path(__file__).resolve().parent.parent / "examples/lammps_cu/Cu_u3.eam")],
                            thermo_pressure_tensor=True),
        task=Task(type="molecular_dynamics", md=MDSettings(ensemble="NVT", thermostat="nose_hoover", temperature_k=300.0,
                                                           timestep_fs=1.0, steps=100, dump_interval=50)),
        runtime=Runtime(profile="local", job_name="cu"))
    out = tmp_path / "visc"
    write_project(spec, cfg_for(sk_root), out)
    text = (out / "in.lammps").read_text(encoding="utf-8")
    assert "thermo_style custom step time temp pe ke etotal press vol pxy pxz pyz" in text
    assert "\nthermo 1\n" in text
    assert "Green-Kubo" in (out / "README.txt").read_text(encoding="utf-8")


def test_staged_run_is_not_reported_as_tampered(tmp_path, sk_root):
    import json

    from adit.report import check_lines, load_run_report
    from adit.stages import parse_stages, write_stages

    stages_file = tmp_path / "stages.json"
    stages_file.write_text(json.dumps([
        {"name": "opt", "task": {"type": "geometry_optimization", "max_steps": 5}},
        {"name": "nvt", "task": {"type": "molecular_dynamics", "md": {"ensemble": "NVT", "steps": 10}}},
    ]), encoding="utf-8")
    import json as _json

    stages = parse_stages(_json.loads(stages_file.read_text(encoding="utf-8")))
    dirs = write_stages(water_spec(), cfg_for(sk_root), tmp_path / "run", stages)
    second = dirs[1]
    (second / "geometry.gen").write_text("2  C\n H O\n 1 1 0.0 0.0 0.0\n 2 2 0.0 0.0 1.0\n", encoding="utf-8")
    lines, verdict = check_lines(load_run_report(second))
    assert verdict == "ok", lines
    assert any("引き継ぎ" in l and "geometry.gen" in l for l in lines)
    (second / "dftb_in.hsd").write_text("# 人が書き換えた\n", encoding="utf-8")
    lines, verdict = check_lines(load_run_report(second))
    assert verdict == "bad" and any("書き換え" in l and "dftb_in.hsd" in l for l in lines)
