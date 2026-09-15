
import json
from pathlib import Path

import numpy as np
import pytest

from adit.analysis import heavy_setup as H
from adit.analysis import msd_worker as W


def test_estimate_is_arithmetic_only_and_scales():
    small = H.estimate(1000, 18, 100)
    big = H.estimate(10000, 1000, 100)
    assert small["seconds"] < 1.0 and big["seconds"] > small["seconds"] * 100
    assert big["coordinates_mb"] == pytest.approx(10000 * 1000 * 24 / 1e6)
    assert not H.is_heavy(1000, 18) and H.is_heavy(10000, 1000)


def test_write_job_copies_the_worker_and_writes_the_how_to(tmp_path):
    written = H.write_job(tmp_path, dt_fs=10.0, natoms=18, trajectory="Na.dat", cell_file="dftb.inp", taus=50)
    names = {p.name for p in written}
    assert names == {H.WORKER_FILE, H.JOB_FILE}
    worker = (tmp_path / H.WORKER_FILE).read_text(encoding="utf-8")
    assert "from adit" not in worker and "import adit" not in worker
    job = (tmp_path / H.JOB_FILE).read_text(encoding="utf-8")
    assert "--natoms 18" in job and "--dt 10" in job and "--taus 50" in job
    assert "adit-analyze" in job and ("投入" in job or "does not submit" in job)


def test_worker_writes_a_result_file(tmp_path):
    rng = np.random.default_rng(0)
    cell = np.diag([12.0, 11.0, 13.0])
    frames, natoms = 60, 18
    start = rng.random((natoms, 3)) @ cell
    steps = rng.normal(0.0, np.sqrt(2 * 2e-4 * 10.0), size=(frames - 1, natoms, 3))
    pos = np.concatenate([start[None], start[None] + np.cumsum(steps, axis=0)])
    frac = np.linalg.solve(cell.T, pos.reshape(-1, 3).T).T % 1.0
    wrapped = (frac @ cell).reshape(pos.shape)
    table = tmp_path / "Na.dat"
    table.write_text("".join(f"Na {x:.10f} {y:.10f} {z:.10f}\n" for fr in wrapped for x, y, z in fr), encoding="utf-8")
    (tmp_path / "dftb.inp").write_text("".join(f"TV {r[0]:.10f} {r[1]:.10f} {r[2]:.10f}\n" for r in cell), encoding="utf-8")
    out = tmp_path / "msd_vanhove.json"
    W.main([str(table), "--natoms", "18", "--cell", str(tmp_path / "dftb.inp"), "--dt", "10",
            "--taus", "5", "--out", str(out)])
    got = json.loads(out.read_text(encoding="utf-8"))
    assert got["frames"] == frames and got["atoms"] == natoms
    assert len(got["d_per_atom_cm2_s"]) == natoms
    assert got["d_mean_cm2_s"] == pytest.approx(2e-5, rel=0.6)
    assert len(got["vanhove"]["times_fs"]) == 5


def test_worker_does_not_import_adit():
    text = Path("src/adit/analysis/msd_worker.py").read_text(encoding="utf-8")
    assert "from adit" not in text and "import adit" not in text


def _md_dir(tmp_path):
    import shutil

    dst = tmp_path / "run"
    shutil.copytree("examples/dftb_md_water_generated", dst)
    return dst


def test_heavy_analysis_writes_the_job_instead_of_computing(tmp_path):
    from adit.analysis.report import AnalysisOptions, run_analysis

    run = _md_dir(tmp_path)
    res = run_analysis(run, AnalysisOptions(msd=True, vanhove=50, heavy_limit_seconds=0.0,
                                            out_dir=tmp_path / "out"))
    assert (run / H.WORKER_FILE).is_file() and (run / H.JOB_FILE).is_file()
    assert res.tables["vanhove_job"]["result_file"] == H.RESULT_FILE
    assert any("実行用のファイル" in n or "Files to run it" in n for n in res.notes)
    assert "vanhove" not in res.tables


def test_existing_result_file_is_plotted_without_computing(tmp_path):
    from adit.analysis.report import AnalysisOptions, run_analysis

    run = _md_dir(tmp_path)
    (run / H.RESULT_FILE).write_text(json.dumps({
        "vanhove": {"times_fs": [10.0, 20.0], "d_fit_A2_fs": [1e-4, 1.1e-4], "d_direct_A2_fs": [1e-4, 1.0e-4],
                    "alpha2": [0.01, 0.02], "rms_A": [0.1, 0.2], "displacement": "mic", "half_width_A": 5.0,
                    "truncated_from_fs": None, "near_cap_fraction": 0.0},
        "d_per_atom_cm2_s": [1.0e-5, 1.2e-5, 0.9e-5], "symbols": ["O", "H", "H"], "atom_index": [0, 1, 2],
        "fit_range_fs": [10.0, 50.0]}, ensure_ascii=False), encoding="utf-8")
    res = run_analysis(run, AnalysisOptions(msd=True, vanhove=50, out_dir=tmp_path / "out"))
    assert res.tables["vanhove"]["computed_here"] is False
    assert res.tables["msd_per_atom"]["D_cm2_s"] == [1.0e-5, 1.2e-5, 0.9e-5]
    assert "vanhove" in res.figures and "d_per_atom" in res.figures
    assert any("計算はこの場でしていません" in n or "nothing was computed here" in n for n in res.notes)
