"""The native-input CLI writes only a review draft, never generated jobs."""

import json

from adit.convert import main


def _vasp_bundle(path, *, extra=""):
    path.mkdir()
    (path / "INCAR").write_text("ENCUT = 400\nNSW = 0\nIBRION = -1\n" + extra, encoding="utf-8")
    (path / "POSCAR").write_text(
        "Si\n1.0\n5 0 0\n0 5 0\n0 0 5\nSi\n1\nDirect\n0 0 0\n", encoding="utf-8")
    (path / "KPOINTS").write_text("Gamma mesh\n0\nGamma\n1 1 1\n0 0 0\n", encoding="utf-8")


def test_native_cli_writes_report_and_review_draft(tmp_path, capsys):
    source, output = tmp_path / "source", tmp_path / "review"
    _vasp_bundle(source)
    assert main(["import", str(source), str(output)]) == 0
    report = json.loads((output / "import_report.json").read_text(encoding="utf-8"))
    assert report["complete"]
    assert "method.encut" in report["provenance"]
    assert report["files"][str(source / "INCAR")]["sha256"]
    assert report["inferred_defaults"]
    assert (output / "draft_spec.json").is_file()
    assert not (output / "spec.json").exists()
    assert not (output / "submit.sh").exists()
    assert main(["import", str(source), str(output)]) == 1
    from adit.config import save_config
    from tests.conftest import cfg_for
    config = tmp_path / "cluster.toml"
    save_config(cfg_for(None), config)
    assert main(["calculation", str(output / "draft_spec.json"), "missing-template", str(tmp_path / "generated"),
                 "--config", str(config)]) == 1
    assert "--accept-import-defaults" in capsys.readouterr().err
    assert not (tmp_path / "generated").exists()


def test_native_cli_records_unknown_and_never_writes_draft(tmp_path, capsys):
    source, output = tmp_path / "source", tmp_path / "review"
    _vasp_bundle(source, extra="UNKNOWN_KEY = 17\n")
    assert main(["import", str(source), str(output)]) == 1
    report = json.loads((output / "import_report.json").read_text(encoding="utf-8"))
    assert not report["complete"]
    assert report["unknown"]
    assert not (output / "draft_spec.json").exists()
    error = capsys.readouterr().err
    assert "UNKNOWN_KEY = 17" in error
    assert "INCAR:4" in error


def test_native_cli_does_not_write_inside_source(tmp_path):
    source = tmp_path / "source"
    _vasp_bundle(source)
    assert main(["import", str(source), str(source / "review")]) == 1
    assert not (source / "review").exists()


def test_native_issue_reasons_are_natural_in_both_languages(tmp_path, monkeypatch):
    from adit import lang
    from adit.native_import import import_native

    source = tmp_path / "source"
    _vasp_bundle(source, extra="UNKNOWN_KEY = 17\n")
    monkeypatch.setattr(lang, "LANGUAGE", "ja")
    ja = import_native(source).unknown[0]["reason"]
    assert ja == "この INCAR キーワードには対応していません"
    monkeypatch.setattr(lang, "LANGUAGE", "en")
    en = import_native(source).unknown[0]["reason"]
    assert en == "unmapped INCAR keyword"


def test_native_cli_records_unidentified_input_without_creating_draft(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "review"
    assert main(["import", str(source), str(output)]) == 1
    report = json.loads((output / "import_report.json").read_text(encoding="utf-8"))
    assert report["code"] == "undetermined"
    assert not report["complete"]
    assert report["unsupported"]
    assert not (output / "draft_spec.json").exists()
    assert "import_report.json" in capsys.readouterr().err
