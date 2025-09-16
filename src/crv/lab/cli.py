from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import polars as pl

from .policy_builder import (
    PolicyBuildConfig,
    aggregate_policy,
    load_scenarios,
    run_edsl,
    run_mock,
    tidy_results,
    write_manifest,
    write_policy,
)
from .survey import SURVEY_ID


def _print_head(path: Path, n: int = 5) -> None:
    """Print the first n rows of a Parquet file via Polars.

    Args:
        path: Path to parquet file.
        n: Number of rows to print.
    """
    df = pl.read_parquet(path)
    print(df.head(n))


def _load_env_file(env_path: Path = Path(".env"), *, echo: bool = True) -> None:
    """Lightweight .env loader (no external deps). Does not override existing env vars.

    Args:
        env_path: Path to .env file at repo root by default.
        echo: If True, logs which keys were loaded (masked).
    """
    try:
        text = env_path.read_text()
    except FileNotFoundError:
        if echo:
            print(f"[INFO] No .env found at {env_path.resolve()} (skipping)")
        return
    loaded = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and (k not in os.environ or os.environ[k] == ""):
            os.environ[k] = v
            loaded.append(k)
    if echo and loaded:
        masked = []
        for k in loaded:
            val = os.environ.get(k, "")
            if len(val) >= 8:
                masked.append(f"{k}=***{val[-4:]}")
            elif val:
                masked.append(f"{k}=***")
            else:
                masked.append(f"{k}=<empty>")
        print("[INFO] Loaded env keys: " + ", ".join(masked))


def _needs_openai_key(model_slug: str) -> bool:
    """Heuristic: models containing 'gpt-' use OpenAI and require OPENAI_API_KEY."""
    return "gpt-" in model_slug


def _cmd_build_policy(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="build-policy",
        description="Build CRV valuation policy (EDSL or --mock) and write Parquet + manifest.",
    )
    p.add_argument("--scenarios", type=str, default="", help="Path to scenarios parquet.")
    p.add_argument("--persona", type=str, default="persona_baseline", help="Persona identifier.")
    p.add_argument("--model", dest="model_slug", type=str, default="gpt-4o", help="Model slug.")
    p.add_argument("--mock", action="store_true", help="Use mock path (no API keys required).")
    p.add_argument("--seed", type=int, default=123, help="Random seed for mock hashing.")
    p.add_argument(
        "--out-dir",
        type=str,
        default="out/demo",
        help="Output directory (policy_*.parquet, manifest_*.json).",
    )
    p.add_argument(
        "--no-env",
        action="store_true",
        help="Do not auto-load .env (by default, .env is loaded if present).",
    )
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    scenarios_path = Path(args.scenarios) if args.scenarios else Path("")

    # Load .env for provider keys unless explicitly disabled
    if not args.no_env:
        _load_env_file(Path(".env"), echo=True)
    cfg = PolicyBuildConfig(
        scenarios_path=scenarios_path,
        personas=[args.persona],
        models=[args.model_slug],
        out_dir=out_dir,
        seed=args.seed,
        survey_id=SURVEY_ID,
    )
    # Initialize to satisfy static analyzers; populated on real EDSL branch
    edsl_error: str | None = None

    scenarios_df = load_scenarios(cfg.scenarios_path)
    if args.mock:
        raw = run_mock(cfg, scenarios_df)
        mode = "mock"
        edsl_version: str | None = None
    else:
        # Validate provider keys for selected model(s)
        if any(_needs_openai_key(m) for m in cfg.models):
            if not os.environ.get("OPENAI_API_KEY"):
                raise SystemExit(
                    "Missing OPENAI_API_KEY for real EDSL run with OpenAI model(s). "
                    "Set it in your shell or .env, or run with --mock."
                )
            else:
                key_tail = (
                    os.environ["OPENAI_API_KEY"][-4:]
                    if len(os.environ["OPENAI_API_KEY"]) >= 4
                    else "****"
                )
                print(f"[INFO] Using OpenAI provider key: ***{key_tail}")
        print(f"[INFO] Starting real EDSL run for personas={cfg.personas}, models={cfg.models}")
        edsl_error: str | None = None
        # lazy import to introspect version if available
        try:
            import edsl  # type: ignore

            edsl_version = getattr(edsl, "__version__", "unknown")
        except Exception:
            edsl_version = "unknown"
        try:
            raw = run_edsl(cfg, scenarios_df)
            mode = "edsl"
        except Exception as e:
            edsl_error = str(e)
            print(
                f"[WARN] EDSL run failed or returned empty; falling back to --mock. Reason: {edsl_error}"
            )
            raw = run_mock(cfg, scenarios_df)
            mode = "edsl_fallback"

    tidy = tidy_results(raw)
    policy = aggregate_policy(tidy)
    policy_path = write_policy(policy, out_dir)

    meta: dict[str, Any] = {
        "survey_id": cfg.survey_id,
        "seed": cfg.seed,
        "mode": mode,
        "edsl_version": edsl_version or "mock",
        "rows_raw": int(tidy.height),
        "rows_policy": int(policy.height),
        "out_dir": str(out_dir),
        "policy_path": str(policy_path),
    }
    # annotate fallback/errors when applicable
    if not args.mock:
        meta["edsl_fallback"] = mode == "edsl_fallback"
        if mode == "edsl_fallback":
            meta["edsl_error"] = (edsl_error or "")[:500]
    manifest_path = write_manifest(meta, out_dir)

    print(f"[INFO] Wrote policy to {policy_path}")
    print(f"[INFO] Wrote manifest to {manifest_path}")
    _print_head(policy_path, n=5)
    return 0


def _cmd_show_policy(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="show-policy", description="Show a policy parquet head.")
    p.add_argument("--policy", type=str, required=True, help="Path to policy parquet.")
    p.add_argument("--n", type=int, default=5, help="Rows to display.")
    args = p.parse_args(argv)

    _print_head(Path(args.policy), n=args.n)
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ai_agents", description="AI agents policy utilities CLI.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build-policy")
    sub.add_parser("show-policy")
    return p


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        build_argparser().print_help()
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "build-policy":
        code = _cmd_build_policy(rest)
    elif cmd == "show-policy":
        code = _cmd_show_policy(rest)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        code = 2
    raise SystemExit(code)


if __name__ == "__main__":
    main()
