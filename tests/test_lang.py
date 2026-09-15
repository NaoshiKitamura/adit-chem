
from __future__ import annotations

import re

import pytest

from adit import lang
from adit.config import default_config
from adit.project import ProjectError, build_project
from adit.spec import Runtime, Task
from adit.validate import validate
from tests.conftest import pbs_profile, water_spec

_JA = re.compile(r"[぀-ヿ一-鿿]")


@pytest.fixture
def cfg(sk_root):
    c = default_config(sk_root=str(sk_root))
    c.profiles["cluster"] = pbs_profile()
    return c


@pytest.fixture
def english():
    lang.set_language("en")
    yield
    lang.set_language("ja")


def test_default_is_japanese(cfg):
    lang.set_language("ja")
    files = build_project(water_spec(), cfg)
    assert _JA.search(files.texts["README.txt"]) and _JA.search(files.texts["submit.sh"])


@pytest.mark.parametrize("profile", ["local", "cluster"])
def test_english_outputs_have_no_japanese(cfg, english, profile):
    rt = Runtime(profile=profile, ncpus=8, omp_threads=8, walltime="01:00:00", job_name="w") if profile == "cluster" else Runtime(profile="local")
    files = build_project(water_spec(runtime=rt), cfg)
    for name in ("README.txt", "submit.sh", "analyze.py"):
        assert not _JA.search(files.texts[name]), name
    r = files.texts["README.txt"]
    assert "== Reading the results ==" in r and "== Citation ==" in r
    if profile == "cluster":
        assert "Copy this whole directory to the cluster" in r and "qsub submit.sh" in r
        assert "module command not available" in files.texts["submit.sh"]


def test_english_validation_messages(cfg, english):
    spec = water_spec(task=Task(type="molecular_dynamics"))
    spec = spec.model_copy(update={"structure": spec.structure.model_copy(update={"charge": 99})})
    errs = validate(spec, cfg)
    assert errs and all(not _JA.search(str(e)) for e in errs), [str(e) for e in errs]
    with pytest.raises(ProjectError) as ex:
        build_project(spec, cfg)
    assert "fix the following to generate" in str(ex.value)
    assert "structure." not in str(ex.value)


def test_english_validation_dftb_specific(cfg, english):
    from adit.spec import DftbMethod
    spec = water_spec(method=DftbMethod(sk_set="nodocs-0-1"))
    errs = validate(spec, cfg)
    assert errs and all(not _JA.search(str(e)) for e in errs), [str(e) for e in errs]
