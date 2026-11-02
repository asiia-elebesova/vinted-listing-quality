"""Review Vinted listings with Claude: flag missing checklist items and draft an improved German title and description.

No SDK needed: uses only the Python standard library.
    PowerShell:  $env:ANTHROPIC_API_KEY="your_key"
    python src/llm_review.py --limit 3     # quick test
    python src/llm_review.py               # all listings
"""
import argparse, csv, json, os, time, urllib.request, urllib.error
from common import ROOT, ISSUES, CHECKLIST, PROFILE, load_listings

SYSTEM = """You are an assistant for a private seller on Vinted Germany. You check listings against the seller's checklist and rewrite them in natural, friendly German.
Rules:
- Never invent facts (brand, size, measurements, material, defects, condition, origin). Use only information from the listing and the seller profile.
- If important information is missing, insert a placeholder like [BITTE ERGÄNZEN: Mängel ja/nein] instead of guessing.
- For brands from outside the EU, give the EU size if the listing contains it; otherwise insert [BITTE ERGÄNZEN: EU-Größe].
- Add the seller's fit note, storage note and contact invitation from the profile when they are missing.
- Keep the description clear and scannable: one or two short sentences, then a bullet list (Marke, Modell/Art, Größe, Passform, Farbe, Material if known, Zustand, Mängel), then storage note and contact invitation.
- Title: brand + item type + size + colour (+ one key feature), max 80 characters, no emojis."""

USER = """Checklist (an issue is present when the definition applies):
{checklist}

Seller profile:
{profile}

Listing:
{listing}

Return only JSON with these keys:
{keys} (each 0 or 1),
"questions_for_seller": list of short questions in Russian about information you could not find,
"new_title": string,
"new_description": string."""

def call(listing, model, key):
    body = {"model": model, "max_tokens": 1500, "temperature": 0, "system": SYSTEM,
            "messages": [{"role": "user", "content": USER.format(
                checklist=json.dumps(CHECKLIST, ensure_ascii=False, indent=1),
                profile=json.dumps(PROFILE, ensure_ascii=False, indent=1),
                listing=json.dumps(listing, ensure_ascii=False, indent=1),
                keys=", ".join(f'"{i}"' for i in ISSUES))}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
            text = "".join(b.get("text", "") for b in data["content"])
            return json.loads(text[text.find("{"): text.rfind("}") + 1])
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
            if attempt == 3: raise
            time.sleep(2 ** attempt)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--input", default=None, help="CSV with listings (default: data/my_listings.csv)")
    a = ap.parse_args()
    key = os.environ.get("ANTHROPIC_API_KEY") or exit("Set ANTHROPIC_API_KEY first.")
    rows = load_listings(a.input)[: a.limit or None]
    preds, reviews = [], []
    for i, l in enumerate(rows, 1):
        res = call({k: v for k, v in l.items() if k != "id"}, a.model, key)
        preds.append({"id": l["id"], **{k: int(res.get(k, 0)) for k in ISSUES}})
        reviews.append({"id": l["id"], "old_title": l["title"], "new_title": res.get("new_title", ""),
                        "questions_for_seller": " | ".join(res.get("questions_for_seller", [])),
                        "new_description": res.get("new_description", "")})
        print(f"{i}/{len(rows)} {l['id']}")
    with open(ROOT / "outputs" / "predictions_llm.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", *ISSUES]); w.writeheader(); w.writerows(preds)
    with open(ROOT / "outputs" / "rewrites.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(reviews[0])); w.writeheader(); w.writerows(reviews)
    print("Saved outputs/predictions_llm.csv and outputs/rewrites.csv")

if __name__ == "__main__":
    main()
