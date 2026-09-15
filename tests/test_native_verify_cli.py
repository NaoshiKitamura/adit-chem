"""The native verification command must be read-only unless a new report is requested."""

import json

from adit.convert import main
from tests.test_native_verify import make_bundle


def test_verify_cli_checks_generated_bundle_without_writing(tmp_path, capsys):
    bundle = tmp_path / "generated"
    bundle.mkdir()
    make_bundle(bundle)
    before = {p.name: p.read_bytes() for p in bundle.iterdir()}

    assert main(["verify", str(bundle)]) == 0
    assert before == {p.name: p.read_bytes() for p in bundle.iterdir()}
    output = capsys.readouterr().out
    assert "matched" in output or "一致" in output


def test_verify_cli_reports_mismatch_and_preserves_input(tmp_path, capsys):
    bundle = tmp_path / "generated"
    bundle.mkdir()
    make_bundle(bundle)
    incar = bundle / "INCAR"
    incar.write_text(incar.read_text(encoding="utf-8").replace("EDIFF = 1e-08", "EDIFF = 2e-08"), encoding="utf-8")
    before = {p.name: p.read_bytes() for p in bundle.iterdir()}
    report_path = tmp_path / "verification.json"

    assert main(["verify", str(bundle), "--report", str(report_path)]) == 1
    assert before == {p.name: p.read_bytes() for p in bundle.iterdir()}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert any(item["field"] == "method.ediff" for item in report["mismatched"])
    assert "method.ediff" in capsys.readouterr().err
    assert main(["verify", str(bundle), "--report", str(report_path)]) == 1


def test_verify_cli_rejects_report_inside_generated_bundle(tmp_path):
    bundle = tmp_path / "generated"
    bundle.mkdir()
    make_bundle(bundle)
    assert main(["verify", str(bundle), "--report", str(bundle / "verification.json")]) == 1
    assert not (bundle / "verification.json").exists()


def test_verify_cli_missing_bundle_is_failure(tmp_path):
    assert main(["verify", str(tmp_path / "missing")]) == 1
