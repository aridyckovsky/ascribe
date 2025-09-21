"""
CRV App UI package.

This package contains the decomposed Streamlit UI for the CRV dashboard. It exposes
high-level orchestration and focused modules for separate concerns (header, runs,
helpers), replacing the previous monolithic src/app/ui.py.

Modules:
    - app: Streamlit application orchestrator (streamlit_app).
    - header: Global header (run picker, theme, cache preferences).
    - runs: Run discovery, caching, and demo-run creation.
    - helpers: Small cross-cutting helpers (accelerators, time formatting, KPIs).

Usage:
    from app.ui import streamlit_app
    streamlit_app(default_run="out/demo_run", default_watch_ttl=10)
"""

from __future__ import annotations

from .app import streamlit_app
from .header import render_header

__all__ = [
    "streamlit_app",
    "render_header",
]
