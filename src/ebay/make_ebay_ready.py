"""Merge reviewed rewrites with listing fields into outputs/ebay_ready.csv (edit it in Excel before publishing)."""
import csv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
lst = {r["id"]: r for r in csv.DictReader(open(ROOT / "data" / "my_listings.csv", encoding="utf-8"))}
rw = list(csv.DictReader(open(ROOT / "outputs" / "rewrites.csv", encoding="utf-8-sig")))
cols = ["id", "new_title", "new_description", "brand", "size", "color", "material", "condition", "price", "category_id"]
with open(ROOT / "outputs" / "ebay_ready.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rw:
        l = lst.get(r["id"], {})
        w.writerow({"id": r["id"], "new_title": r["new_title"], "new_description": r["new_description"],
                    **{k: l.get(k, "") for k in ["brand", "size", "color", "material", "condition", "price"]}, "category_id": ""})
print("Saved outputs/ebay_ready.csv - check texts and prices, then add photos to photos/<id>/")
