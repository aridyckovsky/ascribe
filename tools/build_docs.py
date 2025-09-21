from pathlib import Path

import mkdocs_gen_files

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

pyproject = ROOT / "pyproject.toml"
if pyproject.exists():
    pyproject_doc = Path("pyproject.toml")
    with mkdocs_gen_files.open(pyproject_doc, "w") as f:
        f.write(pyproject.read_text(encoding="utf-8"))

# 2) API entry
api_md = Path("api/crv_core.md")
with mkdocs_gen_files.open(api_md, "w") as f:
    f.write("# `crv.core` API\n\n::: crv.core\n")
