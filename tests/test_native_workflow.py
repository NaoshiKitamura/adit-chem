"""All user interfaces share the same safe native-input review workflow."""

import json

import pytest

from adit.native_workflow import NativeWorkflowError, write_import_review
from tests.test_native_import_cli import _vasp_bundle


def test_review_writes_only_report_and_draft_for_supported_bundle(tmp_path):
    source, output = tmp_path / "source", tmp_path / "review"
    _vasp_bundle(source)
    original = {p.name: p.read_bytes() for p in source.iterdir()}

    result, written = write_import_review(source, output)

    assert written == output
    assert result.spec is not None
    assert (output / "draft_spec.json").is_file()
    assert json.loads((output / "import_report.json").read_text(encoding="utf-8"))["complete"]
    assert original == {p.name: p.read_bytes() for p in source.iterdir()}


def test_review_keeps_reason_when_code_cannot_be_detected(tmp_path):
    source, output = tmp_path / "source", tmp_path / "review"
    source.mkdir()
    result, _ = write_import_review(source, output)
    assert result.spec is None
    assert (output / "import_report.json").is_file()
    assert not (output / "draft_spec.json").exists()


def test_review_refuses_existing_or_inside_source_destination(tmp_path):
    source = tmp_path / "source"
    _vasp_bundle(source)
    with pytest.raises(NativeWorkflowError):
        write_import_review(source, source / "review")
    assert not (source / "review").exists()
    output = tmp_path / "review"
    output.mkdir()
    with pytest.raises(NativeWorkflowError):
        write_import_review(source, output)
    missing = tmp_path / "missing"
    with pytest.raises(NativeWorkflowError):
        write_import_review(missing, missing)
    assert not missing.exists()
