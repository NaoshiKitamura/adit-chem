import os
import time
from pathlib import Path

import pytest

pytest.importorskip("pyte")
if os.name != "nt":
    pytest.importorskip("ptyprocess")

from adit.gui.terminal_backend import ShellSession, available, default_shell

SHELL = ["cmd.exe"] if os.name == "nt" else ["/bin/sh"]
ECHO = "echo adit-terminal" + ("\r\n" if os.name == "nt" else "\n")


def _wait_for(session: ShellSession, needle: str, seconds: float = 8.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        session.drain()
        if needle in session.text():
            return True
        time.sleep(0.05)
    return False


def test_a_shell_runs_and_its_output_reaches_the_screen(tmp_path):
    assert available()[0]
    session = ShellSession(cwd=tmp_path, command=SHELL, rows=12, cols=60)
    try:
        session.write(ECHO)
        assert _wait_for(session, "adit-terminal"), session.text()
        assert session.alive
    finally:
        session.close()


def test_the_screen_keeps_the_size_it_was_given(tmp_path):
    session = ShellSession(cwd=tmp_path, command=SHELL, rows=10, cols=40)
    try:
        assert len(session.lines()) == 10 and len(session.lines()[0]) == 40
        session.resize(20, 100)
        assert (session.rows, session.cols) == (20, 100)
        assert len(session.lines()) == 20 and len(session.lines()[0]) == 100
    finally:
        session.close()


@pytest.mark.skipif(os.name == "nt", reason="cmd.exe の出力の書式が違う")
def test_wide_characters_take_two_columns(tmp_path):
    session = ShellSession(cwd=tmp_path, command=SHELL, rows=8, cols=40)
    try:
        session.write("echo 日本語\n")
        assert _wait_for(session, "日本語"), session.text()
        row = next(r for r in session.lines() if any(c.text == "日" for c in r))
        i = next(i for i, c in enumerate(row) if c.text == "日")
        assert row[i + 1].text == ""      # 全角の 2 桁目は空
    finally:
        session.close()


def test_the_default_shell_is_a_real_program():
    argv = default_shell()
    assert argv and (Path(argv[0]).name or argv[0])


@pytest.mark.skipif(os.name == "nt", reason="Windows は別のシェル")
def test_the_editor_opens_saves_and_refuses_binaries(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from adit.gui.panels.workspace_panel import WorkspacePanel

    QApplication.instance() or QApplication([])

    (tmp_path / "in.hsd").write_text("Driver = {}\n", encoding="utf-8")
    (tmp_path / "blob.bin").write_bytes(bytes(range(256)))
    panel = WorkspacePanel(root=tmp_path)
    try:
        assert panel.open_file(tmp_path / "in.hsd") == ""
        panel.editor.insertPlainText("# note\n")
        assert panel.editor.dirty and panel.save() == ""
        assert (tmp_path / "in.hsd").read_text(encoding="utf-8").startswith("# note")
        assert panel.open_file(tmp_path / "blob.bin") != ""      # 開かない理由を返す
    finally:
        panel.close_session()
