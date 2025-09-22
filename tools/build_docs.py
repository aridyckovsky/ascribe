from pathlib import Path

import mkdocs_gen_files  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parents[1]
p = Path("src/crv/core/core.ebnf")
ebnf = p.read_text(encoding="utf-8")
out = Path("docs/grammar/ebnf.md")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("# CRV Core Grammar (EBNF)\n\n```ebnf\n" + ebnf + "\n```\n", encoding="utf-8")
print(f"[ok] wrote {out}")

# 1) EBNF.md
ebnf_md = Path("grammar/ebnf.md")
with mkdocs_gen_files.open(ebnf_md, "w") as f:
    f.write("# CRV Core Grammar (EBNF)\n\n")
    f.write("```ebnf\n")
    f.write(ebnf.rstrip() + "\n")
    f.write("```\n")
mkdocs_gen_files.set_edit_path(ebnf_md, "src/crv/core/grammar.py")

# 1b) Project and package READMEs surfaced in docs
repo_readme = ROOT / "README.md"
if repo_readme.exists():
    index_md = Path("index.md")
    readme_text = repo_readme.read_text(encoding="utf-8")
    readme_text = readme_text.replace(
        "## Citation (Future-thinking)",
        '<a id="citation"></a>\n## Citation (Future-thinking)',
    )
    with mkdocs_gen_files.open(index_md, "w") as f:
        f.write(readme_text)
    mkdocs_gen_files.set_edit_path(index_md, "README.md")

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

# 2) API Reference: generate a full module tree for crv.* packages
PACKAGES = ["core", "io", "lab", "mind", "viz", "world"]

# Generate a minimal Getting Started page under Guide
getting_started_md = Path("guide/getting-started.md")
getting_started_md.parent.mkdir(parents=True, exist_ok=True)
with mkdocs_gen_files.open(getting_started_md, "w") as f:
    f.write(
        "# Getting Started\n\n"
        "Follow these steps to set up CRV Agents locally and run a minimal example.\n\n"
        "## Prerequisites\n\n"
        "- Python 3.13+ (verify: `python3 --version`)\n"
        "- uv (Python packaging tool)\n\n"
        "Install uv (macOS/Linux):\n\n"
        "```bash\n"
        "curl -LsSf https://astral.sh/uv/install.sh | sh\n"
        "```\n"
        "Or via pipx:\n"
        "```bash\n"
        "pipx install uv\n"
        "```\n\n"
        "## Clone and install\n\n"
        "```bash\n"
        "git clone https://github.com/aridyckovsky/crv_agents.git\n"
        "cd crv_agents\n"
        "uv sync\n"
        "```\n\n"
        "## Quick start\n\n"
        "Run a small demo (see scripts/ for more examples):\n"
        "```bash\n"
        "uv run python scripts/run_small_sim.py\n"
        "```\n\n"
        "## Develop/docs locally\n\n"
        "Build docs (strict):\n"
        "```bash\n"
        "bash tools/generate_docs.sh\n"
        "```\n\n"
        "## Next steps\n\n"
        "- Read the Core contracts and grammar.\n"
        "- Explore module guides for IO, Lab, Viz, Mind, and World.\n"
    )

summary_lines: list[str] = []
# Define full top-level nav via literate-nav (overrides mkdocs.yaml nav)
summary_lines.extend(
    [
        "- [Overview](index.md)",
        "- Guide",
        "    - [Getting Started](guide/getting-started.md)",
        "    - Core",
        "        - [Contracts (README)](src/crv/core/README.md)",
        "        - [Grammar (EBNF)](grammar/ebnf.md)",
        "        - [Grammar diagrams (HTML)](grammar/diagrams.html)",
        "    - [IO](src/crv/io/README.md)",
        "    - [Lab](src/crv/lab/README.md)",
        "    - [Viz](src/crv/viz/README.md)",
        "    - [Mind](src/crv/mind/README.md)",
        "    - [World](src/crv/world/README.md)",
        "- API Reference",
    ]
)

for pkg in PACKAGES:
    pkg_dir = ROOT / "src" / "crv" / pkg
    if not pkg_dir.exists():
        continue

    pkg_import = f"crv.{pkg}"

    # Package index page
    pkg_index_md = Path(f"api/crv/{pkg}/index.md")
    pkg_index_md.parent.mkdir(parents=True, exist_ok=True)
    with mkdocs_gen_files.open(pkg_index_md, "w") as f:
        f.write(f"# `{pkg_import}` API\n\n")
        f.write("See the module pages listed in the navigation.\n")
    # Link edit path to the package __init__.py if present
    init_path = Path(f"src/crv/{pkg}/__init__.py")
    if init_path.exists():
        mkdocs_gen_files.set_edit_path(pkg_index_md, init_path.as_posix())

    # SUMMARY: top-level entry for the package
    summary_lines.append(f"    - [{pkg_import}]({pkg_index_md.as_posix()})")

    # Walk all modules in the package
    for py_file in sorted(pkg_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue

        rel_from_src = py_file.relative_to(ROOT / "src")  # e.g., crv/io/read.py
        import_path = ".".join(rel_from_src.with_suffix("").parts)  # e.g., crv.io.read

        # Destination doc path mirrors the python module path under api/
        doc_path = Path("api") / rel_from_src.with_suffix(".md")
        doc_path.parent.mkdir(parents=True, exist_ok=True)

        with mkdocs_gen_files.open(doc_path, "w") as f:
            f.write(f"# `{import_path}`\n\n::: {import_path}\n")
        mkdocs_gen_files.set_edit_path(doc_path, rel_from_src.as_posix())

        leaf_name = import_path.split(".")[-1]
        summary_lines.append(f"        - [{leaf_name}]({doc_path.as_posix()})")

# 3) Write SUMMARY.md for literate-nav with just the API section
with mkdocs_gen_files.open("SUMMARY.md", "w") as f:
    f.write("\n".join(summary_lines) + "\n")
