"""Readable before/after report from outputs/rewrites.csv."""
import csv
from common import ROOT
rows = list(csv.DictReader(open(ROOT / "outputs" / "rewrites.csv", encoding="utf-8-sig")))
md = ["# Listing review", ""]
for r in rows:
    md += [f"## {r['old_title']}", "", f"**New title:** {r['new_title']}", ""]
    if r["questions_for_seller"]: md += [f"**Уточнить:** {r['questions_for_seller']}", ""]
    md += ["**New description:**", "", r["new_description"], "", "---", ""]
(ROOT / "outputs" / "review_report.md").write_text("\n".join(md), encoding="utf-8")
print("Saved outputs/review_report.md")
