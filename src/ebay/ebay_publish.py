"""Step 3: create eBay listings from reviewed listings.

Input CSV (default outputs/ebay_ready.csv) with columns:
  id, new_title, new_description, brand, size, color, material, condition, price, category_id (optional)
Photos: photos/<id>/*.jpg (1-12 photos, first one is the main photo).

By default it only CREATES the offer (unpublished draft). Add --publish to put it live.
Listings that still contain [BITTE ERGÄNZEN ...] or miss required item specifics are skipped and reported.
"""
import argparse, csv, difflib, re, sys, time
from pathlib import Path
from ebay_api import ROOT, cfg, banner, access_token, category_tree_id, suggest_categories, category_aspects, upload_image, \
    ensure_location, put_inventory_item, create_offer, publish_offer, EbayError

ASPECT_FROM_FIELD = {"Marke": "brand", "Größe": "size", "Farbe": "color", "Material": "material", "Obermaterial": "material"}

def build_aspects(row, aspects_meta):
    """Returns (aspects, missing, invalid). invalid = values not in eBay's list for select-only fields."""
    out, missing, invalid = {}, [], []
    for a in aspects_meta:
        field = ASPECT_FROM_FIELD.get(a["name"])
        val = (row.get("aspect_" + a["name"]) or "").strip() or ((row.get(field) or "").strip() if field else "")
        if val:
            # several values are separated by ";" (a comma can be part of a value, e.g. "7,5 cm")
            vals = [v.strip() for v in val.split(";") if v.strip()][:1 if a["name"] != "Farbe" else 3]
            if a.get("mode") == "SELECTION_ONLY" and a["values"]:
                low = {x.lower(): x for x in a["values"]}
                fixed = []
                for v in vals:
                    if v.lower() in low:
                        fixed.append(low[v.lower()])
                    else:
                        near = difflib.get_close_matches(v, a["values"], n=6, cutoff=0.3)
                        invalid.append(f"{a['name']}='{v}' gibt es nicht (ähnlich: {', '.join(near) or '-'})")
                vals = fixed
            if vals: out[a["name"]] = vals
        elif a["required"]:
            ex = ", ".join(a["values"][:12])
            missing.append(a["name"] + (f" (z.B. {ex})" if ex else ""))
    return out, missing, invalid

def html(desc):
    paras = [p.strip() for p in desc.split("\n\n") if p.strip()]
    def block(p):
        lines = [l.strip() for l in p.split("\n") if l.strip()]
        if all(l[:1] in "•-*" for l in lines):
            return "<ul>" + "".join(f"<li>{l.lstrip('•-* ').strip()}</li>" for l in lines) + "</ul>"
        return "<p>" + "<br>".join(lines) + "</p>"
    return "".join(block(p) for p in paras)

EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D\u2B50\u2B55\u2190-\u21FF]")

def no_emoji(text):
    """eBay does not like emoji (and refuses them in titles). Remove them and tidy spaces."""
    text = EMOJI.sub("", text)
    return "\n".join(re.sub(r"[ \t]{2,}", " ", l).rstrip() for l in text.split("\n"))

def with_retry(fn, *args):
    """eBay sometimes answers 'system error' (25001/500) for no reason: wait and try once more."""
    try:
        return fn(*args)
    except EbayError as e:
        if "25001" not in str(e) and "-> 500" not in str(e):
            raise
        print("  eBay system error, trying again in 5 seconds...")
        time.sleep(5)
        return fn(*args)

SANDBOX_PLACEHOLDER = "https://i.ebayimg.com/images/i/182196556219-0-1/s-l1000.jpg"

CACHE_PATH = ROOT / "outputs" / "ebay_image_cache.json"

def _cache():
    try:
        import json
        return json.load(open(CACHE_PATH, encoding="utf-8"))
    except Exception:
        return {}

def _cache_save(cache):
    import json
    json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"), indent=1)

def upload_photos(c, tok, photos):
    """Upload photos once; remember eBay picture URLs per file (path + size + mtime) so re-runs don't upload again."""
    if c["environment"] == "production":
        cache, urls = _cache(), []
        for p in photos:
            st = p.stat(); key = f"{c['environment']}|{p.relative_to(ROOT).as_posix()}|{st.st_size}|{int(st.st_mtime)}"
            if key not in cache:
                cache[key] = with_retry(upload_image, c, tok, p); _cache_save(cache)
            urls.append(cache[key])
        return urls
    return _upload_photos_sandbox(c, tok, photos)

def _upload_photos_sandbox(c, tok, photos):
    """Upload photo files to eBay. Sandbox often rejects file uploads (eBay error 500):
    there we retry once, then use a placeholder picture so the rest of the flow can be tested.
    In production a failed upload stops this listing (no placeholder ever goes live)."""
    urls = []
    for p in photos:
        try:
            urls.append(upload_image(c, tok, p))
        except EbayError as e:
            try:
                time.sleep(2); urls.append(upload_image(c, tok, p))
            except EbayError:
                if c["environment"] != "sandbox":
                    raise
                print(f"  sandbox: photo upload not supported ({p.name}) -> using placeholder picture")
                return [SANDBOX_PLACEHOLDER]
    return urls

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT / "outputs" / "ebay_ready.csv"))
    ap.add_argument("--only", default="", help="comma-separated ids")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--check", action="store_true", help="only check category and item specifics; uploads and creates nothing")
    a = ap.parse_args()
    c = cfg(); banner(c); tok = access_token(c)
    live = a.publish and c["environment"] == "production"
    if live and not a.only:
        sys.exit("Real publishing needs --only with explicit ids (one or two at a time).")
    if not all(c["policies"].values()): sys.exit("Fill policies in config/ebay.json (run ebay_setup.py).")
    ensure_location(c, tok); tree = category_tree_id(c, tok)
    rows = list(csv.DictReader(open(a.input, encoding="utf-8-sig")))
    if a.only: rows = [r for r in rows if r["id"] in a.only.split(",")]
    report = []
    for r in rows:
        sku = f"V{r['id']}"
        try:
            if "BITTE ERGÄNZEN" in r["new_title"] + r["new_description"]:
                raise ValueError("text still has [BITTE ERGÄNZEN] placeholders")
            versand = (r.get("versand") or "").strip().lower()
            if versand in ("gross", "groß", "big"):
                ship_policy = c["policies"].get("fulfillment_big_policy_id")
                if not ship_policy: raise ValueError("versand=gross, but no big shipping policy: run ebay_setup.py")
            elif versand in ("", "klein", "small"):
                ship_policy = None
            else:
                raise ValueError(f"unknown versand '{versand}' (use empty/klein or gross)")
            cond = c["condition_map"].get(r["condition"].strip())
            if not cond: raise ValueError(f"unknown condition '{r['condition']}' (add to condition_map)")
            pdir = ROOT / "photos" / r["id"]
            if (r.get("photos") or "").strip():   # explicit list, e.g. "01.jpg,02.jpg,04.jpg"
                photos = [pdir / n.strip() for n in r["photos"].split(",") if n.strip()]
                gone = [p.name for p in photos if not p.exists()]
                if gone: raise ValueError(f"photos not found in photos/{r['id']}/: {', '.join(gone)}")
                photos = photos[:12]
            else:
                photos = sorted(pdir.glob("*.jp*g"))[:12]
            if not photos: raise ValueError(f"no photos in photos/{r['id']}/")
            cat, path = r.get("category_id") or "", ""
            if not cat:
                sug = suggest_categories(c, tok, tree, r["new_title"])
                if not sug: raise ValueError("no category suggestion; add category_id")
                cat, path = sug[0]; print(f"{sku}: category {cat} ({path})")
            aspects, missing, invalid = build_aspects(r, category_aspects(c, tok, tree, cat))
            if invalid or missing:
                raise ValueError(" | ".join(x for x in [
                    ("invalid: " + "; ".join(invalid)) if invalid else "",
                    ("missing: " + "; ".join(missing) + " (add columns aspect_<Name>)") if missing else ""] if x))
            if a.check:
                report.append({"id": r["id"], "status": "check OK", "offer_id": "", "listing_id": "", "note": f"{cat}: {path if not r.get('category_id') else ''} | {len(photos)} photos | versand {versand or 'klein'} | {aspects}"[:500]})
                print(report[-1]); continue
            urls = upload_photos(c, tok, photos)
            title = no_emoji(r["new_title"]).strip()
            desc = html(no_emoji(r["new_description"]))
            with_retry(put_inventory_item, c, tok, sku, title, desc, aspects, cond, urls)
            offer = with_retry(create_offer, c, tok, sku, cat, desc, r["price"], ship_policy)
            if live:
                print(f"\n  {sku}: {title}\n  Preis: {float(r['price']):.2f} {c['currency']}  |  Versand: {versand or 'klein'}  |  {len(urls)} Fotos  |  Kategorie {cat}")
                if input("  Really publish on eBay? Type JA to confirm: ").strip() != "JA":
                    report.append({"id": r["id"], "status": "draft offer created (not confirmed)", "offer_id": offer, "listing_id": "", "note": ""})
                    print(report[-1]); continue
            listing = publish_offer(c, tok, offer) if a.publish else ""
            report.append({"id": r["id"], "status": "published" if listing else "draft offer created", "offer_id": offer, "listing_id": listing, "note": ""})
        except (ValueError, EbayError, OSError) as e:
            report.append({"id": r["id"], "status": "skipped", "offer_id": "", "listing_id": "", "note": str(e)[:2000]})
        print(report[-1])
    out = ROOT / "outputs" / "ebay_report.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0])); w.writeheader(); w.writerows(report)
    print("Saved", out)

if __name__ == "__main__":
    main()
