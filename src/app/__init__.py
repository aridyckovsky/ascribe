from __future__ import annotations

"""
Top-level Streamlit app package.

This package hosts the interactive CRV visualization app (Streamlit) decoupled
from the crv.* library modules. Shared visualization utilities remain under
crv.viz.*; the Streamlit UI shell and app-specific helpers live here.

CLI entrypoint (configured in pyproject.toml):
    crv-app = app.app:main
"""
