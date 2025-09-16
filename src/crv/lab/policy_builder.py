from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

# Silence known third-party deprecation warnings emitted during EDSL import,
# and set JUPYTER_PLATFORM_DIRS to prevent jupyter_core from warning.
# os.environ.setdefault("JUPYTER_PLATFORM_DIRS", "1")
# warnings.filterwarnings("ignore", category=DeprecationWarning, module="jupyter_core.*")
# warnings.filterwarnings("ignore", category=DeprecationWarning, module="jupyter_client.*")
# warnings.filterwarnings("ignore", category=DeprecationWarning, module="nbclient.*")
# warnings.filterwarnings("ignore", category=DeprecationWarning, module="nbconvert.*")
from edsl import Survey  # Import EDSL at module level (no in-function imports)

# Local survey builders (EDSL wrappers)
from .survey import SURVEY_ID, build_agents, build_models, build_question, build_scenarios


@dataclass(slots=True, frozen=True)
class PolicyBuildConfig:
    """Configuration for building a valuation policy.

    Attributes:
        scenarios_path: Path to scenarios parquet. If missing, a tiny demo grid is synthesized.
        personas: List of persona identifiers.
        models: List of model slugs (metadata only in --mock).
        out_dir: Output directory where policy and manifest are written.
        survey_id: Stable survey identifier (bump when prompt/schema changes).
        seed: Integer random seed used for mock hashing and reproducibility.
    """

    scenarios_path: Path
    personas: list[str]
    models: list[str]
    out_dir: Path
    survey_id: str = SURVEY_ID
    seed: int = 123


def _ensure_out_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_scenarios(path: Path) -> pl.DataFrame:
    """Load scenarios from Parquet or synthesize a tiny demo grid if missing.

    The schema contains:
      - ctx_token_kind: str
      - ctx_owner_status: str
      - ctx_peer_alignment: str

    Args:
        path: Path to a parquet file. If not found, a synthetic grid with 3–6 rows is generated.

    Returns:
        Polars DataFrame with the required ctx_* columns.
    """
    # Only treat as a file if it's a non-empty path to a parquet file.
    pstr = str(path)
    is_valid_file = (
        bool(pstr)
        and path.exists()
        and path.is_file()
        and path.suffix.lower()
        in (
            ".parquet",
            ".parq",
        )
    )
    if is_valid_file:
        df = pl.read_parquet(pstr)
        required = {"ctx_token_kind", "ctx_owner_status", "ctx_peer_alignment"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in scenarios parquet: {sorted(missing)}")
        return df.select(
            pl.col("ctx_token_kind").cast(pl.String),
            pl.col("ctx_owner_status").cast(pl.String),
            pl.col("ctx_peer_alignment").cast(pl.String),
        )

    # Synthesize a compact demo grid (3–6 rows)
    token_kinds = ["Alpha", "Beta"]
    owner = ["owned", "not_owned"]
    peer = ["aligned", "neutral", "misaligned"]
    rows: list[dict[str, str]] = []
    # Keep to 6 rows: two token kinds × three peer states; fix owner to both for kind Alpha, one for Beta
    rows.extend(
        {"ctx_token_kind": "Alpha", "ctx_owner_status": o, "ctx_peer_alignment": p}
        for o in owner
        for p in peer[:2]
    )
    rows.extend(
        {"ctx_token_kind": "Beta", "ctx_owner_status": "not_owned", "ctx_peer_alignment": p}
        for p in peer
    )
    return pl.DataFrame(
        rows,
        schema={
            "ctx_token_kind": pl.String,
            "ctx_owner_status": pl.String,
            "ctx_peer_alignment": pl.String,
        },
    )


def _seeded_hash_int(s: str, seed: int) -> int:
    raw = f"{seed}|{s}".encode()
    h = hashlib.sha256(raw).hexdigest()
    # Map to 1..7 inclusive
    return (int(h[:8], 16) % 7) + 1


def run_mock(cfg: PolicyBuildConfig, scenarios_df: pl.DataFrame) -> pl.DataFrame:
    """Produce deterministic Likert answers via seeded hashes over scenario×persona×model.

    Args:
        cfg: Policy build configuration.
        scenarios_df: Scenario grid with ctx_* columns.

    Returns:
        Polars DataFrame with columns: ctx_*, persona, model, question, answer (int 1..7).
    """
    qname = "q_rate_token_value"
    rows: list[dict[str, Any]] = []
    for r in scenarios_df.iter_rows(named=True):
        ctx = (str(r["ctx_token_kind"]), str(r["ctx_owner_status"]), str(r["ctx_peer_alignment"]))
        for persona in cfg.personas:
            for model in cfg.models:
                key = f"{ctx[0]}|{ctx[1]}|{ctx[2]}|{persona}|{model}"
                ans = _seeded_hash_int(key, cfg.seed)
                rows.append(
                    {
                        "ctx_token_kind": ctx[0],
                        "ctx_owner_status": ctx[1],
                        "ctx_peer_alignment": ctx[2],
                        "persona": persona,
                        "model": model,
                        "question": qname,
                        "answer": int(ans),
                    }
                )
    return pl.DataFrame(rows)


def run_edsl(cfg: PolicyBuildConfig, scenarios_df: pl.DataFrame) -> pl.DataFrame:
    """Execute the EDSL Survey and collect raw results into a tidy-compatible frame.

    This function relies on edsl.Survey().by(...).run() producing a dataframe
    convertible to pandas. We introspect columns and map into the tidy schema.

    Args:
        cfg: Policy build configuration.
        scenarios_df: Scenario grid with ctx_* columns.

    Returns:
        Polars DataFrame with columns: ctx_*, persona, model, question, answer.
    """
    # EDSL Survey imported at module level

    scen = build_scenarios(scenarios_df)
    agents = build_agents(cfg.personas)
    models = build_models(cfg.models)
    question = build_question()

    # Build Survey with questions list; then attach scenarios, agents, and models
    survey = Survey(questions=[question])
    jobs = survey.by(scen).by(agents).by(models)
    # Expected Parrot API typically returns a pandas.DataFrame via .run().to_pandas()
    res = jobs.run()  # type: ignore[attr-defined]
    if hasattr(res, "to_pandas"):
        pdf = res.to_pandas()  # type: ignore[no-untyped-call]
    else:
        # Some versions may return a dataframe-like already usable with pandas interface
        pdf = res  # type: ignore[assignment]

    df = pl.from_pandas(pdf)  # type: ignore[arg-type]

    # Introspect probable column names
    # Common variants: 'question_name' or 'question', 'answer' or 'response',
    # persona: 'agent'/'persona'/'agent_name'/'agent.persona', model: 'model'/'model_name'/'model.model'
    col_map: dict[str, str] = {}
    # question
    for c in ["question", "question_name", "q_name"]:
        if c in df.columns:
            col_map["question"] = c
            break
    # answer
    for c in ["answer", "response", "value"]:
        if c in df.columns:
            col_map["answer"] = c
            break
    # If no direct answer column, look for 'answer.<qname>' style
    if "answer" not in col_map:
        try:
            answer_like = next(
                (c for c in df.columns if isinstance(c, str) and c.startswith("answer.")), None
            )
        except Exception:
            answer_like = None
        if answer_like:
            col_map["answer"] = answer_like  # e.g., 'answer.q_rate_token_value'
    # persona
    for c in ["persona", "agent", "agent_name", "agent.persona"]:
        if c in df.columns:
            col_map["persona"] = c
            break
    # model
    for c in ["model", "model_name", "provider_model", "model.model"]:
        if c in df.columns:
            col_map["model"] = c
            break
    # Normalize dotted column names if present
    rename_map_extra: dict[str, str] = {}
    if col_map.get("persona") == "agent.persona":
        rename_map_extra["agent.persona"] = "persona"
        col_map["persona"] = "persona"
    if col_map.get("model") == "model.model":
        rename_map_extra["model.model"] = "model"
        col_map["model"] = "model"
    if rename_map_extra:
        df = df.rename(rename_map_extra)

    # Try to extract/rename scenario context columns if missing
    # Case A: flattened columns like 'scenario.ctx_token_kind'
    rename_map = {}
    for name in ["ctx_token_kind", "ctx_owner_status", "ctx_peer_alignment"]:
        flat = f"scenario.{name}"
        if flat in df.columns and name not in df.columns:
            rename_map[flat] = name
    if rename_map:
        df = df.rename(rename_map)

    # Case B: struct-typed 'scenario' column with ctx_* fields
    schema = df.schema
    if "scenario" in df.columns and str(schema.get("scenario", "")).startswith("Struct"):
        try:
            df = df.with_columns(
                pl.col("scenario").struct.field("ctx_token_kind").alias("ctx_token_kind"),
                pl.col("scenario").struct.field("ctx_owner_status").alias("ctx_owner_status"),
                pl.col("scenario").struct.field("ctx_peer_alignment").alias("ctx_peer_alignment"),
            )
        except Exception:
            # Best-effort; if struct fields not present, continue and let required check handle it
            pass

    required_ctx = {"ctx_token_kind", "ctx_owner_status", "ctx_peer_alignment"}
    missing_ctx = required_ctx - set(df.columns)
    if missing_ctx:
        raise ValueError(f"EDSL results missing ctx columns: {sorted(missing_ctx)}")

    # Build normalized dataframe
    out = pl.DataFrame(
        {
            "ctx_token_kind": df["ctx_token_kind"].cast(pl.String),
            "ctx_owner_status": df["ctx_owner_status"].cast(pl.String),
            "ctx_peer_alignment": df["ctx_peer_alignment"].cast(pl.String),
            "persona": df[col_map.get("persona", "persona")].cast(pl.String)
            if "persona" in col_map or "persona" in df.columns
            else pl.lit("persona_baseline", dtype=pl.String),
            "model": df[col_map.get("model", "model")].cast(pl.String)
            if "model" in col_map or "model" in df.columns
            else pl.lit("gpt-4o", dtype=pl.String),
            "question": df[col_map.get("question", "question")].cast(pl.String)
            if "question" in col_map or "question" in df.columns
            else pl.lit("q_rate_token_value", dtype=pl.String),
            "answer": df[col_map.get("answer", "answer")].cast(pl.Int64)
            if "answer" in col_map or "answer" in df.columns
            else pl.lit(0, dtype=pl.Int64),
        }
    )
    return out


def tidy_results(raw_df: pl.DataFrame) -> pl.DataFrame:
    """Normalize raw results to tidy schema.

    Ensures columns:
      - ctx_token_kind, ctx_owner_status, ctx_peer_alignment (str)
      - persona, model, question (str)
      - answer (int)
    """
    return raw_df.select(
        pl.col("ctx_token_kind").cast(pl.String),
        pl.col("ctx_owner_status").cast(pl.String),
        pl.col("ctx_peer_alignment").cast(pl.String),
        pl.col("persona").cast(pl.String),
        pl.col("model").cast(pl.String),
        pl.col("question").cast(pl.String),
        pl.col("answer").cast(pl.Int64),
    )


def aggregate_policy(tidy_df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate tidy answers into policy with mean, sd, and count.

    Groups by ctx_* + persona + model.

    Returns:
        Polars DataFrame with columns:
        ctx_token_kind, ctx_owner_status, ctx_peer_alignment, persona, model,
        value_mean: f64, value_sd: f64, n: i64
    """
    return (
        tidy_df.group_by(
            ["ctx_token_kind", "ctx_owner_status", "ctx_peer_alignment", "persona", "model"]
        )
        .agg(
            value_mean=pl.col("answer").mean().cast(pl.Float64),
            value_sd=pl.col("answer").std(ddof=1).fill_null(0.0).cast(pl.Float64),
            n=pl.len().cast(pl.Int64),
        )
        .select(
            "ctx_token_kind",
            "ctx_owner_status",
            "ctx_peer_alignment",
            "persona",
            "model",
            "value_mean",
            "value_sd",
            "n",
        )
    )


def _policy_filename(survey_id: str) -> str:
    return f"policy_{survey_id}.parquet"


def _manifest_filename(survey_id: str) -> str:
    return f"manifest_{survey_id}.json"


def write_policy(policy_df: pl.DataFrame, out_dir: Path) -> Path:
    """Write the policy parquet under out/demo/ with survey_id naming."""
    _ensure_out_dir(out_dir)
    path = out_dir / _policy_filename(SURVEY_ID)
    policy_df.write_parquet(path)
    return path


def write_manifest(meta: dict[str, Any], out_dir: Path) -> Path:
    """Write a manifest JSON with metadata for audit and reproducibility."""
    _ensure_out_dir(out_dir)
    ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    meta_out = {
        "timestamp": ts,
        **meta,
    }
    path = out_dir / _manifest_filename(SURVEY_ID)
    path.write_text(json.dumps(meta_out, indent=2))
    return path
