"""
Streamlit application orchestrator for CRV.

This module composes the global header and all page tabs while delegating
supporting concerns to focused modules under app.ui.* (header, runs, helpers).
It replaces the previous monolithic src/app/ui.py with a maintainable structure.

Responsibilities:
    - Configure Streamlit page.
    - Render global header (run selector, theme, cache prefs).
    - Load core run tables via app.data with configurable caching.
    - Compute derived globals (time bounds, id lists).
    - Mount tab content (Overview, Time Series, Network, Identity, Triads, CEE, Events, Data).

Notes:
    - Charts are produced by app.charts and crv.viz.* modules.
    - All functions include Google-style docstrings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, cast

import altair as alt
import polars as pl
import streamlit as st

from app import charts as app_charts
from app.data import (
    get_time_bounds,
    load_agents_tokens,
    load_events,
    load_model_specs,
    load_object_object,
    load_other_object,
    load_relations,
)
from crv.viz.timeseries import (
    TimeseriesResult,
    list_available_metrics,
    prepare_metric_timeseries,
    render_timeseries,
)

from .header import render_header
from .helpers import compute_overview_kpis


def streamlit_app(
    default_run: str | None = None,
    default_roots: list[str] | None = None,
    default_watch_ttl: int = 10,
) -> None:
    """Render the CRV Streamlit application.

    Args:
        default_run (str | None): Optional preselected run directory path.
        default_roots (list[str] | None): Retained for compatibility; roots are managed
            in header preferences (ignored here).
        default_watch_ttl (int): Default auto-refresh interval for run discovery.

    Returns:
        None

    Notes:
        - Uses app.ui.header.render_header to render the global controls and compute a
          CacheConfig used by all loaders in app.data.
        - When no runs are found, a minimal demo run is created under out/demo_run.
    """
    del default_roots  # managed via header preferences

    # Page config
    st.set_page_config(page_title="CRV App", layout="wide")

    # Header (run selection, theme, cache preferences)
    run_dir, cache_cfg = render_header(
        default_run=default_run,
        default_watch_ttl=default_watch_ttl,
    )
    if not run_dir:
        st.error("Select a run directory (contains agents_tokens.parquet) from the header.")
        return
    run_path = Path(run_dir)

    # Load core table (agents_tokens)
    try:
        with st.spinner("Loading agents_tokens ..."):
            at_df = load_agents_tokens(str(run_path), cfg=cache_cfg)
    except FileNotFoundError as e:
        st.error(str(e))
        return
    except Exception as e:  # pragma: no cover - defensive UX
        st.error(f"Failed to load agents_tokens: {e}")
        return

    # Derived globals & identifiers
    try:
        t_min, t_max = get_time_bounds(at_df)
    except Exception:
        t_min, t_max = (0, 0)
    group_field = "group" if "group" in at_df.columns else None

    agent_ids_all = (
        sorted(set(at_df.get_column("agent_id").to_list())) if "agent_id" in at_df.columns else []
    )
    object_ids_all = sorted(set(at_df.get_column("o").to_list())) if "o" in at_df.columns else []
    group_values_all = (
        sorted(set(at_df.get_column("group").drop_nulls().to_list())) if group_field else []
    )

    # Tabs (page navigation)
    tab_overview, tab_ts, tab_net, tab_id, tab_tri, tab_cee, tab_events, tab_data = st.tabs(
        ["Overview", "Time Series", "Network", "Identity", "Triads", "CEE", "Events", "Data"]
    )

    # ----------------------------
    # Overview
    # ----------------------------
    with tab_overview:
        st.subheader("Run summary")
        try:
            specs = load_model_specs(str(run_path), cfg=cache_cfg)
            if specs:
                st.table(specs)
            else:
                st.caption("No model.parquet/metadata.json found.")
        except Exception:
            st.caption("Failed to load run specs.")

        # KPIs
        kpi = compute_overview_kpis(at_df)
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Final mean value_score", f"{kpi['final_mean_value']:.3f}")
        with c2:
            st.metric("Final holdings rate", f"{100.0 * kpi['final_hold_rate']:.1f}%")

        st.subheader("Row count by time")
        try:
            ch = app_charts.overview_counts_by_t(at_df)
            st.altair_chart(cast(Any, ch), theme=None, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to render counts chart: {e}")

    # ----------------------------
    # Time Series
    # ----------------------------
    with tab_ts:
        metric_specs = list_available_metrics()
        metric_id_to_label = {spec["id"]: spec["label"] for spec in metric_specs}
        metric_options = [spec["id"] for spec in metric_specs]
        default_metrics = [
            m for m in ("value_score", "s_io", "y_io") if m in metric_options
        ] or metric_options[:1]

        with st.sidebar.expander("Time Series Controls", expanded=True):
            selected_metrics = st.multiselect(
                "Metrics",
                options=metric_options,
                default=default_metrics,
                format_func=lambda metric_id: str(metric_id_to_label.get(metric_id, metric_id)),
                key="ts_metrics_select",
            )
            scope_choice = st.radio(
                "Scope",
                options=["Aggregate", "Group", "Agent"],
                index=0,
                key="ts_scope_choice",
            )
            scope_map = {"Aggregate": "aggregate", "Group": "group", "Agent": "agent"}
            scope = scope_map[scope_choice]
            if scope == "group" and not group_field:
                st.warning("Run data has no group column; falling back to aggregate scope.")
                scope = "aggregate"
            scope_literal = cast(Literal["aggregate", "group", "agent"], scope)

            show_quantiles = st.checkbox("Show quantile band", value=True, key="ts_show_quantiles")
            quantile_band = st.slider(
                "Quantile band (low/high)",
                min_value=0.0,
                max_value=1.0,
                value=(0.1, 0.9),
                step=0.05,
                key="ts_quantile_band",
            )
            split_by_object_default = scope != "group"
            split_by_object = st.checkbox(
                "Split lines by object",
                value=split_by_object_default,
                key="ts_split_objects",
            )
            ts_max_points = st.number_input(
                "Max points (0 disables)",
                min_value=0,
                value=500,
                step=100,
                key="ts_max_points",
            )
            ts_stride = st.number_input(
                "Stride (every k; 0 disables)",
                min_value=0,
                value=0,
                step=1,
                key="ts_stride",
            )
            cost_line = None
            if "value_score" in selected_metrics:
                cost_line = st.number_input(
                    "Reference line",
                    min_value=-10.0,
                    max_value=10.0,
                    value=0.0,
                    step=0.05,
                    key="ts_cost_line",
                )

        with st.sidebar.expander("Filters", expanded=False):
            agent_filter: list[int] | None = None
            if scope == "agent" and agent_ids_all:
                agent_selection = st.multiselect(
                    "Agents",
                    options=agent_ids_all,
                    default=agent_ids_all[:1],
                    key="ts_agent_filter",
                )
                agent_filter = agent_selection or None

            group_filter: list[str] | None = None
            if scope in ("group", "aggregate") and group_values_all:
                default_groups = group_values_all if scope == "group" else []
                group_selection = st.multiselect(
                    "Groups",
                    options=group_values_all,
                    default=default_groups,
                    key="ts_group_filter",
                )
                group_filter = group_selection or None

            object_filter: list[int] | None = None
            if object_ids_all:
                object_selection = st.multiselect(
                    "Objects", options=object_ids_all, default=[], key="ts_object_filter"
                )
                object_filter = object_selection or None

        with st.sidebar.expander("Event Overlays", expanded=False):
            overlay_enabled = st.checkbox(
                "Show event markers", value=False, key="ts_overlay_enabled"
            )
            events_df = None
            overlay_types: list[str] = []
            if overlay_enabled:
                try:
                    events_df = load_events(str(run_path), cfg=cache_cfg)
                except Exception:
                    events_df = None
                if events_df is None or events_df.is_empty():
                    st.caption("No events available for overlay.")
                    overlay_enabled = False
                else:
                    type_opts = (
                        sorted(set(events_df.get_column("type").to_list()))
                        if "type" in events_df.columns
                        else []
                    )
                    overlay_types = st.multiselect(
                        "Event types",
                        options=type_opts,
                        default=type_opts,
                        key="ts_overlay_types",
                    )

        # Brush and charts
        try:
            counts = at_df.group_by("t").agg(pl.len().alias("n")).sort("t")
        except Exception:
            counts = pl.DataFrame({"t": [], "n": []})
        top_vals = counts.to_dicts()
        brush = alt.selection_interval(name="brush_t", encodings=["x"])
        top = (
            alt.Chart(alt.Data(values=top_vals))
            .mark_bar()
            .encode(x="t:Q", y="n:Q")
            .add_params(brush)
            .properties(title="Time window (brush to filter below)")
        )

        metric_charts: list[alt.Chart | alt.LayerChart] = []
        quantiles_arg = cast(tuple[float, float] | None, st.session_state.get("ts_quantile_band"))
        if not st.session_state.get("ts_show_quantiles", True):
            quantiles_arg = None
        max_points = int(st.session_state.get("ts_max_points", 500)) or None
        stride = int(st.session_state.get("ts_stride", 0)) or None

        for metric_id in selected_metrics:
            result = prepare_metric_timeseries(
                at_df,
                metric_id,
                scope=scope_literal,
                agent_ids=agent_filter,
                object_ids=object_filter,
                groups=group_filter,
                quantiles=quantiles_arg,
                split_by_object=split_by_object,
            )

            frame = app_charts.apply_ts_sampling(
                result.frame,
                max_points=max_points,
                stride=stride,
            )
            sampled_result = TimeseriesResult(
                frame=frame,
                value_field=result.value_field,
                color_field=result.color_field,
                quantile_fields=result.quantile_fields,
                tooltip_fields=result.tooltip_fields,
            )

            chart = render_timeseries(sampled_result)

            if metric_id == "value_score":
                cost_line_val = st.session_state.get("ts_cost_line", None)
                if cost_line_val is not None:
                    chart = app_charts.layer_with_rule_y(chart, float(cost_line_val))

            overlay_chart = None
            if overlay_enabled and events_df is not None and not events_df.is_empty():
                ev = events_df
                if agent_filter:
                    ev = ev.filter(pl.col("i").is_in(agent_filter))
                if object_filter:
                    ev = ev.filter(pl.col("o").is_in(object_filter))
                if not ev.is_empty():
                    overlay_chart = app_charts.overlay_event_rules(ev, types=overlay_types or None)

            chart = chart.transform_filter(brush)
            if overlay_chart is not None:
                chart = app_charts.layer_with_overlay(chart, overlay_chart.transform_filter(brush))

            metric_charts.append(
                chart.properties(title=metric_id_to_label.get(metric_id, metric_id))
            )

        if not metric_charts:
            st.info("Select at least one metric to display.")
            ts_block = top
        else:
            ts_block = alt.vconcat(top, *metric_charts)
        st.altair_chart(cast(Any, ts_block), theme=None, use_container_width=True)

    # ----------------------------
    # Network
    # ----------------------------
    with tab_net:
        with st.sidebar.expander("Network Controls", expanded=True):
            t_sel = st.slider(
                "Time t", min_value=t_min, max_value=t_max, value=t_min, step=1, key="net_t_sel"
            )
            edge_mode = st.radio(
                "Filter edges by", options=["Threshold", "Top-K"], index=0, key="net_edge_mode"
            )
            net_edge_thresh = st.number_input(
                "Edge threshold |a_ij| \u2265",
                min_value=0.0,
                value=0.05,
                step=0.01,
                format="%.2f",
                key="net_edge_thresh",
            )
            net_max_edges = st.number_input(
                "Max edges (0 means unlimited)",
                min_value=0,
                value=200,
                step=50,
                key="net_max_edges",
            )

        st.subheader(f"Agent network at t = {t_sel}")
        rel_df = load_relations(str(run_path), cfg=cache_cfg)
        if rel_df is None:
            st.info("relations.parquet not found.")
        else:
            ch_net = app_charts.network_snapshot_chart(
                rel_df,
                at_df=at_df,
                t_sel=int(t_sel),
                edge_threshold=float(net_edge_thresh) if edge_mode == "Threshold" else None,
                network_max_edges=int(net_max_edges)
                if (edge_mode == "Top-K" and net_max_edges > 0)
                else None,
            )
            st.altair_chart(cast(Any, ch_net), theme=None, use_container_width=True)

    # ----------------------------
    # Identity (per-agent balanced-identity representation)
    # ----------------------------
    with tab_id:
        with st.sidebar.expander("Identity Controls", expanded=True):
            agent_ids = (
                sorted(set(at_df.get_column("agent_id").to_list()))
                if "agent_id" in at_df.columns
                else []
            )
            agent_sel: int | None = (
                cast(int, st.selectbox("Agent", options=agent_ids, index=0, key="id_agent_sel"))
                if agent_ids
                else None
            )
            t_sel = st.slider(
                "Time t", min_value=t_min, max_value=t_max, value=t_min, step=1, key="id_t_sel"
            )
            id_top_o = st.number_input(
                "Top-O objects by |s_io|", min_value=1, value=6, step=1, key="id_top_o"
            )
            id_top_j = st.number_input(
                "Top-J others by |a_ij|", min_value=1, value=6, step=1, key="id_top_j"
            )
            show_valence = st.checkbox(
                "Show object→valence edges (rp/rn)", value=True, key="id_show_valence"
            )

        st.subheader("Balanced identity representation")
        if agent_sel is None:
            st.info("No agents in agents_tokens.")
        else:
            rel_df = load_relations(str(run_path), cfg=cache_cfg)
            other_df = load_other_object(str(run_path), cfg=cache_cfg)
            oo_df = load_object_object(str(run_path), cfg=cache_cfg)
            ch_id = app_charts.identity_representation_chart(
                at_df=at_df,
                rel_df=rel_df,
                other_df=other_df,
                oo_df=oo_df,
                agent_sel=int(agent_sel),
                t_sel=int(t_sel),
                top_o=int(id_top_o),
                top_j=int(id_top_j),
                show_valence=bool(show_valence),
            )
            st.altair_chart(cast(Any, ch_id), theme=None, use_container_width=True)

    # ----------------------------
    # Triads
    # ----------------------------
    with tab_tri:
        other_df = load_other_object(str(run_path), cfg=cache_cfg)
        with st.sidebar.expander("Triads Controls", expanded=True):
            t_sel = st.slider(
                "Time t", min_value=t_min, max_value=t_max, value=t_min, step=1, key="tri_t_sel"
            )
            agent_sel: int | None = None
            if other_df is not None and "i" in other_df.columns:
                agent_ids = sorted(set(other_df.get_column("i").to_list()))
                if agent_ids:
                    agent_sel = cast(
                        int,
                        st.selectbox(
                            "Agent (for triads)", options=agent_ids, index=0, key="tri_agent_sel"
                        ),
                    )
            triads_top_j = st.number_input(
                "Triads: top-J peers", min_value=1, value=3, step=1, key="tri_top_j"
            )
            triads_top_o = st.number_input(
                "Triads: top-O objects", min_value=1, value=6, step=1, key="tri_top_o"
            )

        st.subheader(f"Identity triads at t = {t_sel}")
        if other_df is None:
            st.info("other_object.parquet not found.")
        elif agent_sel is None:
            st.info("No agent available for triads.")
        else:
            rel_df = load_relations(str(run_path), cfg=cache_cfg)
            ch_tri = app_charts.triads_chart(
                other_df,
                at_df=at_df,
                rel_df=rel_df,
                agent_sel=int(agent_sel),
                t_sel=int(t_sel),
                triads_top_j=int(triads_top_j),
                triads_top_o=int(triads_top_o),
            )
            st.altair_chart(cast(Any, ch_tri), theme=None, use_container_width=True)

    # ----------------------------
    # CEE
    # ----------------------------
    with tab_cee:
        with st.sidebar.expander("CEE Controls", expanded=True):
            cee_max_points = st.number_input(
                "CEE max points per object (0 disables cap)",
                min_value=0,
                value=500,
                step=100,
                key="cee_max_points",
            )
            cee_stride = st.number_input(
                "CEE stride (every k; 0 disables)",
                min_value=0,
                value=0,
                step=1,
                key="cee_stride",
            )
            cee_independent_y = st.checkbox(
                "Independent Y scales per object", value=False, key="cee_independent_y"
            )
            show_y0 = st.checkbox("Show y=0 reference line", value=True, key="cee_show_y0")

        st.subheader("CEE small multiples")
        cee_path = run_path / "cee.parquet"
        if not cee_path.exists():
            st.info("cee.parquet not found.")
        else:
            try:
                # Minimal cached loader for CEE (Polars-first)
                def _load_cee_impl(p: str) -> pl.DataFrame:
                    lf = pl.scan_parquet(p)
                    names = lf.collect_schema().names()
                    want = [c for c in ["t", "o", "token_id", "group", "cee"] if c in names]
                    df = lf.select(want).collect()
                    # Normalize token_id->o if present
                    if "o" not in df.columns and "token_id" in df.columns:
                        df = df.rename({"token_id": "o"})
                    return df

                if cache_cfg.persist:
                    _load_cee = st.cache_data(ttl=cache_cfg.ttl, persist="disk")(_load_cee_impl)
                else:
                    _load_cee = st.cache_data(ttl=cache_cfg.ttl)(_load_cee_impl)

                cee_df = _load_cee(str(cee_path))
                ch_cee = app_charts.cee_small_multiples_chart(
                    cee_df,
                    cee_max_points=int(cee_max_points) if cee_max_points > 0 else None,
                    cee_stride=int(cee_stride) if cee_stride > 0 else None,
                    object_col="o",
                    group_col="group",
                )
                # Optional y=0 rule overlay
                if show_y0:
                    ch_cee = app_charts.layer_with_rule_y(ch_cee, 0.0)
                # Optional independent y scales per object facet
                if cee_independent_y:
                    ch_cee = ch_cee.resolve_scale(y="independent")
                st.altair_chart(cast(Any, ch_cee), theme=None, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to load/render CEE: {e}")

    # ----------------------------
    # Events
    # ----------------------------
    with tab_events:
        with st.sidebar.expander("Events Controls", expanded=True):
            ev = load_events(str(run_path), cfg=cache_cfg)
            if ev is None or ev.is_empty():
                st.info("events.parquet not found.")
            else:
                # Options
                if "type" in ev.columns:
                    try:
                        types_opts = sorted(set(ev.get_column("type").to_list()))
                    except Exception:
                        types_opts = []
                else:
                    types_opts = []
                types_sel = st.multiselect(
                    "Event types",
                    options=types_opts,
                    default=types_opts,
                    key="events_types",
                )
                filter_i = None
                filter_o = None
                if "i" in ev.columns:
                    try:
                        i_opts = sorted(set(ev.get_column("i").to_list()))
                    except Exception:
                        i_opts = []
                    if i_opts:
                        filter_i = cast(
                            Any,
                            st.selectbox(
                                "Filter agent i (optional)",
                                options=[None] + i_opts,
                                index=0,
                                key="events_filter_i",
                            ),
                        )
                if "o" in ev.columns:
                    try:
                        o_opts = sorted(set(ev.get_column("o").to_list()))
                    except Exception:
                        o_opts = []
                    if o_opts:
                        filter_o = cast(
                            Any,
                            st.selectbox(
                                "Filter object o (optional)",
                                options=[None] + o_opts,
                                index=0,
                                key="events_filter_o",
                            ),
                        )

                st.subheader("Events timeline")
                ch_ev = app_charts.events_timeline_chart(
                    ev,
                    types=types_sel or None,
                    filter_i=cast(int, filter_i) if isinstance(filter_i, int) else None,
                    filter_o=cast(int, filter_o) if isinstance(filter_o, int) else None,
                )
                st.altair_chart(cast(Any, ch_ev), theme=None, use_container_width=True)

                st.subheader("Events preview")
                try:
                    st.dataframe(ev.head(200), width="stretch")
                    st.text(f"Rows: {ev.height}, Columns: {list(ev.columns)}")
                except Exception as e:
                    st.error(f"Failed to render events: {e}")

    # ----------------------------
    # Data (table viewer)
    # ----------------------------
    with tab_data:
        with st.sidebar.expander("Data Viewer Controls", expanded=True):
            head_n = st.number_input(
                "Show first N rows", min_value=5, value=100, step=25, key="data_head_n"
            )

        st.subheader("agents_tokens.parquet (normalized)")
        st.caption(
            "Columns shown may include: t, agent_id, o/token_id→o, s_io, rp, rn, y_io, value_score, s_pos, s_neg, salience, group"
        )
        try:
            # Already loaded at_df is normalized (step→t, token_id→o) in loader
            at_preview = at_df.head(int(head_n))
            st.dataframe(at_preview, width="stretch")
            st.text(f"Rows: {at_df.height}, Columns: {list(at_df.columns)}")
        except Exception as e:
            st.error(f"Failed to render agents_tokens: {e}")

        st.subheader("relations.parquet (if present)")
        try:
            rel_df = load_relations(str(run_path), cfg=cache_cfg)
            if rel_df is None or rel_df.is_empty():
                st.caption("Relations not found.")
            else:
                st.dataframe(rel_df.head(int(head_n)), width="stretch")
                st.text(f"Rows: {rel_df.height}, Columns: {list(rel_df.columns)}")
        except Exception as e:
            st.error(f"Failed to render relations: {e}")

        st.subheader("other_object.parquet (if present)")
        try:
            other_df = load_other_object(str(run_path), cfg=cache_cfg)
            if other_df is None or other_df.is_empty():
                st.caption("Other→object (b_ijo) not found.")
            else:
                st.dataframe(other_df.head(int(head_n)), width="stretch")
                st.text(f"Rows: {other_df.height}, Columns: {list(other_df.columns)}")
        except Exception as e:
            st.error(f"Failed to render other_object: {e}")

        st.subheader("Run specs (model.parquet + metadata.json)")
        try:
            specs = load_model_specs(str(run_path), cfg=cache_cfg)
            if specs:
                st.table(specs)
            else:
                st.caption("No model.parquet/metadata.json found or parsable.")
        except Exception as e:
            st.error(f"Failed to render specs: {e}")
