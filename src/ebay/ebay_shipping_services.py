"""Ask eBay which shipping services exist on ebay.de for DHL, Hermes, GLS, DPD (domestic, usable in listings).
Read-only: changes nothing. Uses the Trading API call GeteBayDetails with your login token."""
import re, urllib.request, xml.etree.ElementTree as ET
from ebay_api import cfg, banner, access_token, hosts

CARRIERS = re.compile(r"dhl|hermes|gls|dpd", re.I)
NS = "{urn:ebay:apis:eBLBaseComponents}"

c = cfg(); banner(c); tok = access_token(c)
body = ('<?xml version="1.0" encoding="utf-8"?>'
        '<GeteBayDetailsRequest xmlns="urn:ebay:apis:eBLBaseComponents">'
        '<DetailName>ShippingServiceDetails</DetailName></GeteBayDetailsRequest>').encode()
req = urllib.request.Request(f"{hosts(c)['api']}/ws/api.dll", data=body, method="POST", headers={
    "X-EBAY-API-CALL-NAME": "GeteBayDetails", "X-EBAY-API-SITEID": "77",
    "X-EBAY-API-COMPATIBILITY-LEVEL": "1423", "X-EBAY-API-IAF-TOKEN": tok, "Content-Type": "text/xml"})
root = ET.fromstring(urllib.request.urlopen(req, timeout=60).read())
ack = root.findtext(f"{NS}Ack")
if ack not in ("Success", "Warning"):
    for e in root.iter(f"{NS}Errors"): print("eBay error:", e.findtext(f"{NS}LongMessage"))
    raise SystemExit(1)
rows = []
for d in root.iter(f"{NS}ShippingServiceDetails"):
    code, desc = d.findtext(f"{NS}ShippingService") or "", d.findtext(f"{NS}Description") or ""
    if d.findtext(f"{NS}InternationalService") == "true" or d.findtext(f"{NS}ValidForSellingFlow") != "true":
        continue
    if CARRIERS.search(code + " " + desc):
        rows.append((code, desc))
for code, desc in sorted(rows): print(f"{code:<40} {desc}")
print(f"\n{len(rows)} services found.")
