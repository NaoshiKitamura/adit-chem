"""Read-only cross-code audit command routing."""

from types import SimpleNamespace

from adit.analysis.cli import main


def test_audit_cli_selects_requested_mode_and_reports_status(monkeypatch, capsys):
    calls = []

    def fake(paths, *, require_md):
        calls.append((paths, require_md))
        return SimpleNamespace(comparable=True, summary_text=lambda: "mechanical audit complete")

    monkeypatch.setattr("adit.analysis.audit_run_dirs", fake)
    assert main(["run_a", "--audit-with", "run_b", "--audit-kind", "energy"]) == 0
    assert calls == [(["run_a", "run_b"], False)]
    assert "mechanical audit complete" in capsys.readouterr().out


def test_audit_cli_fails_on_mismatch_without_analysis_writes(monkeypatch):
    def fake(paths, *, require_md):
        return SimpleNamespace(comparable=False, summary_text=lambda: "mismatch")

    monkeypatch.setattr("adit.analysis.audit_run_dirs", fake)
    assert main(["run_a", "--audit-with", "run_b"]) == 1


def test_audit_cli_rejects_conflicting_modes(capsys):
    assert main(["run_a", "--audit-with", "run_b", "--scan"]) == 1
    assert "--audit-with" in capsys.readouterr().err


def test_audit_cli_does_not_silently_ignore_analysis_options(capsys):
    assert main(["run_a", "--audit-with", "run_b", "--msd", "O"]) == 1
    assert "--msd" in capsys.readouterr().err
    assert main(["run_a", "--audit-with", "run_b", "--temperature", "300"]) == 1
    assert "--temperature" in capsys.readouterr().err
    assert main(["run_a", "--audit-kind=energy"]) == 1
    assert "--audit-with" in capsys.readouterr().err
