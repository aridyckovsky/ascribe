from __future__ import annotations

from pathlib import Path
from typing import Any

import altair as alt
import polars as pl
import pytest

from crv.viz import dashboards, layers, save, timeseries


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def walk_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if p.is_file()]


def find_in_spec(obj: Any, predicate) -> bool:
    """Recursively scan a chart spec dict for a predicate match."""
    if isinstance(obj, dict):
        if predicate(obj):
            return True
        return any(find_in_spec(v, predicate) for v in obj.values())
    if isinstance(obj, list):
        return any(find_in_spec(v, predicate) for v in obj)
    return False


# 1) Static guards: no pandas, no coupling to model/Mesa


def test_no_pandas_and_decoupled() -> None:
    src_viz = Path("src") / "crv" / "viz"
    assert src_viz.exists(), "src/crv/viz directory must exist"

    forbidden_substrings = [
        "import pandas",
        "from pandas",
        "import mesa",
        "from mesa",
        "import crv_abm",
        "from crv_abm",
    ]

    for py in walk_files(src_viz):
        text = read_text(py)
        for s in forbidden_substrings:
            assert s not in text, f"Forbidden import '{s}' found in {py}"


# 2) Spec sanity for timeseries plots and interactions


def test_plot_endowment_contains_band_and_line() -> None:
    df = pl.DataFrame(
        {
            "t": [0, 0, 1, 1, 2, 2],
            "o": [0, 1, 0, 1, 0, 1],
            "s_io": [0.1, 0.2, 0.3, 0.2, 0.5, 0.4],
        }
    )
    ch = timeseries.plot_endowment(df, by_object=True)
    spec = ch.to_dict()

    # Expect a layered chart with an area (band: y and y2) and a line
    def is_area_with_y_y2(d: dict) -> bool:
        if d.get("mark") == "area" or (
            isinstance(d.get("mark"), dict) and d.get("mark", {}).get("type") == "area"
        ):
            enc = d.get("encoding", {})
            return "y" in enc and "y2" in enc
        return False

    def is_line_with_xy(d: dict) -> bool:
        if d.get("mark") == "line" or (
            isinstance(d.get("mark"), dict) and d.get("mark", {}).get("type") == "line"
        ):
            enc = d.get("encoding", {})
            return "x" in enc and "y" in enc
        return False

    assert find_in_spec(spec, is_area_with_y_y2), "Area band with y and y2 not found in spec"
    assert find_in_spec(spec, is_line_with_xy), "Line layer with x and y not found in spec"


def test_plot_cee_small_multiples_facets() -> None:
    df = pl.DataFrame(
        {
            "t": [0, 1, 0, 1],
            "o": ["A", "A", "B", "B"],
            "group": ["g1", "g1", "g1", "g1"],
            "cee": [0.1, 0.2, 0.3, 0.25],
        }
    )
    ch = timeseries.plot_cee_small_multiples(df)
    spec = ch.to_dict()
    assert "facet" in spec, "Facet block not present"
    assert "column" in spec["facet"], "Facet column not present"


def test_brush_linking_present_in_dashboard(tmp_path: Path) -> None:
    # Build a minimal in-memory "run dir" by writing a tiny parquet file
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    at = pl.DataFrame(
        {
            "t": [0, 0, 1, 1, 2, 2],
            "o": [0, 1, 0, 1, 0, 1],
            "s_io": [0.1, 0.2, 0.3, 0.2, 0.5, 0.4],
            "value_score": [0.2, 0.25, 0.3, 0.35, 0.4, 0.45],
            "y_io": [0, 1, 1, 0, 1, 1],
        }
    )
    at.write_parquet(run_dir / "agents_tokens.parquet")

    ch = dashboards.build_default_dashboard(str(run_dir), theme="crv_light", cost=0.3)
    spec = ch.to_dict()

    # Expect a named param "brush_t" and downstream transform filter referencing it
    has_param = find_in_spec(
        spec,
        lambda d: "params" in d
        and any(isinstance(p, dict) and p.get("name") == "brush_t" for p in d.get("params", [])),
    )
    has_filter = find_in_spec(spec, lambda d: d.get("filter") == {"param": "brush_t"})
    assert has_param, "Interval brush param 'brush_t' not found in spec"
    assert has_filter, "transform filter referencing 'brush_t' not found in spec"


# 3) Save HTML without converter; image save should raise when converter missing


def test_save_html_without_converter_and_image_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vals = [{"x": 0, "y": 0}, {"x": 1, "y": 1}]
    ch = alt.Chart(alt.Data(values=vals)).mark_line().encode(x="x:Q", y="y:Q")

    out_html = tmp_path / "report.html"
    save.save(ch, out_html=str(out_html))
    assert out_html.exists() and out_html.stat().st_size > 0

    # Simulate converter missing by making importlib.import_module("vl_convert") raise ImportError
    import importlib

    real_import_module = importlib.import_module

    def fake_import_module(name: str, *args, **kwargs):
        if name == "vl_convert":
            raise ImportError("simulated missing converter")
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    with pytest.raises(RuntimeError) as ei:
        save.save(ch, out_png=str(tmp_path / "report.png"))
    assert "vl-convert-python" in str(ei.value)


# Smoke tests for layers module (ensure encodings are typed)


def test_layers_line_band_points() -> None:
    vals = pl.DataFrame({"t": [0, 1, 2], "y": [0.1, 0.2, 0.3]}).to_dicts()
    ch_line = layers.layer_line(vals, x="t", y="y")
    ch_band = layers.layer_band(
        pl.DataFrame({"t": [0, 1], "lo": [0.0, 0.1], "hi": [0.2, 0.3]}).to_dicts(),
        x="t",
        y_low="lo",
        y_high="hi",
    )
    ch_pts = layers.layer_points(vals, x="t", y="y", opacity=0.2)
    # Basic sanity to ensure they produce serializable specs
    assert isinstance(ch_line.to_dict(), dict)
    assert isinstance(ch_band.to_dict(), dict)
    assert isinstance(ch_pts.to_dict(), dict)
