from __future__ import annotations

import polars as pl

# Silence known third-party deprecation warnings emitted during EDSL import,
# and set JUPYTER_PLATFORM_DIRS to prevent jupyter_core from warning.
# os.environ.setdefault("JUPYTER_PLATFORM_DIRS", "1")
# warnings.filterwarnings("ignore", category=DeprecationWarning, module="jupyter_core.*")
# warnings.filterwarnings("ignore", category=DeprecationWarning, module="jupyter_client.*")
from edsl import Agent, AgentList, Model, ModelList, QuestionLinearScale, ScenarioList

__all__ = [
    "SURVEY_ID",
    "build_question",
    "build_scenarios",
    "build_agents",
    "build_models",
]

# TODO: version from git tag or something dynamic
SURVEY_ID: str = "crv_one_agent_valuation_v0.1.0"


def build_question() -> QuestionLinearScale:
    """Construct the Likert 1–7 valuation question.

    Returns:
        QuestionLinearScale: Structured Likert question named 'q_rate_token_value'.
    """
    return QuestionLinearScale(
        "q_rate_token_value",
        "Rate the expected value of token '{{ ctx_token_kind }}' for the focal agent "
        "on a 1–7 scale given: ownership={{ ctx_owner_status }}, "
        "peer alignment={{ ctx_peer_alignment }}. Return only the number.",
        list(range(1, 8)),
    )


def build_scenarios(df: pl.DataFrame) -> ScenarioList:
    """Convert a Polars DataFrame with ctx_* columns to an EDSL ScenarioList.

    The DataFrame must contain columns:
      - ctx_token_kind: str
      - ctx_owner_status: str
      - ctx_peer_alignment: str

    Args:
        df: Polars DataFrame with required ctx_* columns.

    Returns:
        ScenarioList: EDSL scenario list constructed from rows.

    Raises:
        ValueError: If required columns are missing.
    """
    required = {"ctx_token_kind", "ctx_owner_status", "ctx_peer_alignment"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required scenario columns: {sorted(missing)}")

    # edsl.ScenarioList accepts list[dict]
    rows = [
        {
            "ctx_token_kind": str(r["ctx_token_kind"]),
            "ctx_owner_status": str(r["ctx_owner_status"]),
            "ctx_peer_alignment": str(r["ctx_peer_alignment"]),
        }
        for r in df.iter_rows(named=True)
    ]
    return ScenarioList.from_list("ctx", rows)


def build_agents(personas: list[str]) -> AgentList:
    """Build an AgentList from persona names.

    Args:
        personas: List of persona identifiers.

    Returns:
        AgentList: EDSL AgentList where each Agent has a persona name.
    """
    # Provide persona via Agent traits for EDSL
    agents = [Agent(traits={"persona": p}) for p in personas]
    return AgentList(agents)


def build_models(models: list[str]) -> ModelList:
    """Build a ModelList from model slugs.

    Args:
        models: List of model slugs (e.g., 'gpt-4o').

    Returns:
        ModelList: EDSL ModelList where each Model references a model slug.
    """
    models_list = [Model(m) for m in models]
    return ModelList(models_list)
