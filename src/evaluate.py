"""Precision, recall and F1 per checklist item, computed in SQL (SQLite).
Usage: python src/evaluate.py outputs/predictions_rules.csv [outputs/predictions_llm.csv]
"""
import csv, sqlite3, sys
from pathlib import Path
from common import ROOT, ISSUES

def load(con, table, path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    con.execute(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, {', '.join(i + ' INT' for i in ISSUES)})")
    con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * (len(ISSUES) + 1))})",
                    [[r["id"], *[int(r[i]) for i in ISSUES]] for r in rows])

lines = ["# Evaluation", "", "Ground truth: data/labels.csv (1 = issue present)", ""]
for path in sys.argv[1:]:
    con = sqlite3.connect(":memory:"); load(con, "labels", ROOT / "data" / "labels.csv"); load(con, "pred", path)
    n = con.execute("SELECT COUNT(*) FROM pred").fetchone()[0]
    lines += [f"## {Path(path).name} ({n} listings)", "", "| Issue | TP | FP | FN | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|"]
    for i in ISSUES:
        tp, fp, fn = [x or 0 for x in con.execute(
            f"SELECT SUM(p.{i}=1 AND l.{i}=1), SUM(p.{i}=1 AND l.{i}=0), SUM(p.{i}=0 AND l.{i}=1) FROM pred p JOIN labels l USING(id)").fetchone()]
        p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0; f = 2 * p * r / (p + r) if p + r else 0.0
        lines.append(f"| {i} | {tp} | {fp} | {fn} | " + ("n/a | n/a | n/a |" if tp + fp + fn == 0 else f"{p:.2f} | {r:.2f} | {f:.2f} |"))
    lines.append("")
out = "\n".join(lines); (ROOT / "outputs" / "evaluation.md").write_text(out, encoding="utf-8"); print(out)
