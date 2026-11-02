import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = json.load(open(ROOT / "config" / "checklist.json", encoding="utf-8"))
PROFILE = json.load(open(ROOT / "config" / "seller_profile.json", encoding="utf-8"))
ISSUES = list(CHECKLIST)

def load_listings(path=None):
    return list(csv.DictReader(open(path or ROOT / "data" / "my_listings.csv", encoding="utf-8")))
