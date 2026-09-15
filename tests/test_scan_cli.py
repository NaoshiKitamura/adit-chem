
import shutil
from pathlib import Path

import pytest

from tests.conftest import cfg_for, water_spec
from adit.config import ConfigError, ensure_config, save_config
from adit.spec import DftbMethod

REPO = Path(__file__).resolve().parent.parent


def test_adit_gen_scan_and_analyze_scan(sk_root, tmp_path, capsys):
    from adit.analysis.cli import main as analyze
    from adit.cli import main as gen
    cfg_path = tmp_path / "cluster.toml"; save_config(cfg_for(sk_root), cfg_path)
    spec_path = tmp_path / "spec.json"; water_spec(method=DftbMethod(sk_set="fake-1-0")).save(spec_path)
    out = tmp_path / "scan"
    assert gen([str(spec_path), str(out), "--config", str(cfg_path), "--scan", "method.scc_tolerance=1e-5,1e-7"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["scan.json", "scc_tolerance_1e-5", "scc_tolerance_1e-7"]
    assert gen([str(spec_path), str(tmp_path / "bad"), "--config", str(cfg_path), "--scan", "method.nothing=1,2"]) == 1
    assert "method.nothing" in capsys.readouterr().err
    for d in ("scc_tolerance_1e-5", "scc_tolerance_1e-7"):
        shutil.rmtree(out / d); shutil.copytree(REPO / "examples" / "water_generated", out / d)
    assert analyze([str(out), "--scan"]) == 0
    assert (out / "scan_energies.csv").is_file() and "scc_tolerance_1e-7" in (out / "scan_energies.csv").read_text(encoding="utf-8")
    assert analyze([str(tmp_path), "--scan"]) == 1


def test_broken_settings_file_is_not_overwritten(tmp_path):
    p = tmp_path / "cluster.toml"
    text = 'sk_root = "C:\\Users\\me\\slakos"\n'
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError):
        ensure_config(p)
    assert p.read_text(encoding="utf-8") == text
    q = tmp_path / "new" / "cluster.toml"
    cfg, path, created = ensure_config(q)
    assert created and q.is_file() and "local" in cfg.profiles
