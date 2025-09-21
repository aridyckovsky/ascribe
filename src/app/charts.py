from __future__ import annotations

import altair as alt
import polars as pl

from crv.viz import events as _events
from crv.viz import identity as _identity
from crv.viz.base import normalize_time_object, to_values, validate_schema
from crv.viz.networks import compute_circular_layout, plot_network
from crv.viz.timeseries import (
    plot_cee_small_multiples,
    plot_counts_by_t,
    plot_endowment,
    plot_holdings_rate,
    plot_valuation,
)


# Uniform chart defaults for a professional look
def _apply_chart_defaults(ch: alt.TopLevelMixin) -> alt.TopLevelMixin:
    try:
        return (
            ch.configure_axis(labelFontSize=12, titleFontSize=12, grid=True)
            .configure_legend(labelFontSize=12, titleFontSize=12)
            .configure_title(fontSize=14)
            .configure_view(strokeOpacity=0)
        )
    except Exception:
        # If configuration fails (e.g., non-top-level), return chart as-is
        return ch


# ----------------------------
# Layering helpers (no inline casting in UI)
# ----------------------------


def layer_with_rule_y(base: object, y: float, *, color: str = "#999") -> alt.LayerChart:
    """Return a LayerChart that overlays a horizontal rule at y on the base chart.

    Args:
        base (alt.TopLevelMixin): Base chart to layer on.
        y (float): Y value for the rule.
        color (str): Rule color (default '#999').

    Returns:
        alt.LayerChart: Layered chart.
    """
    rule = alt.Chart(alt.Data(values=[{"y": float(y)}])).mark_rule(color=color).encode(y="y:Q")
    return alt.layer(base, rule)  # type: ignore


def layer_with_overlay(base: object, overlay: object) -> alt.LayerChart:
    """Return a LayerChart combining a base chart with an overlay chart.

    Args:
        base (alt.TopLevelMixin): Base chart.
        overlay (alt.TopLevelMixin): Overlay chart (e.g., event rules).

    Returns:
        alt.LayerChart: Layered chart.
    """
    return alt.layer(base, overlay)  # type: ignore


# ----------------------------
# Overview
# ----------------------------


def overview_counts_by_t(at_df: pl.DataFrame) -> alt.TopLevelMixin:
    """Mini bar chart of counts by t (delegates to timeseries.plot_counts_by_t)."""
    ch = plot_counts_by_t(at_df)
    return _apply_chart_defaults(ch.properties(title="Counts by time (t)"))


# ----------------------------
# Time series (server-side slice then reuse existing builders)
# ----------------------------


def _apply_ts_sampling(
    df: pl.DataFrame, *, max_points: int | None, stride: int | None
) -> pl.DataFrame:
    if stride is not None and stride > 1:
        return (
            df.sort("t").with_row_index(name="_rn").filter(pl.col("_rn") % stride == 0).drop("_rn")
        )
    if max_points is not None and max_points > 0 and df.height > max_points:
        # Approx even sample by stride
        stride = max((df.height + max_points - 1) // max_points, 1)
        return (
            df.sort("t").with_row_index(name="_rn").filter(pl.col("_rn") % stride == 0).drop("_rn")
        )
    return df


def apply_ts_sampling(
    df: pl.DataFrame, *, max_points: int | None = None, stride: int | None = None
) -> pl.DataFrame:
    """Public wrapper for internal sampling; stable name for external callers."""
    return _apply_ts_sampling(df, max_points=max_points, stride=stride)


def ts_endowment_chart(
    at_df: pl.DataFrame,
    *,
    group_field: str | None,
    by_object_if_no_group: bool = True,
    ts_max_points: int | None = None,
    ts_stride: int | None = None,
) -> alt.TopLevelMixin:
    """Band+line endowment. Sampling applied to raw rows before aggregation."""
    need = {"t", "s_io"}
    if group_field:
        need.add(group_field)
    if by_object_if_no_group:
        need.add("o")
    df = at_df.select([c for c in at_df.columns if c in need]).clone()
    df = _apply_ts_sampling(df, max_points=ts_max_points, stride=ts_stride)
    return _apply_chart_defaults(
        plot_endowment(df, group=group_field, by_object=by_object_if_no_group)
    )


def ts_valuation_chart(
    at_df: pl.DataFrame,
    *,
    cost: float | None,
    group_field: str | None,
    ts_max_points: int | None = None,
    ts_stride: int | None = None,
) -> alt.TopLevelMixin:
    need = {"t", "value_score"}
    if group_field:
        need.add(group_field)
    df = at_df.select([c for c in at_df.columns if c in need]).clone()
    df = _apply_ts_sampling(df, max_points=ts_max_points, stride=ts_stride)
    return _apply_chart_defaults(plot_valuation(df, cost=cost, group=group_field))


def ts_holdings_rate_chart(
    at_df: pl.DataFrame,
    *,
    group_field: str | None,
    ts_max_points: int | None = None,
    ts_stride: int | None = None,
) -> alt.TopLevelMixin:
    need = {"t", "y_io"}
    if group_field:
        need.add(group_field)
    df = at_df.select([c for c in at_df.columns if c in need]).clone()
    df = _apply_ts_sampling(df, max_points=ts_max_points, stride=ts_stride)
    return _apply_chart_defaults(plot_holdings_rate(df, group=group_field))


# ----------------------------
# Events timeline and overlays
# ----------------------------


def events_timeline_chart(
    events_df: pl.DataFrame,
    *,
    types: list[str] | None = None,
    filter_i: int | None = None,
    filter_o: int | None = None,
) -> alt.TopLevelMixin:
    """Events timeline (delegates to crv.viz.events.timeline_chart)."""
    return _apply_chart_defaults(
        _events.timeline_chart(
            events_df,
            types=types,
            filter_i=[filter_i] if filter_i is not None else None,
            filter_o=[filter_o] if filter_o is not None else None,
        )
    )


def overlay_event_rules(
    events_df: pl.DataFrame, *, types: list[str] | None = None
) -> alt.TopLevelMixin:
    """Vertical rules overlay (delegates to crv.viz.events.overlay_rules)."""
    return _apply_chart_defaults(_events.overlay_rules(events_df, types=types))


# ----------------------------
# Network snapshot at t_sel
# ----------------------------


def network_snapshot_chart(
    rel_df: pl.DataFrame,
    at_df: pl.DataFrame | None,
    *,
    t_sel: int,
    edge_threshold: float | None = 0.05,
    network_max_edges: int | None = None,
) -> alt.TopLevelMixin:
    """Build network snapshot using relations at a given time."""
    rel_df = normalize_time_object(rel_df)
    validate_schema(rel_df, {"t": pl.Int64, "i": pl.Int64, "j": pl.Int64})
    if "a_ij" not in rel_df.columns:
        raise ValueError("relations must include a_ij")

    # Filter at t_sel
    r = rel_df.filter(pl.col("t") == t_sel)
    if r.height == 0:
        # Empty placeholder
        return _apply_chart_defaults(
            alt.Chart(alt.Data(values=[]))
            .mark_text()
            .encode(text=alt.value(f"No edges at t={t_sel}"))
        )

    # Threshold or top-K by |a_ij|
    r = r.with_columns([pl.col("a_ij").abs().alias("weight")])
    if edge_threshold is not None:
        r = r.filter(pl.col("weight") >= float(edge_threshold))
    else:
        # No threshold provided: drop zero-weight links so we don't draw a fully connected graph
        r = r.filter(pl.col("weight") > 0)
    if network_max_edges is not None and r.height > network_max_edges:
        r = r.sort("weight", descending=True).head(network_max_edges)
    # If after filtering there are no edges, return a placeholder rather than drawing zero-weight edges
    if r.height == 0:
        return _apply_chart_defaults(
            alt.Chart(alt.Data(values=[]))
            .mark_text()
            .encode(text=alt.value(f"No edges at t={t_sel} (post-filter)"))
        )

    node_ids = sorted(set(r["i"].to_list()) | set(r["j"].to_list()))
    layout = compute_circular_layout(node_ids)

    # Optional group coloring from at_df at this t
    nodes = layout
    if at_df is not None and {"agent_id", "group", "t"}.issubset(set(at_df.columns)):
        gmap = (
            at_df.filter(pl.col("t") == t_sel)
            .select(["agent_id", "group"])
            .unique(keep="first")
            .rename({"agent_id": "i"})
        )
        if gmap.height > 0:
            nodes = nodes.join(gmap, on="i", how="left")
    # Fallback: ensure a nominal 'group' column exists for coloring/validation
    if "group" not in nodes.columns:
        nodes = nodes.with_columns(pl.lit("all").alias("group"))

    # Preserve src/dst before joins so optimizer doesn't drop them
    r2 = r.with_columns([pl.col("i").alias("src"), pl.col("j").alias("dst")])

    edges = (
        r2.join(layout.rename({"i": "src", "x": "x1", "y": "y1"}), left_on="i", right_on="src")
        .join(layout.rename({"i": "dst", "x": "x2", "y": "y2"}), left_on="j", right_on="dst")
        .select(["src", "dst", "x1", "y1", "x2", "y2", "weight"])
    )
    return _apply_chart_defaults(
        plot_network(nodes, edges, node_color="group", node_size=None, edge_weight="weight")
    )


# ----------------------------
# Triads for agent_sel at t_sel
# ----------------------------


def triads_chart(
    b_df: pl.DataFrame,
    at_df: pl.DataFrame | None,
    rel_df: pl.DataFrame | None,
    *,
    agent_sel: int,
    t_sel: int,
    triads_top_j: int = 3,
    triads_top_o: int = 6,
) -> alt.TopLevelMixin:
    """Facet per-agent identity triads by peer j (rows) and object o (columns), plus mean bar (delegates to crv.viz.identity)."""
    return _apply_chart_defaults(
        _identity.plot_identity_triads(
            b_df=b_df,
            at_df=at_df,
            rel_df=rel_df,
            agent_sel=agent_sel,
            t_sel=t_sel,
            top_j=triads_top_j,
            top_o=triads_top_o,
        )
    )


# ----------------------------
# CEE small multiples
# ----------------------------


def cee_small_multiples_chart(
    cee_df: pl.DataFrame,
    *,
    cee_max_points: int | None = None,
    cee_stride: int | None = None,
    object_col: str = "o",
    group_col: str = "group",
) -> alt.TopLevelMixin:
    """Stride/cap per object, then delegate to plot_cee_small_multiples."""
    # Validate minimally (plot_cee_small_multiples will perform strict checks)
    if not {"t", object_col, group_col, "cee"}.issubset(set(cee_df.columns)):
        raise ValueError("cee_df missing required columns")

    df = cee_df
    # Apply stride per object to keep points bounded
    if cee_stride is not None and cee_stride > 1:
        parts: list[pl.DataFrame] = []
        for _, g in df.group_by(object_col, maintain_order=True):
            g2 = (
                g.sort("t")
                .with_row_index(name="_rn")
                .filter(pl.col("_rn") % cee_stride == 0)
                .drop("_rn")
            )
            parts.append(g2)
        df = pl.concat(parts, how="vertical") if parts else df
    elif cee_max_points is not None and cee_max_points > 0:
        # Approx cap per object
        out_parts: list[pl.DataFrame] = []
        for o, g in df.group_by(object_col, maintain_order=True):
            n = g.height
            if n <= cee_max_points:
                out_parts.append(g)
            else:
                stride = max((n + cee_max_points - 1) // cee_max_points, 1)
                out_parts.append(
                    g.sort("t")
                    .with_row_index(name="_rn")
                    .filter(pl.col("_rn") % stride == 0)
                    .drop("_rn")
                )
        df = pl.concat(out_parts, how="vertical")

    return _apply_chart_defaults(
        plot_cee_small_multiples(df, object_col=object_col, group_col=group_col)
    )


# ----------------------------
# Identity representation (per agent at time t)
# ----------------------------


def identity_representation_chart(
    *,
    at_df: pl.DataFrame,
    rel_df: pl.DataFrame | None,
    other_df: pl.DataFrame | None,
    oo_df: pl.DataFrame | None = None,
    agent_sel: int,
    t_sel: int,
    top_o: int = 6,
    top_j: int = 6,
    show_valence: bool = True,
) -> alt.TopLevelMixin:
    """Balanced identity representation (delegates to crv.viz.identity)."""
    return _apply_chart_defaults(
        _identity.plot_identity_representation(
            at_df=at_df,
            rel_df=rel_df,
            other_df=other_df,
            oo_df=oo_df,
            agent_sel=agent_sel,
            t_sel=t_sel,
            top_o=top_o,
            top_j=top_j,
            show_valence=show_valence,
        )
    )


def extract_identity_representation(
    *,
    at_df: pl.DataFrame,
    rel_df: pl.DataFrame | None,
    other_df: pl.DataFrame | None,
    oo_df: pl.DataFrame | None,
    agent_sel: int,
    t_sel: int,
    top_o: int = 6,
    top_j: int = 6,
) -> dict[str, list[dict[str, object]]]:
    """Return the per-agent balanced-identity data at time t (no coordinates).

    Returns a dictionary with:
      - objects: [{o, s_io, rp, rn}]
      - others: [{j, a_ij}]
      - b_ijo: [{j, o, b_ijo}]
    All slicing/aggregation done in Polars.
    """
    # Slice agent-token data
    need_at = {"t", "o", "s_io", "agent_id"}
    has_rp = "rp" in at_df.columns
    has_rn = "rn" in at_df.columns
    if has_rp:
        need_at.add("rp")
    if has_rn:
        need_at.add("rn")
    if not need_at.issubset(set(at_df.columns)):
        return {"objects": [], "others": [], "b_ijo": []}

    at_t = (
        at_df.filter((pl.col("t") == t_sel) & (pl.col("agent_id") == agent_sel))
        .select([c for c in at_df.columns if c in need_at])
        .unique(keep="last")
    )
    objs = at_t.with_columns(pl.col("s_io").abs().alias("_abs")).sort("_abs", descending=True)
    objs = objs.head(top_o).drop("_abs")
    objs = objs.with_columns(
        [
            (pl.col("rp") if has_rp else pl.lit(0.0)).alias("rp"),
            (pl.col("rn") if has_rn else pl.lit(0.0)).alias("rn"),
        ]
    ).select(["o", "s_io", "rp", "rn"])

    # Slice self->other
    if rel_df is not None and {"t", "i", "j", "a_ij"}.issubset(set(rel_df.columns)):
        rdf = normalize_time_object(rel_df).filter(
            (pl.col("t") == t_sel) & (pl.col("i") == agent_sel)
        )
        others = (
            rdf.with_columns(pl.col("a_ij").abs().alias("_abs"))
            .sort("_abs", descending=True)
            .head(top_j)
            .drop("_abs")
            .select(["j", "a_ij"])
        )
    else:
        others = pl.DataFrame(
            {"j": pl.Series([], dtype=pl.Int64), "a_ij": pl.Series([], dtype=pl.Float64)}
        )

    # Slice other->object restricted to selected sets
    if other_df is not None and {"t", "i", "j", "o", "b_ijo"}.issubset(set(other_df.columns)):
        b = normalize_time_object(other_df).filter(
            (pl.col("t") == t_sel) & (pl.col("i") == agent_sel)
        )
        sels_o = set(objs["o"].to_list())
        sels_j = set(others["j"].to_list())
        b = b.filter(pl.col("o").is_in(list(sels_o)) & pl.col("j").is_in(list(sels_j))).select(
            ["j", "o", "b_ijo"]
        )
    else:
        b = pl.DataFrame(
            {
                "j": pl.Series([], dtype=pl.Int64),
                "o": pl.Series([], dtype=pl.Int64),
                "b_ijo": pl.Series([], dtype=pl.Float64),
            }
        )

    # Slice object<->object among selected objects
    if oo_df is not None and {"t", "i", "o", "op", "r_oo"}.issubset(set(oo_df.columns)):
        oo = normalize_time_object(oo_df).filter(
            (pl.col("t") == t_sel) & (pl.col("i") == agent_sel)
        )
        sels_o = set(objs["o"].to_list())
        oo = oo.filter(pl.col("o").is_in(list(sels_o)) & pl.col("op").is_in(list(sels_o))).select(
            ["o", "op", "r_oo"]
        )
    else:
        oo = pl.DataFrame(
            {
                "o": pl.Series([], dtype=pl.Int64),
                "op": pl.Series([], dtype=pl.Int64),
                "r_oo": pl.Series([], dtype=pl.Float64),
            }
        )

    return {
        "objects": to_values(objs),
        "others": to_values(others),
        "b_ijo": to_values(b),
        "object_object": to_values(oo),
    }
