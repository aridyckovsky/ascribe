import os
import subprocess
import tempfile
from pathlib import Path

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

for pkg in PACKAGES:
    pkg_dir = ROOT / "src" / "crv" / pkg
    if not pkg_dir.exists():
        continue

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

# API Reference (packages → modules)
add("API Reference")
for pkg in PACKAGES:
    if not api_entries.get(pkg):
        continue
    add(f"crv.{pkg}", 1)
    for import_path, doc_path in api_entries[pkg]:
        add(f"[{import_path}]({doc_path})", 2)

# Emit SUMMARY.md
with mkdocs_gen_files.open("SUMMARY.md", "w") as f:
    f.writelines(summary_lines)

# 3) llms.txt via DSPy helper (fallback handled within build_llms_txt)
# Allow override of base URL via env (default: DOCS_BASE_URL=https://docs.ascribe.live)
txt = build_llms_txt(site_name="CRV Agents", base_url=os.getenv("DOCS_BASE_URL"))
with mkdocs_gen_files.open("llms.txt", "w") as f:
    f.write(txt)
