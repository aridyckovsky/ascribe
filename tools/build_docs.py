import os
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
from dotenv import load_dotenv

from tools.docs_llms import build_llms_txt

ROOT = Path(__file__).resolve().parents[1]


# Load variables from a local .env file for development.
# In CI, GitHub Actions provides env directly.
load_dotenv()

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

# 1b) Project and package READMEs surfaced in docs

core_readme = ROOT / "src" / "crv" / "core" / "README.md"
if core_readme.exists():
    target_core_readme = Path("src/crv/core/README.md")
    with mkdocs_gen_files.open(target_core_readme, "w") as f:
        f.write(core_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_core_readme, "src/crv/core/README.md")

# Surface IO README in docs (if present)
io_readme = ROOT / "src" / "crv" / "io" / "README.md"
if io_readme.exists():
    target_io_readme = Path("src/crv/io/README.md")
    with mkdocs_gen_files.open(target_io_readme, "w") as f:
        f.write(io_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_io_readme, "src/crv/io/README.md")

# Surface Lab README in docs (if present)
lab_readme = ROOT / "src" / "crv" / "lab" / "README.md"
if lab_readme.exists():
    target_lab_readme = Path("src/crv/lab/README.md")
    with mkdocs_gen_files.open(target_lab_readme, "w") as f:
        f.write(lab_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_lab_readme, "src/crv/lab/README.md")

# Surface Viz README in docs (if present)
viz_readme = ROOT / "src" / "crv" / "viz" / "README.md"
if viz_readme.exists():
    target_viz_readme = Path("src/crv/viz/README.md")
    with mkdocs_gen_files.open(target_viz_readme, "w") as f:
        f.write(viz_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_viz_readme, "src/crv/viz/README.md")

# Surface Mind README in docs (if present)
mind_readme = ROOT / "src" / "crv" / "mind" / "README.md"
if mind_readme.exists():
    target_mind_readme = Path("src/crv/mind/README.md")
    with mkdocs_gen_files.open(target_mind_readme, "w") as f:
        f.write(mind_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_mind_readme, "src/crv/mind/README.md")

# Surface World README in docs (if present)
world_readme = ROOT / "src" / "crv" / "world" / "README.md"
if world_readme.exists():
    target_world_readme = Path("src/crv/world/README.md")
    with mkdocs_gen_files.open(target_world_readme, "w") as f:
        f.write(world_readme.read_text(encoding="utf-8"))
    mkdocs_gen_files.set_edit_path(target_world_readme, "src/crv/world/README.md")

pyproject = ROOT / "pyproject.toml"
if pyproject.exists():
    pyproject_doc = Path("pyproject.toml")
    with mkdocs_gen_files.open(pyproject_doc, "w") as f:
        f.write(pyproject.read_text(encoding="utf-8"))

# 2) Navigation + API Reference (per-module pages) via gen-files + literate-nav
PACKAGES = ["core", "io", "lab", "mind", "viz", "world"]

# Build literate-nav SUMMARY.md manually for broad compatibility
# Collect per-module API pages while generating them, then write a nested bullet list.
api_entries = {pkg: [] for pkg in PACKAGES}
# Map of discovered package import path -> generated doc path (api/.../index.md)
package_entries = {}

for pkg in PACKAGES:
    pkg_dir = ROOT / "src" / "crv" / pkg
    if not pkg_dir.exists():
        continue

    # Generate package pages for every discovered package (directories with __init__.py).
    # These pages will be used in the nav; module pages are still generated (below) but not listed.
    for init_file in sorted(pkg_dir.rglob("__init__.py")):
        rel_from_src = init_file.relative_to(ROOT / "src")  # e.g., crv/core/tables/__init__.py
        package_import_path = ".".join(rel_from_src.parts[:-1])  # e.g., crv.core.tables
        doc_path = Path("api") / rel_from_src.parent / "index.md"
        with mkdocs_gen_files.open(doc_path, "w") as f:
            f.write(
                f"# `{package_import_path}`\n\n::: {package_import_path}\n    options:\n      show_submodules: false\n      members_order: source\n      show_source: false\n      show_if_no_docstring: true\n      filters:\n        - '!.*'\n"
            )
        mkdocs_gen_files.set_edit_path(doc_path, rel_from_src.parent.as_posix())
        package_entries[package_import_path] = doc_path.as_posix()

    for py_file in sorted(pkg_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue

        rel_from_src = py_file.relative_to(ROOT / "src")  # e.g., crv/io/read.py
        import_path = ".".join(rel_from_src.with_suffix("").parts)  # e.g., crv.io.read

        # Destination doc path under api/
        doc_path = Path("api") / rel_from_src.with_suffix(".md")
        with mkdocs_gen_files.open(doc_path, "w") as f:
            f.write(f"# `{import_path}`\n\n::: {import_path}\n")
        mkdocs_gen_files.set_edit_path(doc_path, rel_from_src.as_posix())

        api_entries[pkg].append((import_path, doc_path.as_posix()))

# Compose literate-nav as nested bullets
summary_lines = []


def add(line: str, level: int = 0) -> None:
    summary_lines.append(("    " * level) + f"* {line}\n")


# Overview
add("[Overview](index.md)")

# Guide
add("Guide")
add("[Getting Started](guide/getting-started.md)", 1)
# Core area
add("Core", 1)
add("[Contracts](src/crv/core/README.md)", 2)
add("[Grammar (EBNF)](grammar/ebnf.md)", 2)
add("[Grammar Diagrams](grammar/diagrams.html)", 2)

# Other surfaced package READMEs (if present)
if (ROOT / "src" / "crv" / "io" / "README.md").exists():
    add("[IO](src/crv/io/README.md)", 1)
if (ROOT / "src" / "crv" / "lab" / "README.md").exists():
    add("[Lab](src/crv/lab/README.md)", 1)
if (ROOT / "src" / "crv" / "mind" / "README.md").exists():
    add("[Mind](src/crv/mind/README.md)", 1)
if (ROOT / "src" / "crv" / "world" / "README.md").exists():
    add("[World](src/crv/world/README.md)", 1)
if (ROOT / "src" / "crv" / "viz" / "README.md").exists():
    add("[Viz](src/crv/viz/README.md)", 1)

# API Reference (packages with modules listed under the nearest package)
add("API Reference")


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

# 3) llms.txt via DSPy helper (fallback handled within build_llms_txt)
# Allow override of base URL via env (default: DOCS_BASE_URL=https://docs.ascribe.live)
txt = build_llms_txt(site_name="Ascribe Documentation", base_url=os.getenv("DOCS_BASE_URL"))
with mkdocs_gen_files.open("llms.txt", "w") as f:
    f.write(txt)
