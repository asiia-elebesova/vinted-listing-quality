"""Manage listings that are already on eBay.

  python ebay_manage.py list               # show all your items: status, price, link
  python ebay_manage.py end 10475828265    # take an item off sale (e.g. sold on Vinted); several ids: 1,2,3

"end" does not delete anything: the listing stops, the draft stays.
To put it back on sale: ebay_publish.py --only <id> --publish
"""
import sys
from ebay_api import cfg, banner, access_token, list_inventory, find_offer, get_offer, withdraw_offer, item_url, EbayError

STATUS = {"PUBLISHED": "ONLINE", "UNPUBLISHED": "draft / ended"}

def sku_of(x):
    x = x.strip()
    return x if x.startswith("V") else "V" + x

def cmd_list(c, tok):
    items = list_inventory(c, tok)
    if not items:
        print("No items on eBay yet."); return
    print(f"{'Vinted id':<14}{'status':<16}{'price':>9}  title / link")
    for sku, title in items:
        try:
            oid = find_offer(c, tok, sku)
            o = get_offer(c, tok, oid) if oid else None
        except EbayError:
            print(f"{sku[1:]:<14}{'eBay no answer':<16}{'':>9}  {title[:60]}  (run list again)"); continue
        if not oid:
            print(f"{sku[1:]:<14}{'no offer':<16}{'':>9}  {title[:60]}"); continue
        st = STATUS.get(o.get("status"), o.get("status", "?"))
        price = o.get("pricingSummary", {}).get("price", {})
        lid = o.get("listing", {}).get("listingId", "")
        print(f"{sku[1:]:<14}{st:<16}{price.get('value', ''):>6} {price.get('currency', ''):<3} {title[:60]}")
        if lid and o.get("status") == "PUBLISHED":
            print(f"{'':<30}{item_url(c, lid)}")

def cmd_end(c, tok, ids):
    for raw in ids.split(","):
        sku = sku_of(raw)
        oid = find_offer(c, tok, sku)
        if not oid:
            print(f"{sku[1:]}: not found on eBay"); continue
        o = get_offer(c, tok, oid)
        if o.get("status") != "PUBLISHED":
            print(f"{sku[1:]}: not online (already ended or never published)"); continue
        if c["environment"] == "production":
            if input(f"{sku[1:]}: take this listing off eBay? Type JA: ").strip() != "JA":
                print("  skipped"); continue
        try:
            withdraw_offer(c, tok, oid); print(f"{sku[1:]}: ended (draft kept)")
        except EbayError as e:
            print(f"{sku[1:]}: could not end -> {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("list", "end") or (sys.argv[1] == "end" and len(sys.argv) < 3):
        sys.exit(__doc__)
    c = cfg(); banner(c); tok = access_token(c)
    cmd_list(c, tok) if sys.argv[1] == "list" else cmd_end(c, tok, sys.argv[2])
