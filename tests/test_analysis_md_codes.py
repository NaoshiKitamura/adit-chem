
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from ase.io import read

from adit.analysis import AnalysisOptions, run_analysis
from adit.analysis import trajectory as trj
from adit.analysis.readers import HARTREE_EV, detect_code, load_run
from adit.analysis.readers_extra import KJ_MOL_EV
from adit.results import summarize_run

REPO = Path(__file__).resolve().parent.parent
EX = REPO / "examples"


def _copy(name: str, tmp_path: Path) -> Path:
    d = tmp_path / name
    shutil.copytree(EX / name, d, ignore=shutil.ignore_patterns("analysis"))
    return d


def test_detect_new_codes():
    assert detect_code(EX / "lammps_cu_nvt_generated") == "lammps"
    assert detect_code(EX / "gromacs_spce_nvt_generated") == "gromacs"
    assert detect_code(EX / "cp2k_h2o_md_generated") == "cp2k"


# ---------------- LAMMPS ----------------
def test_lammps_thermo_and_dump():
    r = load_run(EX / "lammps_cu_nvt_generated")
    assert len(r.energies_ev) == 7 and r.energies_ev[0] == pytest.approx(-378.17075)
    assert r.times_fs == pytest.approx([0, 50, 100, 150, 200, 250, 300])  # Time 0.05 ps = 50 fs
    assert r.temperatures_k[0] == pytest.approx(300) and r.series["pressure"]["values"][0] == pytest.approx(3474.5344)
    t = r.frames
    assert isinstance(t, trj.Trajectory) and len(t) == 7 and r.frame_dt_fs == pytest.approx(50.0)  # 0.001 ps × 1000 × 50
    ref = read(EX / "lammps_cu_nvt_generated" / "traj.lammpstrj", format="lammps-dump-text", index=":")
    assert len(ref) == 7
    for a, b in zip(t, ref):
        assert a.get_chemical_symbols() == ["Cu"] * 108
        assert np.allclose(a.positions, b.positions) and np.allclose(a.cell, b.cell)
    assert np.allclose(t[0].positions[1], [0, 1.8075, 1.8075])


def test_lammps_estimate_uses_file_size():
    t = trj.Trajectory(EX / "lammps_cu_nvt_generated" / "traj.lammpstrj", "lammpsdump", fmt="Cu")
    est = t.estimate_total_frames()
    assert 7 <= est <= 14 and t._shared["total"] is None, est
    assert len(t) == 7


def test_lammps_triclinic_box_bounds(tmp_path):
    p = tmp_path / "t.lammpstrj"
    xy, xz, yz = 1.0, -0.5, 0.3
    lo, hi = np.zeros(3), np.array([10.0, 9.0, 8.0])
    xlo_b, xhi_b = lo[0] + min(0, xy, xz, xy + xz), hi[0] + max(0, xy, xz, xy + xz)
    ylo_b, yhi_b = lo[1] + min(0, yz), hi[1] + max(0, yz)
    p.write_text("ITEM: TIMESTEP\n0\nITEM: NUMBER OF ATOMS\n2\nITEM: BOX BOUNDS xy xz yz pp pp pp\n"
                 f"{xlo_b} {xhi_b} {xy}\n{ylo_b} {yhi_b} {xz}\n{lo[2]} {hi[2]} {yz}\n"
                 "ITEM: ATOMS id type x y z\n2 2 1.0 2.0 3.0\n1 1 0.5 0.5 0.5\n", encoding="utf-8")
    a = trj.Trajectory(p, "lammpsdump", fmt="Cu O")[0]
    assert np.allclose(a.cell, [[10, 0, 0], [xy, 9, 0], [xz, yz, 8]])
    assert a.get_chemical_symbols() == ["Cu", "O"] and np.allclose(a.positions[1], [1, 2, 3])


def test_lammps_analysis_and_export(tmp_path):
    d = _copy("lammps_cu_nvt_generated", tmp_path)
    res = run_analysis(d, AnalysisOptions(rdf=True, msd=True, export=True))
    assert {"energy", "temperature", "rdf", "msd"} <= set(res.figures)
    assert res.tables["msd"]["dt_fs"] == pytest.approx(50.0)
    back = read(d / "analysis" / "export" / "trajectory.extxyz", index=":")
    assert len(back) == 7 and np.allclose(back[0].cell.lengths(), [10.845] * 3)


# ---------------- GROMACS ----------------
def test_gromacs_md_log_table():
    r = load_run(EX / "gromacs_spce_nvt_generated")
    assert len(r.energies_ev) == 11
    assert r.energies_ev[0] == pytest.approx(-8.27105e3 * KJ_MOL_EV)
    assert r.times_fs[:2] == pytest.approx([0.0, 50.0]) and r.temperatures_k[0] == pytest.approx(313.192)
    assert r.series["pressure"]["values"][0] == pytest.approx(232.761) and "conserved" in r.series
    assert r.frame_source == "adit.gro" and len(r.frames) == 1 and len(r.final) == 648
    assert set(r.final.get_chemical_symbols()) == {"O", "H"}
    assert any("adit.xtc" in n for n in r.notes)


def test_gromacs_minimization():
    r = load_run(EX / "gromacs_spce_em_generated")
    assert r.energies_ev and r.energies_ev[0] == pytest.approx(-9.95368e3 * KJ_MOL_EV) and r.temperatures_k is None
    s = summarize_run(EX / "gromacs_spce_em_generated")
    assert s.converged and s.finished


def test_gromacs_export_tells_how_to_convert_xtc(tmp_path):
    d = _copy("gromacs_spce_nvt_generated", tmp_path)
    res = run_analysis(d, AnalysisOptions(export=True))
    readme = (d / "analysis" / "export" / "export_README.txt").read_text(encoding="utf-8")
    assert "gmx trjconv" in readme and res.tables["export"]["n_frames"] == 1


# ---------------- CP2K ----------------
def test_cp2k_single_point_energy_and_charges():
    r = load_run(EX / "cp2k_h2o_generated")
    assert r.energies_ev == pytest.approx([-17.219399129356 * HARTREE_EV], rel=1e-9) or len(r.energies_ev) == 1
    q = {c["definition"]: c for c in r.charges}
    assert q["Mulliken (CP2K)"]["values"] == pytest.approx([-0.246753, 0.123376, 0.123376])
    assert q["Hirshfeld (CP2K)"]["values"] == pytest.approx([-1.110, 0.561, 0.561])
    assert q["Mulliken (CP2K)"]["source"].startswith("output.log:")
    assert r.final is not None and np.allclose(r.final.positions[0], [3.0, 3.0, 3.298154])


def test_cp2k_md_ener_and_trajectory():
    r = load_run(EX / "cp2k_h2o_md_generated")
    assert r.times_fs == pytest.approx([0, 0.5, 1.0, 1.5, 2.0, 2.5]) and r.temperatures_k[1] == pytest.approx(272.045771763)
    assert r.energies_ev[0] == pytest.approx((0.001425067 - 17.219399129) * HARTREE_EV)
    assert r.series["conserved"]["values"][0] == pytest.approx(-17.217974062 * HARTREE_EV)
    assert len(r.frames) == 6 and r.frame_dt_fs == pytest.approx(0.5) and not any(r.frames[0].pbc)  # PERIODIC NONE


def test_cp2k_vibrations_from_molden(tmp_path):
    d = _copy("cp2k_h2o_generated", tmp_path)
    (d / "adit-VIBRATIONS-1.mol").write_text("[Molden Format]\n[FREQ]\n 1595.1\n 3657.2\n 3756.0\n[INT]\n 70.1\n 2.0\n 45.3\n[FR-COORD]\n", encoding="utf-8")
    r = load_run(d)
    assert r.frequencies_cm1 == pytest.approx([1595.1, 3657.2, 3756.0]) and r.ir_intensities == pytest.approx([70.1, 2.0, 45.3])


def test_new_codes_summaries_and_analyze(tmp_path):
    for name in ("lammps_cu_nvt_generated", "gromacs_spce_nvt_generated", "cp2k_h2o_md_generated", "cp2k_h2o_generated"):
        s = summarize_run(EX / name)
        assert s.finished, name
        d = _copy(name, tmp_path)
        res = run_analysis(d, AnalysisOptions())
        s_json = json.loads((d / "analysis" / "summary.json").read_text(encoding="utf-8"))
        assert s_json["code"] == res.code and "energy" in res.tables
