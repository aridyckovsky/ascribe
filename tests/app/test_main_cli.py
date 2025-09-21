from __future__ import annotations

import os
from pathlib import Path

import pytest

from app import main as app_main


def test_main_renders_inline(monkeypatch, tmp_path) -> None:
    called = {}

    def fake_streamlit_app(*, default_run=None, default_roots=None, default_watch_ttl=None):
        called["default_run"] = default_run
        called["default_roots"] = default_roots
        called["default_watch_ttl"] = default_watch_ttl

    monkeypatch.setenv("STREAMLIT_SERVER_PORT", "1")
    # Patch the imported symbol used inside app.main (not the package attribute)
    monkeypatch.setattr(app_main, "streamlit_app", fake_streamlit_app, raising=True)

    app_main.main(["--run", str(tmp_path), "--watch-ttl", "7"])

    assert called["default_run"] == str(tmp_path)
    assert called["default_roots"] is None
    assert called["default_watch_ttl"] == 7


def test_main_execs_streamlit(monkeypatch, tmp_path) -> None:
    # Ensure not in Streamlit context
    monkeypatch.delenv("STREAMLIT_SERVER_PORT", raising=False)

    captured = {}

    def fake_execv(exe: str, cmd: list[str]) -> None:
        captured["exe"] = exe
        captured["cmd"] = cmd
        # Prevent process handoff
        raise SystemExit

    monkeypatch.setattr(os, "execv", fake_execv, raising=True)

    with pytest.raises(SystemExit):
        app_main.main(["--run", str(tmp_path), "--watch-ttl", "3"])

    assert captured["cmd"][0] == captured["exe"]
    # Assert we launch `python -m streamlit run <path>`
    assert captured["cmd"][1:4] == ["-m", "streamlit", "run"]
    # The script path should be the path to app.main
    expected_main_path = str(Path(app_main.__file__).resolve())
    assert captured["cmd"][4] == expected_main_path
    # Passthrough args present after `--`
    assert "--" in captured["cmd"]
    dashdash_idx = captured["cmd"].index("--")
    passthrough = captured["cmd"][dashdash_idx + 1 :]
    assert passthrough == ["--run", str(tmp_path), "--watch-ttl", "3"]
