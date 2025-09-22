from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class PageRef:
    title: str
    # Path within the docs site (MkDocs virtual docs), e.g., "guide/getting-started.md"
    path: str


@dataclass(frozen=True)
class ExternalLink:
    title: str
    url: str


@dataclass(frozen=True)
class LLMSConfig:
    site_name: str
    base_url: str | None
    allow_patterns: list[str]
    disallow_patterns: list[str]
    notes: str | None = None


def gather_core_pages() -> list[PageRef]:
    # Curated, site-relative targets that our build already emits (no crawling).
    # Some entries are conditionally present based on surfaced READMEs; including
    # them here keeps the generator DRY and centralized.
    return [
        PageRef("Overview", "index.md"),
        PageRef("Getting Started", "guide/getting-started.md"),
        PageRef("Grammar (EBNF)", "grammar/ebnf.md"),
        PageRef("Grammar Diagrams", "grammar/diagrams.html"),
        # Package guides (conditionally included if surfaced by build_docs)
        PageRef("Core", "src/crv/core/README.md"),
        PageRef("IO", "src/crv/io/README.md"),
        PageRef("Lab", "src/crv/lab/README.md"),
        PageRef("Mind", "src/crv/mind/README.md"),
        PageRef("World", "src/crv/world/README.md"),
        PageRef("Viz", "src/crv/viz/README.md"),
        # API top sections (directories rendered by MkDocs; useful as sections)
        PageRef("API: crv.core", "api/crv/core/"),
        PageRef("API: crv.io", "api/crv/io/"),
        PageRef("API: crv.lab", "api/crv/lab/"),
        PageRef("API: crv.mind", "api/crv/mind/"),
        PageRef("API: crv.viz", "api/crv/viz/"),
        PageRef("API: crv.world", "api/crv/world/"),
    ]


def gather_external_links() -> list[ExternalLink]:
    return [
        ExternalLink("Expected Parrot EDSL", "https://docs.expectedparrot.com/"),
        ExternalLink("DSPy", "https://dspy.ai"),
        ExternalLink("Polars", "https://pola.rs"),
        ExternalLink("Mesa", "https://mesa.readthedocs.io"),
    ]


def _format_seed_url(base_url: str | None, doc_path: str) -> str:
    """
    Convert a docs path to the built site's pretty URL:
    - "*.md" -> strip extension, add trailing slash (index.md -> "/")
    - "*.html" and directory paths keep as-is
    """
    p = doc_path.strip("/")
    rel: str
    if p.endswith(".md"):
        if p == "index.md":
            rel = ""
        else:
            rel = p[:-3] + "/"
    else:
        # Keep .html or directory paths unchanged
        rel = p

    if base_url:
        return f"{base_url.rstrip('/')}/{rel}"
    return f"/{rel}"


def _bool_env(name: str, default: bool = True) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _configure_dspy_from_env() -> tuple[object | None, str | None]:
    """
    Try to import and configure DSPy from environment variables.
    Returns (dspy_module_or_None, error_message_or_None).
    """
    try:
        load_dotenv()
        import dspy  # type: ignore
    except Exception:
        return None, "dspy import failed"

    if not _bool_env("DOCS_USE_DSPY", True):
        return None, "DOCS_USE_DSPY disabled"

    model = os.getenv("DOCS_DSPY_MODEL")
    provider = (os.getenv("DOCS_DSPY_PROVIDER") or "openai").lower()

    try:
        lm = None
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not (model and api_key):
                return None, "missing OPENAI_API_KEY or DOCS_DSPY_MODEL"
            try:
                lm = dspy.OpenAI(model=model, api_key=api_key)  # type: ignore[attr-defined]
            except Exception:
                try:
                    # DSPy >=3 unified LM API
                    lm = dspy.LM(f"openai/{model}", api_key=api_key)  # type: ignore[attr-defined]
                except Exception:
                    return None, "failed to configure OpenAI LM"
        elif provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not (model and api_key):
                return None, "missing OPENROUTER_API_KEY or DOCS_DSPY_MODEL"
            try:
                if hasattr(dspy, "OpenRouter"):
                    lm = dspy.OpenRouter(model=model, api_key=api_key)  # type: ignore[attr-defined]
                else:
                    lm = dspy.LM(f"openrouter/{model}", api_key=api_key)  # type: ignore[attr-defined]
            except Exception:
                return None, "failed to configure OpenRouter LM"
        elif provider == "ollama":
            # Local inference endpoint if available
            try:
                if hasattr(dspy, "Ollama"):
                    lm = dspy.Ollama(model=model or "llama3")  # type: ignore[attr-defined]
                else:
                    lm = dspy.LM(f"ollama/{model or 'llama3'}")  # type: ignore[attr-defined]
            except Exception:
                return None, "failed to configure Ollama LM"
        else:
            return None, f"unsupported provider: {provider}"

        dspy.settings.configure(lm=lm)
        seed = os.getenv("DOCS_DSPY_SEED")
        if seed and seed.isdigit():
            try:
                import random

                random.seed(int(seed))
            except Exception:
                # Non-fatal
                pass
        return dspy, None
    except Exception as e:
        return None, str(e)


def render_llms_txt_dspy(
    cfg: LLMSConfig, pages: list[PageRef], externals: list[ExternalLink]
) -> str | None:
    """
    Attempt to synthesize llms.txt using DSPy if available. Falls back to None
    on import or runtime errors so the caller can provide a non-DSPy path.
    """
    try:
        dspy, _err = _configure_dspy_from_env()
        if not dspy:
            return None

        ds: Any = dspy

        # Prepare structured inputs for the DSPy program
        allow_lines = "\n".join(f"Allow: {pat}" for pat in (cfg.allow_patterns or []))
        disallow_lines = "\n".join(f"Disallow: {pat}" for pat in (cfg.disallow_patterns or []))
        seeds_markdown = "\n".join(
            f"- {p.title}: {_format_seed_url(cfg.base_url, p.path)}" for p in pages
        )
        references_markdown = "\n".join(f"- {e.title}: {e.url}" for e in externals)
        notes = cfg.notes or ""

        # Define signature and author module inline to avoid hard dependency at import time
        class WriteLLMSTxt(ds.Signature):  # type: ignore[name-defined]
            """
            Write a complete llms.txt for an LLM-friendly site crawl, inspired by the DSPy tutorial.

            Requirements:
            - Output plain text (no markdown code fences), suitable as llms.txt.
            - Begin with: "User-agent: *"
            - Include one line per allow/disallow, exactly prefixed with "Allow:" or "Disallow:".
            - Include a "Seeds" section as a markdown-style bullet list using the provided seeds_markdown verbatim.
            - Include an "External references" section as a bullet list using references_markdown verbatim.
            - If notes is non-empty, include a "Notes" section and include notes as plain text.
            - Do not invent URLs. Use inputs as given.
            """

            site_name: str = ds.InputField(desc="Human-readable site name.")
            base_url: str = ds.InputField(desc="Base URL (may be empty if unknown).")
            allow_lines: str = ds.InputField(desc='Lines like "Allow: /path" (may be empty).')
            disallow_lines: str = ds.InputField(desc='Lines like "Disallow: /path" (may be empty).')
            seeds_markdown: str = ds.InputField(desc='Bullet list "- Title: URL" lines.')
            references_markdown: str = ds.InputField(desc='Bullet list "- Name: URL" lines.')
            notes: str = ds.InputField(desc="Optional notes; may be empty.")
            llms_txt: str = ds.OutputField(desc="Final llms.txt content.")

        class LLMSAuthor(ds.Module):  # type: ignore[name-defined]
            def __init__(self) -> None:
                super().__init__()
                self.write = ds.Predict(WriteLLMSTxt)

            def forward(
                self,
                site_name: str,
                base_url: str,
                allow_lines: str,
                disallow_lines: str,
                seeds_markdown: str,
                references_markdown: str,
                notes: str,
            ) -> str:
                out = self.write(
                    site_name=site_name,
                    base_url=base_url or "",
                    allow_lines=allow_lines,
                    disallow_lines=disallow_lines,
                    seeds_markdown=seeds_markdown,
                    references_markdown=references_markdown,
                    notes=notes,
                )
                return out.llms_txt

        author = LLMSAuthor()
        txt = author(
            site_name=cfg.site_name,
            base_url=(cfg.base_url or ""),
            allow_lines=allow_lines,
            disallow_lines=disallow_lines,
            seeds_markdown=seeds_markdown,
            references_markdown=references_markdown,
            notes=notes,
        ).strip()

        # Normalize formatting: strip any accidental code fences and ensure newline
        if "```" in txt:
            txt = txt.replace("```", "").strip()
        if not txt.endswith("\n"):
            txt += "\n"

        return txt
    except Exception:
        return None


def render_llms_txt_fallback(
    cfg: LLMSConfig, pages: list[PageRef], externals: list[ExternalLink]
) -> str:
    lines: list[str] = []
    lines.append("# llms.txt (fallback)\n")
    lines.append("User-agent: *\n")
    if cfg.allow_patterns:
        for pat in cfg.allow_patterns:
            lines.append(f"Allow: {pat}\n")
    if cfg.disallow_patterns:
        for pat in cfg.disallow_patterns:
            lines.append(f"Disallow: {pat}\n")

    lines.append("\n# Seeds\n")
    for p in pages:
        lines.append(f"- {p.title}: {_format_seed_url(cfg.base_url, p.path)}\n")

    lines.append("\n# External references\n")
    for e in externals:
        lines.append(f"- {e.title}: {e.url}\n")

    if cfg.notes:
        lines.append(f"\n# Notes\n{cfg.notes}\n")

    return "".join(lines)


def build_llms_txt(site_name: str, base_url: str | None) -> str:
    cfg = LLMSConfig(
        site_name=site_name,
        base_url=base_url,
        allow_patterns=["/"],
        disallow_patterns=[],
        notes=("This file guides LLM crawlers. Prefer stable URLs and avoid rate limits."),
    )
    pages = gather_core_pages()
    externals = gather_external_links()
    text = render_llms_txt_dspy(cfg, pages, externals)
    if text:
        return text
    # If DSPy output is required, fail the build rather than silently falling back.
    # Set DOCS_DSPY_REQUIRED=true to enforce this in local dev or CI.
    if _bool_env("DOCS_DSPY_REQUIRED", False):
        raise RuntimeError("DSPy generation required but unavailable or failed")
    return render_llms_txt_fallback(cfg, pages, externals)


__all__ = [
    "PageRef",
    "ExternalLink",
    "LLMSConfig",
    "gather_core_pages",
    "gather_external_links",
    "render_llms_txt_dspy",
    "render_llms_txt_fallback",
    "build_llms_txt",
]
