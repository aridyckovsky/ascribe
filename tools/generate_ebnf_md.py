from pathlib import Path

p = Path("src/crv/core/core.ebnf")
ebnf = p.read_text(encoding="utf-8")
out = Path("docs/grammar/ebnf.md")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("# CRV Core Grammar (EBNF)\n\n```ebnf\n" + ebnf + "\n```\n", encoding="utf-8")
print(f"[ok] wrote {out}")
