"""
Header (global controls) for the CRV Streamlit application.

This module renders the top-of-page controls, including:
- Run selection and discovery preferences (watch roots, refresh interval).
- Manual refresh button and optional demo-run creation on empty trees.
- Theme selection and cache preferences panel.
- Construction of a CacheConfig used by data loaders.

Notes:
    - Avoids performing heavy IO directly; uses ui.runs for scanning and caching.
    - Applies the selected CRV viz theme globally via crv.viz.theme.enable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import streamlit as st

from app.data import CacheConfig
from crv.viz import theme as crv_theme

from .helpers import enable_vegafusion_optional, format_ts, humanize_ago
from .runs import cached_list_runs, create_min_demo_run, list_runs_impl


def render_header(
    *,
    default_run: str | None,
    default_watch_ttl: int,
) -> tuple[str, CacheConfig]:
    """Render the global header and return the selected run path and cache config.

    The header provides:
      - Run selector populated from discovered runs under configured roots.
      - Preferences for watch roots and auto-refresh interval.
      - Theme selector (crv_light/crv_dark).
      - Cache controls: TTL and persist-to-disk toggle.

    Args:
        default_run (str | None): Optional preselected run path.
        default_watch_ttl (int): Default auto-refresh interval for run discovery.

    Returns:
        tuple[str, CacheConfig]: (selected_run_path_or_empty, cache_config)

    Notes:
        - When no runs are found under the current roots, a minimal demo run is
          created under 'out/demo_run' and a subsequent refresh is triggered.
        - The cache configuration returned is used by app.data loaders to build
          decorated callables with matching Streamlit caching semantics.
    """
    # Title and optional accelerator
    st.markdown("### CRV App")
    accel_msg = enable_vegafusion_optional()
    if accel_msg:
        st.caption(accel_msg)

    # Session defaults
    if "watch_roots" not in st.session_state:
        st.session_state["watch_roots"] = ["out"]
    if "watch_ttl" not in st.session_state:
        st.session_state["watch_ttl"] = int(default_watch_ttl)
    if "watch_refresh_bump" not in st.session_state:
        st.session_state["watch_refresh_bump"] = 0
    if "theme_choice" not in st.session_state:
        st.session_state["theme_choice"] = "crv_light"
    if "cache_ttl" not in st.session_state:
        st.session_state["cache_ttl"] = 600
    if "cache_persist" not in st.session_state:
        st.session_state["cache_persist"] = False

    # Resolve runs list (cached)
    roots = tuple(sorted(set(map(str, st.session_state["watch_roots"] or ["out"]))))
    runs = cached_list_runs(roots, 200)

    # If nothing in 'out', try 'runs'
    if not runs and ("runs" not in roots) and Path("runs").exists():
        runs = list_runs_impl(["runs"], 200)

    # If still none, create demo run
    if not runs:
        try:
            demo_path = Path("out") / "demo_run"
            create_min_demo_run(demo_path)
            st.success(f"No runs found. Created demo run at {demo_path}")
            st.session_state["watch_refresh_bump"] += 1
            runs = cached_list_runs(tuple(["out"]), 200)
        except Exception as e:  # pragma: no cover - defensive UX
            st.error(f"Failed to create demo run automatically: {e}")

    # Build header columns
    c1, c2, c3 = st.columns([0.42, 0.38, 0.20])

    # Left: Run selector and updated caption
    option_to_path: dict[str, str] = {}
    options: list[str] = []
    for item in runs:
        label = f"{item['name']} — updated {humanize_ago(item['mtime'])}"
        option_to_path[label] = item["path"]
        options.append(label)
    selected_label_default_index = 0

    # Preselect by default_run if provided, else prior session state if present
    if default_run:
        try:
            dpath = str(Path(default_run).resolve())
            for lab, pth in option_to_path.items():
                if str(Path(pth).resolve()) == dpath:
                    selected_label_default_index = options.index(lab)
                    break
        except Exception:
            pass
    elif (
        "selected_run_label" in st.session_state
        and st.session_state["selected_run_label"] in options
    ):
        selected_label_default_index = options.index(st.session_state["selected_run_label"])

    with c1:
        selected_label = st.selectbox(
            "Run",
            options=options or ["(no runs found)"],
            index=selected_label_default_index if options else 0,
            key="run_selector_header",
        )
        selected_run_path = option_to_path.get(selected_label, "") if options else ""
        # Updated timestamp
        if selected_run_path:
            try:
                mtime = Path(selected_run_path).stat().st_mtime
            except Exception:
                mtime = 0.0
            st.caption(f"Updated: {format_ts(mtime)} ({humanize_ago(mtime)})")
        else:
            st.caption("Select a run directory containing agents_tokens.parquet.")

    # Middle: Refresh + Preferences (watch roots)
    with c2:
        cols_mid = st.columns([0.33, 0.67])
        with cols_mid[0]:
            if st.button("Refresh"):
                st.session_state["watch_refresh_bump"] += 1
                st.rerun()
        with cols_mid[1]:
            with st.expander("Preferences", expanded=False):
                # Watch roots (global)
                roots_all = st.multiselect(
                    "Watch roots",
                    options=sorted(set(st.session_state["watch_roots"] + ["out", "runs"])),
                    default=st.session_state["watch_roots"],
                    help="Directories scanned recursively for runs.",
                    key="pref_watch_roots",
                )
                add_root = st.text_input(
                    "Add root (absolute or relative path)",
                    value="",
                    placeholder="e.g., runs/local or /abs/path/to/runs",
                    key="pref_watch_add_root",
                )
                if add_root:
                    p = Path(add_root)
                    if p.exists():
                        if str(p) not in roots_all:
                            roots_all.append(str(p))
                    else:
                        st.caption("Path does not exist; not added.")
                st.session_state["watch_roots"] = roots_all or ["out"]

                # Auto-refresh interval (used for caching TTL)
                watch_ttl = st.number_input(
                    "Auto-refresh interval (seconds)",
                    min_value=0,
                    value=int(st.session_state["watch_ttl"]),
                    step=5,
                    key="pref_watch_ttl",
                )
                st.session_state["watch_ttl"] = int(watch_ttl)

                st.caption(
                    f"Watching {len(st.session_state['watch_roots'])} root(s), found {len(runs)} run(s)."
                )

    # Right: Theme + Cache Preferences (global)
    with c3:
        theme_choice = st.selectbox(
            "Theme",
            options=["crv_light", "crv_dark"],
            index=0 if st.session_state["theme_choice"] == "crv_light" else 1,
            key="theme_choice_header",
        )
        st.session_state["theme_choice"] = theme_choice

        # Global cache settings (apply via CacheConfig)
        with st.expander("Cache", expanded=False):
            ttl = st.number_input(
                "Cache TTL (seconds)",
                min_value=0,
                value=int(st.session_state["cache_ttl"]),
                step=60,
                help="0 disables TTL",
                key="cache_ttl_header",
            )
            persist = st.checkbox(
                "Persist to disk",
                value=bool(st.session_state["cache_persist"]),
                key="cache_persist_header",
            )
            st.session_state["cache_ttl"] = int(ttl)
            st.session_state["cache_persist"] = bool(persist)

    # Apply theme globally
    theme_val: Literal["crv_light", "crv_dark"] = (
        "crv_light" if st.session_state["theme_choice"] == "crv_light" else "crv_dark"
    )
    crv_theme.enable(theme_val)  # type: ignore[arg-type]

    # Update selected run in state
    st.session_state["selected_run_label"] = selected_label
    st.session_state["selected_run_path"] = selected_run_path or (default_run or "")

    # Build cache config for loaders
    cache_cfg = CacheConfig(
        ttl=int(st.session_state["cache_ttl"]) if int(st.session_state["cache_ttl"]) > 0 else None,
        persist=bool(st.session_state["cache_persist"]),
    )

    return (st.session_state["selected_run_path"] or "", cache_cfg)
