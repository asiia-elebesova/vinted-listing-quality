"""Step 2: shipping location and business policies (shipping, payment, returns).

Creates the location "home" and the three policies below if a policy with that NAME does not exist yet,
then writes their IDs into config/ebay.json. To change a policy: edit it here AND give it a new name,
run this again, then re-run ebay_publish.py for your items so they use the new policy.
These values are what buyers see."""
from ebay_api import raw_cfg, save_raw_cfg, cfg, banner, access_token, ensure_location, list_policies, opt_in_policies, create_policy, EbayError

def svc(order, code, price):
    return {"sortOrder": order, "shippingServiceCode": code, "shippingCost": {"value": price, "currency": "EUR"}}

DEFAULTS = {
    # Small items (clothes, accessories). Buyer chooses the carrier; all have tracking.
    # Prices = online label, home delivery, smallest size class (checked Nov 2026). No DHL Päckchen: no tracking.
    "fulfillment": {"name": "Versand Kleidung klein",
                    "handlingTime": {"value": 3, "unit": "DAY"},
                    "shippingOptions": [{"optionType": "DOMESTIC", "costType": "FLAT_RATE", "shippingServices": [
                        svc(1, "DE_GLSPaket", "4.59"),
                        svc(2, "DE_DPDClassic", "5.15"),
                        svc(3, "DE_HermesPackchen", "5.19"),
                        svc(4, "DE_DHLPaket", "6.19")]}]},
    # Big parcels (shoes, boots, coats): up to 5 kg, Hermes M <= 80 cm, GLS/DPD M <= 70 cm (longest + shortest side).
    # Use with column versand=gross in the listings CSV.
    "fulfillment_big": {"name": "Versand groß (Schuhe, Stiefel)",
                    "handlingTime": {"value": 3, "unit": "DAY"},
                    "shippingOptions": [{"optionType": "DOMESTIC", "costType": "FLAT_RATE", "shippingServices": [
                        svc(1, "DE_GLSPaket", "6.89"),
                        svc(2, "DE_DPDClassic", "6.95"),
                        svc(3, "DE_HermesPaket", "6.99"),
                        svc(4, "DE_DHLPaket", "7.69")]}]},
    # Payment through eBay, immediate payment required
    "payment": {"name": "Zahlung Standard", "immediatePay": True},
    # Private seller: no returns (eBay buyer protection still applies if the item is not as described)
    "return": {"name": "Keine Rücknahme", "returnsAccepted": False},
}
KEY = {"fulfillment": "fulfillment_policy_id", "fulfillment_big": "fulfillment_big_policy_id",
       "payment": "payment_policy_id", "return": "return_policy_id"}
KIND = {"fulfillment": "fulfillment", "fulfillment_big": "fulfillment", "payment": "payment", "return": "return"}

c = cfg(); banner(c); tok = access_token(c)
ensure_location(c, tok); print("Location OK:", c["location"]["key"])
try:
    pol = list_policies(c, tok)
except EbayError:
    print("Turning on business policies for this account...")
    opt_in_policies(c, tok); pol = list_policies(c, tok)

chosen = {}
for key, body in DEFAULTS.items():
    kind, want = KIND[key], body["name"]
    match = [pid for pid, name in pol[kind] if name == want]
    if match:
        chosen[key] = match[0]; print(f"{key}: using existing '{want}' ({match[0]})")
    else:
        try:
            chosen[key] = create_policy(c, tok, kind, body); print(f"{key}: created '{want}' ({chosen[key]})")
        except EbayError as e:
            print(f"{key}: could not create '{want}': {e}")

raw = raw_cfg()
target = raw[c["environment"]] if c["environment"] in raw else raw
for key, pid in chosen.items():
    target.setdefault("policies", {})[KEY[key]] = pid
save_raw_cfg(raw)
print("\nPolicy IDs saved in config/ebay.json." if len(chosen) == len(DEFAULTS) else "\nSome policies are missing (see errors above).")
print("Items already on eBay keep their old policy until you run ebay_publish.py for them again.")
