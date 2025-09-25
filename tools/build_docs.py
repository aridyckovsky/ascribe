import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Guard: ensure docs are built via the canonical wrapper to prepare env (Node, uv, PYTHONPATH, DSPy flags)
if os.getenv("ASCRIBE_DOCS_VIA_WRAPPER") != "1":
    sys.exit(
        "Docs must be built via tools/generate_docs.sh.\n"
        "Run: bash tools/generate_docs.sh\n"
        "This ensures Node deps, uv sync, PYTHONPATH, and DSPy flags are set."
    )

import mkdocs_gen_files
import yaml
from dotenv import load_dotenv

from tools.docs_llms import build_llms_txt

ROOT = Path(__file__).resolve().parents[1]

# Load variables from a local .env file for development.
# In CI, GitHub Actions provides env directly.
load_dotenv()

# ---------------------------
# Stability metadata handling
# ---------------------------

STABILITY_VALUES = {"stable", "experimental", "unstable"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_stability_map(
    path: Path = Path("docs/metadata/stability.yml"),
) -> dict[str, dict[str, str]]:
    """
    Load stability metadata and return a flat map keyed by import_path.
    Each value is a dict with keys: status, note?, since?
    The function is forgiving: malformed entries are ignored.
    """
    try:
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        result: dict[str, dict[str, str]] = {}

        def handle_list(items: list[dict] | None) -> None:
            if not items:
                return
            for rec in items:
                if not isinstance(rec, dict):
                    continue
                import_path = rec.get("import_path")
                status = rec.get("status")
                if not import_path or status not in STABILITY_VALUES:
                    # Skip invalid records silently to avoid breaking strict docs build.
                    continue
                note = rec.get("note")
                since = rec.get("since")
                if since and not (SEMVER_RE.match(since) or ISO_DATE_RE.match(since)):
                    # Ignore invalid since field
                    since = None
                result[import_path] = {"status": status, "note": note, "since": since}

        handle_list(data.get("packages"))
        handle_list(data.get("modules"))
        return result
    except Exception:
        # Do not break docs build if YAML is malformed; act as if no stability data provided.
        return {}


def _stability_admonition(rec: dict[str, str]) -> str:
    """
    Render a Material admonition block for a stability record.
    - stable -> note "Stable API"
    - experimental -> warning "Experimental API"
    - unstable -> danger "Unstable API"
    """
    status = rec.get("status")
    if not status:
        return ""
    kind = {"stable": "note", "experimental": "warning", "unstable": "danger"}[status]
    title = {
        "stable": "Stable API",
        "experimental": "Experimental API",
        "unstable": "Unstable API",
    }[status]
    parts: list[str] = []
    if rec.get("note"):
        parts.append(str(rec["note"]).strip())
    if rec.get("since"):
        parts.append(f"Since: {rec['since']}.")
    body = " ".join(p for p in parts if p).strip()
    out = f'!!! {kind} "{title}"\n'
    if body:
        out += f"    {body}\n"
    return out


def emit_package_page(
    package_import_path: str, doc_path: Path, stability: dict[str, dict[str, str]]
) -> None:
    """
    Emit a package index page that:
    - Shows heading with import path
    - Injects stability admonition if configured
    - Uses mkdocstrings directive with filters to suppress members (package overview only)
    """
    with mkdocs_gen_files.open(doc_path, "w") as f:
        f.write(f"# {package_import_path}\n\n")
        rec = stability.get(package_import_path, {"status": "experimental"})
        if rec:
            f.write(_stability_admonition(rec) + "\n")
        f.write(
            f"::: {package_import_path}\n"
            f"    options:\n"
            f"      show_submodules: false\n"
            f"      members_order: source\n"
            f"      show_source: false\n"
            f"      show_docstring: true\n"
            f"      show_if_no_docstring: true\n"
            f"      filters:\n"
            f"        - '!.*'\n"
        )


def emit_module_page(
    import_path: str, doc_path: Path, stability: dict[str, dict[str, str]]
) -> None:
    """
    Emit a module page that:
    - Shows heading with import path
    - Injects stability admonition if configured
    - Uses mkdocstrings module directive
    """
    with mkdocs_gen_files.open(doc_path, "w") as f:
        f.write(f"# {import_path}\n\n")
        rec = stability.get(import_path, {"status": "experimental"})
        if rec:
            f.write(_stability_admonition(rec) + "\n")
        f.write(f"::: {import_path}\n    options:\n      show_if_no_docstring: true\n")


def build_api_landing(
    packages: dict[str, str],
    modules_by_package: dict[str, list[tuple[str, str]]],
) -> None:
    """
    Generate docs/api/index.md with an overview and links to top-level packages.
    """
    # Short descriptions for top-level packages (research-oriented tone; succinct)
    DESCRIPTIONS: dict[str, str] = {
        "crv.core": "Core data structures, grammar, and typed contracts that define the CRV/CIRVA loop and artifacts.",
        "crv.io": "IO and manifest paths for deterministic, Arrow-friendly artifacts; emphasizes replayability and audit.",
        "crv.lab": "Lab utilities to elicit persona-specific valuation policies and run controlled sweeps.",
        "crv.mind": "Mind orchestration and policy interfaces mediating valuation and decision pipelines.",
        "crv.viz": "Visualization hooks and dashboards to explore runs, identity graphs, and KPIs.",
        "crv.world": "World rules, events, and visibility channels that drive the CRV/CIRVA step function.",
    }

    landing_path = Path("api") / "index.md"
    with mkdocs_gen_files.open(landing_path, "w") as f:
        f.write("# API Reference\n\n")
        f.write(
            "This reference is organized by packages. Start from a package overview, then follow links\n"
            "to canonical module pages. Stability annotations at the top of each page communicate\n"
            "whether an interface is stable, experimental, or unstable.\n\n"
        )

        for pkg in sorted(
            (p for p in packages.keys() if p.count(".") == 1),  # only top-level like crv.core
            key=lambda s: s,
        ):
            doc = packages.get(pkg)
            if not doc:
                continue
            desc = DESCRIPTIONS.get(pkg, "")
            f.write(f"## `{pkg}`\n\n")
            rel_doc = Path(doc).relative_to("api").as_posix()
            f.write(f"[Package overview]({rel_doc}). {desc}\n\n")

            # Optionally list a few modules for orientation (short labels only)
            mods = sorted(modules_by_package.get(pkg, []))
            if mods:
                f.write("Modules (selection):\n\n")
                # List up to 6 modules to avoid clutter
                for mod_import, mod_doc in mods[:6]:
                    short = mod_import.split(".")[-1]
                    rel_mod = Path(mod_doc).relative_to("api").as_posix()
                    f.write(f"- [{short}]({rel_mod})\n")
                f.write("\n")

    # Set edit path for landing page to the generator to make provenance clear
    mkdocs_gen_files.set_edit_path(landing_path, "tools/build_docs.py")


# ---------------------------
# 1) Grammar (EBNF) and diagrams
# ---------------------------

p = Path("src/crv/core/core.ebnf")
ebnf = p.read_text(encoding="utf-8")

# 1) EBNF.md
ebnf_md = Path("grammar/ebnf.md")
with mkdocs_gen_files.open(ebnf_md, "w") as f:
    f.write("# CRV Core Grammar (EBNF)\n\n")
    f.write("```ebnf\n")
    f.write(ebnf.rstrip() + "\n")
    f.write("```\n")
mkdocs_gen_files.set_edit_path(ebnf_md, "src/crv/core/core.ebnf")

# 1a) Grammar diagrams (HTML) via gen-files (always generated to virtual docs)
try:
    with tempfile.TemporaryDirectory() as td:
        out_html = Path(td) / "diagrams.html"
        subprocess.run(
            [
                "npx",
                "ebnf2railroad",
                "-t",
                "CRV Core Grammar Diagrams",
                str((ROOT / p).resolve()),
                "-o",
                str(out_html),
            ],
            check=True,
            cwd=(ROOT / "tools" / "ebnf"),
        )
        html = out_html.read_text(encoding="utf-8")
    with mkdocs_gen_files.open("grammar/diagrams.html", "w") as f:
        f.write(html)
except Exception:
    with mkdocs_gen_files.open("grammar/diagrams.html", "w") as f:
        f.write(
            "<h1>CRV Core Grammar Diagrams</h1><p>Diagram generation unavailable during build.</p>"
        )

# ---------------------------
# 1b) Project and package READMEs surfaced in docs
# ---------------------------

core_readme = ROOT / "src" / "crv" / "core" / "README.md"
if core_readme.exists():
    target_core_readme = Path("guide/core.md")
    with mkdocs_gen_files.open(target_core_readme, "w") as f:
        f.write(core_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_core_readme, "src/crv/core/README.md")

# Surface IO README in docs (if present)
io_readme = ROOT / "src" / "crv" / "io" / "README.md"
if io_readme.exists():
    target_io_readme = Path("guide/io.md")
    with mkdocs_gen_files.open(target_io_readme, "w") as f:
        f.write(io_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_io_readme, "src/crv/io/README.md")

# Surface Lab README in docs (if present)
lab_readme = ROOT / "src" / "crv" / "lab" / "README.md"
if lab_readme.exists():
    target_lab_readme = Path("guide/lab.md")
    with mkdocs_gen_files.open(target_lab_readme, "w") as f:
        f.write(lab_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_lab_readme, "src/crv/lab/README.md")

# Surface Viz README in docs (if present)
viz_readme = ROOT / "src" / "crv" / "viz" / "README.md"
if viz_readme.exists():
    target_viz_readme = Path("guide/viz.md")
    with mkdocs_gen_files.open(target_viz_readme, "w") as f:
        f.write(viz_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_viz_readme, "src/crv/viz/README.md")

# Surface Mind README in docs (if present)
mind_readme = ROOT / "src" / "crv" / "mind" / "README.md"
if mind_readme.exists():
    target_mind_readme = Path("guide/mind.md")
    with mkdocs_gen_files.open(target_mind_readme, "w") as f:
        f.write(mind_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_mind_readme, "src/crv/mind/README.md")

# Surface World README in docs (if present)
world_readme = ROOT / "src" / "crv" / "world" / "README.md"
if world_readme.exists():
    target_world_readme = Path("guide/world.md")
    with mkdocs_gen_files.open(target_world_readme, "w") as f:
        f.write(world_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_world_readme, "src/crv/world/README.md")

pyproject = ROOT / "pyproject.toml"
if pyproject.exists():
    pyproject_doc = Path("pyproject.toml")
    with mkdocs_gen_files.open(pyproject_doc, "w") as f:
        f.write(pyproject.read_text(encoding="utf-8"))

# ---------------------------
# 2) Navigation + API Reference (per-package + per-module pages)
# ---------------------------

# Stability metadata (optional)
STABILITY = load_stability_map()

PACKAGES = ["core", "io", "lab", "mind", "viz", "world"]

# Build literate-nav SUMMARY.md manually for broad compatibility
# Collect per-module API pages while generating them, then write a nested bullet list.
api_entries: dict[str, list[tuple[str, str]]] = {pkg: [] for pkg in PACKAGES}
# Map of discovered package import path -> generated doc path (api/.../index.md)
package_entries: dict[str, str] = {}

# Generate package and module pages
for pkg in PACKAGES:
    pkg_dir = ROOT / "src" / "crv" / pkg
    if not pkg_dir.exists():
        continue

    # Package pages for every discovered package (directories with __init__.py).
    # These pages will be used in the nav; module pages are still generated (below) but not listed.
    for init_file in sorted(pkg_dir.rglob("__init__.py")):
        rel_from_src = init_file.relative_to(ROOT / "src")  # e.g., crv/core/tables/__init__.py
        package_import_path = ".".join(rel_from_src.parts[:-1])  # e.g., crv.core.tables
        doc_path = Path("api") / rel_from_src.parent / "index.md"

        emit_package_page(package_import_path, doc_path, STABILITY)
        mkdocs_gen_files.set_edit_path(doc_path, rel_from_src.parent.as_posix())
        package_entries[package_import_path] = doc_path.as_posix()

    # Module pages
    for py_file in sorted(pkg_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue

        rel_from_src = py_file.relative_to(ROOT / "src")  # e.g., crv/io/read.py
        import_path = ".".join(rel_from_src.with_suffix("").parts)  # e.g., crv.io.read

        # Destination doc path under api/
        doc_path = Path("api") / rel_from_src.with_suffix(".md")

        emit_module_page(import_path, doc_path, STABILITY)
        mkdocs_gen_files.set_edit_path(doc_path, rel_from_src.as_posix())

        # Record for building nav grouping later; store by top-level bucket (core, io, ...)
        top = rel_from_src.parts[1] if len(rel_from_src.parts) > 1 else ""
        if top in api_entries:
            api_entries[top].append((import_path, doc_path.as_posix()))

# Generate placeholder pages for referenced-but-missing targets (keep docstrings visible without broken links)
PLACEHOLDER_TARGETS: dict[str, list[str]] = {
    "lab": [
        "audit",
        "cli",
        "io_helpers",
        "modelspec",
        "personas",
        "policy",
        "policy_builder",
        "probes",
        "scenarios",
        "survey",
        "surveys",
        "tasks",
    ],
    "mind": [
        "cache",
        "compile",
        "eval",
        "oracle_types",
        "oracle",
        "programs",
        "react_controller",
        "signatures",
    ],
    "viz": [
        "base",
        "dashboards",
        "distributions",
        "events",
        "identity",
        "layers",
        "networks",
        "save",
        "theme",
        "timeseries",
    ],
    "world": [
        "agents",
        "config",
        "data",
        "mesa_data",
        "model",
        "observation_rules",
        "sim",
        "sweep",
    ],
}

for pkg_key, names in PLACEHOLDER_TARGETS.items():
    base = Path("api") / "crv" / pkg_key
    for name in names:
        target = base / f"{name}.md"
        # If a real module page was generated, leave it; otherwise create a placeholder so links don't break strict builds.
        if not target.exists():
            with mkdocs_gen_files.open(target, "w") as f:
                f.write(f"# crv.{pkg_key}.{name}\n\n")
                f.write('!!! note "Placeholder"\n')
                f.write(
                    "    This page is a placeholder for future documentation. "
                    "It is intentionally included to avoid broken links in strict builds. "
                    "Content will be added when the corresponding module/docs are finalized.\n"
                )

# Compose literate-nav as nested bullets
summary_lines: list[str] = []


def add(line: str, level: int = 0) -> None:
    summary_lines.append(("    " * level) + f"* {line}\n")


# Overview
add("[Overview](index.md)")

# Guide
add("Guide")
add("[Getting Started](guide/getting-started.md)", 1)
add("[Concepts](guide/concepts.md)", 1)
add("[Artifacts](guide/artifacts.md)", 1)
add("[CLI](guide/cli.md)", 1)
add("[Workflows](guide/workflows.md)", 1)
add("[App](guide/app.md)", 1)
add("[FAQ](guide/faq.md)", 1)
# Modules area
add("Modules", 1)
add("[Core](guide/core.md)", 2)
add("[Grammar (EBNF)](grammar/ebnf.md)", 2)
add("[Grammar Diagrams](grammar/diagrams.html)", 2)

# Package guides (from READMEs) if present, listed under Modules
if (ROOT / "src" / "crv" / "io" / "README.md").exists():
    add("[IO](guide/io.md)", 2)
if (ROOT / "src" / "crv" / "lab" / "README.md").exists():
    add("[Lab](guide/lab.md)", 2)
if (ROOT / "src" / "crv" / "mind" / "README.md").exists():
    add("[Mind](guide/mind.md)", 2)
if (ROOT / "src" / "crv" / "world" / "README.md").exists():
    add("[World](guide/world.md)", 2)
if (ROOT / "src" / "crv" / "viz" / "README.md").exists():
    add("[Viz](guide/viz.md)", 2)

# API Reference (packages with modules listed under the nearest package)
add("API Reference")
# Insert API landing "Overview" at the top of the API section
add("[Overview](api/index.md)", 1)


def _short_label(path: str) -> str:
    return path.split(".")[-1]


# Prepare a mapping from package import path -> list of its module pages
modules_by_package: dict[str, list[tuple[str, str]]] = {k: [] for k in package_entries.keys()}

# Sort packages by descending length to match the nearest (longest) prefix
sorted_packages = sorted(package_entries.keys(), key=len, reverse=True)

# Assign each module to its nearest package (longest matching prefix)
for _, entries in api_entries.items():
    for mod_import_path, mod_doc_path in entries:
        # Skip if this module is itself a package page (__init__.py was handled above)
        if mod_import_path in package_entries:
            continue
        target_pkg = None
        for pkg_path in sorted_packages:
            # Ensure exact dot-boundary prefix match
            if mod_import_path == pkg_path or mod_import_path.startswith(pkg_path + "."):
                target_pkg = pkg_path
                break
        if target_pkg is None:
            # Fallback: attach to top-level 'crv' if nothing matches (shouldn't happen given PACKAGES)
            continue
        modules_by_package[target_pkg].append((mod_import_path, mod_doc_path))

# Emit packages and their modules with clean labels and hierarchical indentation
TOP_LEVEL_PACKAGES = {"crv.core", "crv.io", "crv.world", "crv.lab", "crv.mind", "crv.viz"}

for pkg_path in sorted(package_entries.keys()):
    pkg_doc = package_entries[pkg_path]  # always link to api/<package>/index.md
    pkg_level = max(1, pkg_path.count("."))  # 'crv.core' -> 1, 'crv.core.tables' -> 2

    # Labels: top-level keep full path; subpackages use last segment only
    pkg_label = pkg_path if pkg_path in TOP_LEVEL_PACKAGES else _short_label(pkg_path)

    # Emit plain section header (not a link)
    add(f"{pkg_label}", pkg_level)

    # First child: same label linking to the package index (promotes header to link target)
    add(f"[{pkg_label}]({pkg_doc})", pkg_level + 1)

    # List modules with short labels; avoid duplicate same-name link directly under header
    for mod_import_path, mod_doc_path in sorted(modules_by_package.get(pkg_path, [])):
        mod_label = _short_label(mod_import_path)
        if mod_label == pkg_label:
            continue  # prevent duplicate same-name entry under header
        add(f"[{mod_label}]({mod_doc_path})", pkg_level + 1)

# Emit SUMMARY.md
with mkdocs_gen_files.open("SUMMARY.md", "w") as f:
    f.writelines(summary_lines)

# Build API landing after package/module pages are known
build_api_landing(packages=package_entries, modules_by_package=modules_by_package)

# ---------------------------
# 3) llms.txt via DSPy helper (fallback handled within build_llms_txt)
# ---------------------------

# Allow override of base URL via env (default: DOCS_BASE_URL=https://docs.ascribe.live)
txt = build_llms_txt(site_name="Ascribe Documentation", base_url=os.getenv("DOCS_BASE_URL"))
with mkdocs_gen_files.open("llms.txt", "w") as f:
    f.write(txt)
