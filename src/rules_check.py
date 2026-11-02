"""Rule-based baseline: keyword and regex checks for each checklist item."""
import csv, re
from common import ROOT, ISSUES, PROFILE, load_listings

CONDITION_WORDS = ["neu", "sehr gut", "gut", "getragen", "zustand", "neuwertig", "ungetragen"]
DEFECT_WORDS = ["keine mängel", "keine flecken", "ohne gebrauchsspuren", "keine löcher", "kratzer", "tragespuren", "gebrauchsspuren", "fleck"]
COLOR_WORDS = ["schwarz", "weiß", "rot", "blau", "grün", "gelb", "creme", "braun", "gold", "türkis", "rosa", "grau", "beige", "cognac", "silber", "lila", "bunt"]

def check(l):
    text = (l["title"] + " " + l["description"]).lower()
    new = l["condition"].lower().startswith("neu")
    non_eu = l["brand"].lower() in [b.lower() for b in PROFILE["non_eu_brands"]]
    return {
        "missing_brand": int(not l["brand"] or l["brand"].lower() not in text),
        "missing_size": int(bool(l["size"]) and not re.search(r"(gr(öße|\.)|größe|\b(xxs|xs|s|m|l|xl)\b|\b\d{2,3}\b)", text)),
        "missing_eu_size": int(non_eu and not re.search(r"\b(3[2-9]|4[0-6]|1[0-7]\d|9\d|\d{2,3} ?cm)\b|eu", text)),
        "missing_fit_note": int(not re.search(r"(ich trage|cm groß|fällt|passt|maße|umfang|weite|länge|getragen bei|fußlänge|innensohle)", text)),
        "missing_color": int(not any(c in text for c in COLOR_WORDS)),
        "missing_condition": int(not any(w in text for w in CONDITION_WORDS)),
        "missing_defects_statement": int(not new and not any(w in text for w in DEFECT_WORDS)),
        "missing_storage_note": int("nichtraucher" not in text),
        "missing_contact_invite": int(not re.search(r"(fragen|anfrage|schreib|melden)", text)),
    }

rows = load_listings()
with open(ROOT / "outputs" / "predictions_rules.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id", *ISSUES]); w.writeheader()
    for l in rows: w.writerow({"id": l["id"], **check(l)})
print("Saved outputs/predictions_rules.csv")
