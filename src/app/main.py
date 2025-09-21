"""
CRV App entrypoint.

This module provides the CLI entrypoint to launch the Streamlit UI. It defers
all UI composition to the app.ui package and exists solely to start Streamlit
programmatically or render directly when already running under Streamlit.

Usage:
    - Python execution (hands process to Streamlit):
        uv run python -m app.main --run out/demo_run --watch-ttl 10

    - Streamlit direct:
        streamlit run src/app/main.py -- --run out/demo_run --watch-ttl 10
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from app.ui import streamlit_app


def main(argv: list[str] | None = None) -> None:
    """Console entrypoint that launches Streamlit with the CRV UI.

    If already executing within a Streamlit server (environment variable
    STREAMLIT_SERVER_PORT is set), this function renders the app directly.
    Otherwise, it execs "python -m streamlit run <this_module>" to leverage
    Streamlit's reloader and argument parsing, passing through any supported
    options after "--".

    Args:
        argv (list[str] | None): Optional list of CLI arguments. If None,
            sys.argv[1:] is used.

    Examples:
        uv run python -m app.main --run out/demo_run --watch-ttl 10
        streamlit run src/app/main.py -- --run out/demo_run --watch-ttl 10
    """
    args = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(description="CRV Streamlit App")
    parser.add_argument("--run", default=None, help="Run directory (out/<run_dir>)")
    parser.add_argument(
        "--watch-ttl",
        type=int,
        default=10,
        help="Auto-refresh interval (seconds) for run discovery (0 disables).",
    )
    ns = parser.parse_args(args)

    # If invoked within Streamlit, just render
    if os.environ.get("STREAMLIT_SERVER_PORT"):
        streamlit_app(
            default_run=ns.run,
            default_roots=None,
            default_watch_ttl=int(ns.watch_ttl),
        )
        return

    # Otherwise, exec streamlit run on this module to take over the process
    app_path = Path(__file__).resolve()
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]

    passthrough: list[str] = []
    if ns.run:
        passthrough += ["--run", ns.run]
    if ns.watch_ttl is not None:
        passthrough += ["--watch-ttl", str(int(ns.watch_ttl))]
    if passthrough:
        cmd += ["--"] + passthrough

    try:
        os.execv(sys.executable, cmd)
    except Exception:
        import subprocess

        subprocess.run(cmd, check=False)


if __name__ == "__main__":
    # Support: --run, --watch-ttl after '--' when using `streamlit run`
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run", default=None)
    parser.add_argument("--watch-ttl", type=int, default=10)
    try:
        ns, _ = parser.parse_known_args(sys.argv[1:])
        streamlit_app(
            default_run=ns.run,
            default_roots=None,
            default_watch_ttl=int(ns.watch_ttl),
        )
    except SystemExit:
        # Fallback to no-arg render
        streamlit_app()
