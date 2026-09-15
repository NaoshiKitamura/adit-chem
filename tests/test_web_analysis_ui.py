
from __future__ import annotations

import html as h
import json
import re
import shutil
import threading
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from adit import lang
from adit.analysis import trajectory as trj
from adit.analysis.report import figure_title
from adit.config import default_config
from adit.web.server import WebApp, serve
from tests.conftest import pbs_profile

REPO = Path(__file__).resolve().parent.parent
EX = REPO / "examples"


@pytest.fixture
def web(sk_root, tmp_path):
    cfg = default_config(sk_root=str(sk_root)); cfg.profiles["cluster"] = pbs_profile()
    app = WebApp(cfg, tmp_path / "cluster.toml")
    httpd = serve(app, "127.0.0.1", 0)
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
    yield app, f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown(); httpd.server_close()
    lang.set_language("ja")


def _post(url: str, fields: dict) -> str:
    return urllib.request.urlopen(url, data=urllib.parse.urlencode(fields).encode(), timeout=120).read().decode()


def _get(url: str) -> str:
    return urllib.request.urlopen(url, timeout=120).read().decode()


def _copy(name: str, dest: Path) -> Path:
    d = dest / name
    shutil.copytree(EX / name, d, ignore=shutil.ignore_patterns("analysis"))
    return d


def _error(page: str) -> str:
    m = re.search(r'<div class="error">(.*?)</div>', page, re.S)
    return h.unescape(m.group(1)) if m else ""


def _section(page: str, key: str) -> str:
    m = re.search(rf'<details class="section" id="sec-{key}" open>(.*?)</details>', page, re.S)
    assert m, key
    return h.unescape(m.group(1))


def _value(page: str, name: str) -> str:
    m = re.search(rf'<input type="text" id="{name}" name="{name}"[^>]*value="([^"]*)"', page)
    assert m, name
    return h.unescape(m.group(1))


def test_detailed_fields_are_folded_and_thermo_has_no_defaults(web):
    app, base = web
    page = _get(base + "/analysis")
    assert '<details class="more">' in page
    assert _value(page, "stride") == "1" and _value(page, "th_temps") == "" and _value(page, "th_pressure") == "" and _value(page, "th_spin") == ""
    assert re.search(r'<select id="th_model" name="th_model"><option value="" selected>', page)
    assert re.search(r'<input type="checkbox" id="stats" name="stats" checked>', page)
    assert 'title="' in re.search(r'<label for="stride"[^>]*>', page).group(0)


def test_md_sections_and_new_figures(web, tmp_path):
    app, base = web
    d = _copy("dftb_md_water_generated", tmp_path)
    page = _post(base + "/analysis", {"run_dir": str(d), "rdf": "on", "msd": "on", "stats": "on", "stride": "2", "action": "run"})
    assert not _error(page), _error(page)
    assert '<details class="more" open>' in page
    ch = _section(page, "charges0")
    assert "Mulliken" in ch and "detailed.out:" in ch and "<td>O1</td>" in ch
    tr = _section(page, "trajectory")
    assert "<td>11</td>" in tr and "geo_end.xyz" in tr
    assert "<td>H</td>" in _section(page, "msd") and "ブロック平均" in _section(page, "timeseries_stats")
    for name in ("coordination", "blocking"):
        assert f"<legend>{figure_title(name)}</legend>" in page
    figs = re.findall(r'src="/file\?path=([^"]+)"', page)
    assert urllib.request.urlopen(base + "/file?path=" + figs[0], timeout=60).read()[:4] == b"\x89PNG"


def test_thermo_reason_then_values(web, tmp_path):
    app, base = web
    d = _copy("xtb_vib_water_generated", tmp_path)
    page = _post(base + "/analysis", {"run_dir": str(d), "stats": "on", "th_model": "ideal_gas"})
    th = _section(page, "thermo_ase")
    assert "計算していません" in th and "圧力" in th and "<table" not in th
    assert "output.log:" in _section(page, "thermochemistry") and "xtbout.json:" in _section(page, "electronic")
    page = _post(base + "/analysis", {"run_dir": str(d), "stats": "on", "th_model": "ideal_gas", "th_temps": "298.15, 400", "th_pressure": "100000",
                                      "th_sigma": "2", "th_geometry": "nonlinear", "th_spin": "0"})
    th = _section(page, "thermo_ase")
    assert th.count("<tr>") == 3 and "<td class=\"num\">400</td>" in th
    assert _value(page, "th_temps") == "298.15, 400"
    js = json.loads((d / "analysis" / "summary.json").read_text(encoding="utf-8"))
    assert js["tables"]["thermo_ase"]["computed"]


def test_bad_field_is_named_and_nothing_is_run(web, tmp_path):
    app, base = web
    d = _copy("xtb_vib_water_generated", tmp_path)
    page = _post(base + "/analysis", {"run_dir": str(d), "th_model": "harmonic", "th_exclude": "abc"})
    assert _error(page).startswith("解析の設定を読めません: 除く低い振動の本数") and "<legend>要約</legend>" not in page
    assert _value(page, "th_exclude") == "abc"


def test_too_large_banner_and_stride_button(web, tmp_path, monkeypatch):
    app, base = web
    d = _copy("dftb_md_water_generated", tmp_path)
    monkeypatch.setattr(trj.Trajectory, "file_size", lambda self: 50 * 2**30)
    page = _post(base + "/analysis", {"run_dir": str(d), "msd": "on", "stats": "on"})
    banner = h.unescape(re.search(r'<div class="error-banner" role="alert">(.*?)</div>', page, re.S).group(1))
    assert "--stride" in banner and "--memory-mb" in banner
    n = int(re.search(r'<button type="submit" name="use_stride" value="(\d+)">', page).group(1))
    assert n > 1 and f"間引きを {n} にする" in page
    page = _post(base + "/analysis", {"run_dir": str(d), "msd": "on", "stats": "on", "use_stride": str(n)})
    assert _value(page, "stride") == str(n) and '<details class="more" open>' in page and "<legend>要約</legend>" not in page
    assert "間引きの欄に" in page
    page = _post(base + "/analysis", {"run_dir": str(d), "msd": "on", "stats": "on", "stride": str(n)})
    assert not _error(page) and "<legend>要約</legend>" in page


def test_export_shows_readme_and_path(web, tmp_path):
    app, base = web
    d = _copy("cp2k_h2o_md_generated", tmp_path)
    page = _post(base + "/analysis", {"run_dir": str(d), "stats": "on", "action": "export", "export_unwrap": "on"})
    assert not _error(page), _error(page)
    exp = d / "analysis" / "export"
    box = h.unescape(re.search(r'<fieldset id="export">(.*?)</fieldset>', page, re.S).group(1))
    assert str(exp) in box and (exp / "export_README.txt").read_text(encoding="utf-8").splitlines()[0] in box
    assert "ファイルマネージャ" in box
    assert "非周期軌跡のため、周期境界でのつなぎ直しは行っていません" in (exp / "export_README.txt").read_text(encoding="utf-8")
    assert re.search(r'id="export_unwrap" name="export_unwrap" checked', page)
    page = _post(base + "/analysis", {"run_dir": str(d), "stats": "on"})
    assert '<fieldset id="export">' not in page


def test_compare_page(web, tmp_path):
    app, base = web
    for n in ("xtb_water_generated", "xtb_vib_water_generated", "water_generated"):
        _copy(n, tmp_path)
    page = _get(base + "/analysis?dir=" + urllib.parse.quote(str(tmp_path / "water_generated")))
    assert f'href="/compare?dir={urllib.parse.quote(str(tmp_path))}"' in page
    page = _get(base + "/compare?dir=" + urllib.parse.quote(str(tmp_path)))
    assert page.count('name="rx_dir_') == 6 and "compare.json を読む" not in page
    rows = {"base": str(tmp_path), "n_rows": "6", "rx_name_0": "same", "rx_nu_0": "1", "rx_dir_0": "xtb_water_generated",
            "rx_nu_1": "-1", "rx_dir_1": "xtb_vib_water_generated", "rx_name_2": "unbal", "rx_nu_2": "1", "rx_dir_2": "water_generated"}
    page = _post(base + "/compare", {**rows, "action": "compare"})
    assert not _error(page), _error(page)
    reac = _section(page, "compare_reactions")
    assert "釣り合う" in reac and "H:+2 O:+1" in reac and "ΔE [kJ/mol]" in reac
    cond = _section(page, "compare_conditions")
    assert "task.type" in cond and "<th scope=\"col\">xtb_vib_water_generated</th>" in cond
    assert "xtb_water_generated" in _section(page, "compare_runs")
    figs = re.findall(r'src="/file\?path=([^"]+)"', page)
    assert len(figs) == 1 and urllib.request.urlopen(base + "/file?path=" + figs[0], timeout=60).read()[:4] == b"\x89PNG"
    assert (tmp_path / "compare_runs.csv").is_file()
    page = _post(base + "/compare", {**rows, "action": "add_rows"})
    assert page.count('name="rx_dir_') == 7 and _value_row(page, 2) == "water_generated"
    page = _post(base + "/compare", {**rows, "rx_nu_2": "x"})
    assert "3 行目" in _error(page) and "係数" in _error(page)
    (tmp_path / "compare.json").write_text(json.dumps({"reactions": [{"name": "j", "terms": [{"dir": "water_generated", "nu": 2}]}]}), encoding="utf-8")
    page = _get(base + "/compare?dir=" + urllib.parse.quote(str(tmp_path)))
    assert "compare.json を読む" in page and _value_row(page, 0) == "water_generated"


def _value_row(page: str, i: int) -> str:
    return h.unescape(re.search(rf'name="rx_dir_{i}" value="([^"]*)"', page).group(1))


def test_english_words_match_the_desktop(web, tmp_path):
    from adit.gui import analysis_fields as AF
    app, base = web
    lang.set_language("en")
    page = h.unescape(_get(base + "/analysis"))
    for key in ("more", "stride", "th_model", "export", "export_unwrap", "compare", "uv_fwhm"):
        assert AF.LABELS[key][1] in page, key
    assert "(not computed)" in page
    page = h.unescape(_get(base + "/compare"))
    assert "Compare runs" in page and "Base directory" in page and "Coefficient ν" in page
