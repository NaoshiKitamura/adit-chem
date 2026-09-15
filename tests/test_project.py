import os
import shutil
import subprocess
from pathlib import Path

import pytest

from adit.config import Config, ConfigError, Profile, config_path, default_config, load_config, save_config
from adit.project import ProjectError, build_project, load_project, write_project
from adit.spec import DftbMethod, Runtime
from tests.conftest import REAL_SK_ROOT, water_spec, pbs_profile

DFTB_EXE = os.environ.get("ADIT_DFTB_EXE") or shutil.which("dftb+") or ""
HAVE_REAL = (REAL_SK_ROOT / "mio-1-1").is_dir() and Path(DFTB_EXE).is_file()


@pytest.fixture
def cfg(sk_root) -> Config:
    c = default_config(sk_root=str(sk_root))
    c.profiles["cluster"] = pbs_profile()
    from tests.conftest import slurm_profile
    c.profiles["slurm"] = slurm_profile()
    return c


def test_config_roundtrip(tmp_path, monkeypatch, cfg):
    monkeypatch.setenv("ADIT_CONFIG", str(tmp_path / "c" / "cluster.toml"))
    assert config_path() == tmp_path / "c" / "cluster.toml"
    with pytest.raises(ConfigError):
        load_config()
    save_config(cfg)
    back = load_config()
    assert back == cfg
    assert back.source_path == cfg.source_path == config_path().absolute()
    assert "source_path" not in back.model_dump_json()
    assert "source_path" not in config_path().read_text(encoding="utf-8")
    assert back.profile("cluster").kind == "pbs" and back.profile("cluster").modules_for("dftbplus") == ["dftbplus/25.1"]
    assert back.profile("cluster").modules_for("vasp") == []
    assert list(default_config().profiles) == ["local"]
    with pytest.raises(ConfigError):
        back.profile("nope")


def test_config_broken(tmp_path):
    p = tmp_path / "cluster.toml"; p.write_text("profiles = 3\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_write_project_layout(tmp_path, cfg):
    out = tmp_path / "calc"
    spec = water_spec()
    written = write_project(spec, cfg, out)
    names = sorted(p.relative_to(out).as_posix() for p in written)
    assert names == sorted(["dftb_in.hsd", "geometry.gen", "submit.sh", "spec.json", "README.txt", "analyze.py",
                            "skf/H-H.skf", "skf/H-O.skf", "skf/O-H.skf", "skf/O-O.skf", "skf/LICENSE", "skf/README"])
    assert os.access(out / "submit.sh", os.X_OK)
    assert load_project(out) == spec
    readme = (out / "README.txt").read_text(encoding="utf-8")
    assert "bash submit.sh" in readme and "fake-1-0" in readme


def test_refuse_overwrite(tmp_path, cfg):
    out = tmp_path / "calc"
    write_project(water_spec(), cfg, out)
    with pytest.raises(ProjectError):
        write_project(water_spec(), cfg, out)
    write_project(water_spec(), cfg, out, overwrite=True)


def test_validation_blocks_writing(tmp_path, cfg):
    out = tmp_path / "calc"
    bad = water_spec(method=DftbMethod(sk_set="nope-9-9"))
    with pytest.raises(ProjectError) as ex:
        write_project(bad, cfg, out)
    assert ex.value.errors and ex.value.errors[0].location == "method.sk_set"
    assert not out.exists()


def test_unknown_profile(tmp_path, cfg):
    with pytest.raises(ProjectError) as ex:
        build_project(water_spec(runtime=Runtime(profile="mars")), cfg)
    assert ex.value.errors[0].location == "runtime.profile"


def test_cluster_readme_has_manual_steps(cfg):
    spec = water_spec(runtime=Runtime(profile="cluster", ncpus=8, omp_threads=8, walltime="01:00:00", job_name="w"))
    files = build_project(spec, cfg)
    r = files.texts["README.txt"]
    assert "scp -r" in r and "qsub submit.sh" in r and "qstat" in r
    assert "#PBS -l select=1:ncpus=8:mpiprocs=1:ompthreads=8:jobtype=core" in files.texts["submit.sh"]
    slurm = build_project(water_spec(runtime=Runtime(profile="slurm", ncpus=8, mpiprocs=8, job_name="w")), cfg)
    assert "#SBATCH --job-name=w" in slurm.texts["submit.sh"] and "sbatch submit.sh" in slurm.texts["README.txt"]


@pytest.mark.skipif(not HAVE_REAL, reason="mio-1-1 か dftb+ が無い")
def test_local_submit_runs(tmp_path):
    cfg = default_config(sk_root=str(REAL_SK_ROOT))
    out = tmp_path / "water"
    write_project(water_spec(method=DftbMethod(sk_set="mio-1-1")), cfg, out)
    env = {**os.environ, "PATH": f"{Path(DFTB_EXE).parent}:{os.environ.get('PATH', '')}"}
    r = subprocess.run(["bash", "submit.sh"], cwd=out, capture_output=True, text=True, timeout=300, env=env)
    assert r.returncode == 0, r.stderr
    log = (out / "output.log").read_text(encoding="utf-8")
    assert "Geometry converged" in log and (out / "results.tag").is_file()
