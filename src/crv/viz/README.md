# CRV Visualization — Altair (Vega‑Lite) + Polars

Composable, DRY, typed visualization utilities for CRV simulations. All heavy transforms are done in Polars; Altair receives inline data via values=list[dict] (df.to_dicts()). This package is decoupled from modeling code (no Mesa, no model imports, no pandas in library code).

Key features

- Polars-first: groupby, quantiles, rates, ECDF computed in Polars
- Altair at the edge: render-only, with lightweight interactive transforms where appropriate
- Composable layers: reusable line/band/points/rule layers to assemble complex charts
- Accessible defaults: theme with tableau10, readable axes/legends, sensible sizes
- Interactivity: examples with interval brush (selection param) and linked filtering
- Saving: HTML always; PNG/SVG/PDF via vl-convert-python
- Streamlit app: server-backed, Polars-first slicing, small inline payloads; optional VegaFusion

Install and entrypoint

- Runtime dependencies declared in pyproject.toml:
  - altair>=5.5.0
  - polars>=1.33
  - vl-convert-python>=1.6.0 (for PNG/SVG/PDF)
  - streamlit>=1.49.1
  - vegafusion>=2.0.2 (optional accelerator)
- CLI:
  - crv-viz-report = crv.viz.dashboards:cli_report
  - crv-app = app.ui:main

Streamlit (default for large data)

- The Streamlit app is the default UX for large/interactive runs. It performs Polars-first transforms on the server and only sends the small slice needed to Altair.
- Rendering uses st.altair_chart(chart, theme=None, use_container_width=True) so our Altair theme applies (per Streamlit docs).
- Optional VegaFusion is attempted at startup; if installed, we enable it via alt.data_transformers.enable("vegafusion"). The app still runs without it.

Usage:

```bash
# Optional accelerator
uv add vegafusion

# Generate a run from the example simulation config (writes to out/example_run)
uv run --package crv-abm -- python -m crv.world.sim --config src/crv/world/example_simulation.yaml

# Launch the app (recommended)
uv run crv-app --run out/demo_run

# Or run Streamlit directly
uv run streamlit run src/app/ui.py -- --run out/demo_run
```

Quick start (Python)

- Enable theme and plot an endowment time series with uncertainty band:

  ```python
  import polars as pl
  from crv.viz import theme, timeseries, save

  theme.enable("crv_light")

  at = pl.DataFrame({
      "t": [0,0,1,1,2,2],
      "o": [0,1,0,1,0,1],
      "s_io": [0.1,0.2,0.3,0.2,0.5,0.4],
  })

  ch = timeseries.plot_endowment(at, by_object=True)  # color by object "o"
  save.save(ch, out_html="out/demo_endowment.html")
  # Optional (requires vl-convert-python): save.save(ch, out_png="out/demo_endowment.png")
  ```

Working with Parquet or in-memory DataFrames

- Most APIs accept either:
  - A Polars DataFrame
  - A path to a Parquet file containing the expected columns (lazy scanned via pl.scan_parquet and collected with projection pushdown)
- Example (Parquet path):
  ```python
  ch = timeseries.plot_valuation("out/run/agents_tokens.parquet", cost=0.25)
  ```

Default dashboard (with brush selection)

- Build an interactive dashboard with a top interval brush that filters downstream charts:
  ```python
  from crv.viz import dashboards, theme, save
  theme.enable("crv_light")
  ch = dashboards.build_default_dashboard("out/run_dir", theme="crv_light", cost=0.3)
  save.save(ch, out_html="report.html")
  ```

CLI usage

- Build the default dashboard from a run directory:
  ```bash
  crv-viz-report --run out/<run_dir> --theme crv_light --out report.html
  # Optionally, export PNG (requires vl-convert-python):
  crv-viz-report --run out/<run_dir> --theme crv_light --out report.html --png report.png
  ```
- Flags:
  - --run: directory containing agents_tokens.parquet (and optionally cee.parquet)
  - --theme: crv_light | crv_dark
  - --out: output HTML path
  - --png: optional PNG path
  - --cost: optional cost line for valuation panel

API overview

- Theme
  - crv.viz.theme.enable("crv_light" | "crv_dark")
- Base utilities
  - crv.viz.base.to_values(df): list[dict]
  - crv.viz.base.chart_from(df_or_values, width=380, height=220)
  - crv.viz.base.validate_schema(df, required)
  - crv.viz.base.scan_parquet_columns(path, columns)
- Layers (reusable)
  - layer_line(values, x, y, color=None, tooltip=None)
  - layer_band(values, x, y_low, y_high, color=None, opacity=0.2)
  - layer_points(values, x, y, color=None, opacity=0.3, size=None)
  - layer_rule_y(value, color="#888", stroke_dash=[4,4])
- Time series
  - plot_endowment(df_or_path, group=None, by_object=True, quantiles=(0.1,0.9))
  - plot_valuation(df_or_path, cost=None, group=None)
  - plot_holdings_rate(df_or_path, group=None)
  - plot_cee_small_multiples(df_cee, object_col="o", group_col="group")
- Distributions
  - plot_histogram(df, x, group=None, bins=30)
  - plot_ecdf(df, x, group=None)
  - plot_density(df, x, group=None, bandwidth=None) # small data only
- Networks
  - plot_network(nodes_df, edges_df, node_color="group", node_size="value", edge_weight="weight")
- Dashboards
  - build_default_dashboard(run_dir, theme="crv_light", cost=None)
  - cli_report()
- Save helpers
  - save.save(chart, out_html=None, out_png=None, out_svg=None, out_pdf=None)
  - save.to_url(chart): Vega editor URL

Data contracts (schemas)

- agents_tokens.parquet (inputs for time series):
  - t: int (time)
  - i: int (agent id)
  - o: int (object/token id)
  - s_io: float (endowment [-1,1])
  - rp: float (object→V+)
  - rn: float (object→V-)
  - y_io: int (holding; typically 0/1)
  - value_score: float
- cee.parquet (optional)
  - t: int
  - o: int | str
  - group: str
  - cee: float
- events.parquet (optional but recommended)
  - t: int (derived from step)
  - type: str (Acquire, Relinquish, PeerExchange, CentralExchange, Chat, ...)
  - i/j/o/op/p: ints where applicable (agent, peer, object ids)
  - val: int (±1 stance) when applicable
  - mode: str acquisition mode (choice | assigned)
  - delivered/received: JSON strings encoding central venue token flows
  - recipients: JSON string of chat recipients (empty list for broadcasts)
  - content: chat transcript payload (UTF-8)
- networks (precomputed layout; no layout here)
  - nodes: i:int, x:float, y:float, group:(str|int), value:float?
  - edges: src:int, dst:int, x1:float, y1:float, x2:float, y2:float, weight:float?

Accessibility and performance

- Use “tableau10” for categorical color by default
- Keep tooltips minimal to reduce payload size
- Prefer facets/small multiples over dual axes
- Pre-compute aggregations in Polars; keep Altair transforms lightweight
- For very large data, consider static image exports (PNG/SVG/PDF) for distribution

Minimal end-to-end example

- Endowment with band + line:

  ```python
  import polars as pl
  from crv.viz import theme, timeseries, save

  theme.enable("crv_light")
  df = pl.DataFrame({
      "t":[0,0,1,1,2,2],
      "o":[0,1,0,1,0,1],
      "s_io":[0.1,0.2,0.3,0.2,0.5,0.4],
  })
  ch = timeseries.plot_endowment(df, by_object=True)
  save.save(ch, out_html="out/endowment.html")
  ```

Troubleshooting

- Image export error about vl-convert-python
  - Install vl-convert-python>=1.6.0 to enable PNG/SVG/PDF; HTML export works without it
- Missing columns
  - Ensure Parquet/table contains the expected columns; use base.validate_schema for checks
- Theme not applying
  - Call theme.enable(...) before building charts and ensure the process hasn’t reset Altair configs

License

- MIT (see repository LICENSE)
