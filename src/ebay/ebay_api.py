"""Minimal eBay REST client (standard library only): OAuth user token, Taxonomy, Media, Account and Inventory APIs."""
import base64, json, re, secrets, time, uuid, urllib.parse, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "config" / "ebay.json"
OLD_TOKEN_PATH = ROOT / ".ebay_token.json"   # older versions stored tokens here; no longer used
KEYRING_SERVICE = "vinted-listing-quality-ebay"
# Minimal permissions: read public data, manage own listings, read/manage own business policies. Nothing about money or orders.
SCOPES = ["https://api.ebay.com/oauth/api_scope",
          "https://api.ebay.com/oauth/api_scope/sell.inventory",
          "https://api.ebay.com/oauth/api_scope/sell.account"]

# ---------- Secrets (Windows Credential Manager via keyring; never in files) ----------
def _keyring():
    try:
        import keyring
    except ImportError:
        raise SystemExit("Install the secure store first:  pip install keyring")
    return keyring

def secret_get(c, name):
    return _keyring().get_password(KEYRING_SERVICE, f"{c['environment']}:{name}")

def secret_set(c, name, value):
    _keyring().set_password(KEYRING_SERVICE, f"{c['environment']}:{name}", value)

def secret_delete(c, name):
    kr = _keyring()
    try:
        kr.delete_password(KEYRING_SERVICE, f"{c['environment']}:{name}")
        return True
    except kr.errors.PasswordDeleteError:
        return False

ENVS = ("sandbox", "production")

def raw_cfg():
    if not CFG_PATH.exists():
        raise SystemExit("Copy config/ebay.example.json to config/ebay.json and fill in client_id and ru_name.")
    return json.load(open(CFG_PATH, encoding="utf-8"))

def save_raw_cfg(raw):
    json.dump(raw, open(CFG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def cfg():
    """Settings for the active environment: shared fields + the 'sandbox' or 'production' section."""
    raw = raw_cfg()
    env = raw.get("environment")
    if env not in ENVS:
        raise SystemExit('config/ebay.json: "environment" must be "sandbox" or "production".')
    if "client_secret" in json.dumps(raw):
        raise SystemExit("config/ebay.json contains client_secret. Delete it and run:  python ebay_secrets.py set")
    c = {k: v for k, v in raw.items() if k not in ENVS}
    c.update(raw.get(env, {}))
    tag = "-SBX-" if env == "sandbox" else "-PRD-"
    if tag not in c.get("client_id", ""):
        raise SystemExit(f"config/ebay.json: the {env} App ID must contain {tag}. Check the '{env}' section.")
    if OLD_TOKEN_PATH.exists():
        print(f"WARNING: old token file {OLD_TOKEN_PATH} found. Delete it (tokens now live in Windows Credential Manager).")
    return c

def banner(c):
    if c["environment"] == "production":
        print("=" * 60 + "\n  PRODUCTION: real eBay account, real listings\n" + "=" * 60)
    else:
        print("[sandbox: test eBay, nothing is real]")

def _client_secret(c):
    s = secret_get(c, "client_secret")
    if not s:
        raise SystemExit(f"No Cert ID stored for {c['environment']}. Run:  python ebay_secrets.py set")
    return s

def hosts(c):
    sb = c["environment"] == "sandbox"
    return {"auth": "https://auth.sandbox.ebay.com" if sb else "https://auth.ebay.com",
            "api": "https://api.sandbox.ebay.com" if sb else "https://api.ebay.com",
            "apim": "https://apim.sandbox.ebay.com" if sb else "https://apim.ebay.com"}

class EbayError(Exception):
    pass

def _request(method, url, token=None, body=None, headers=None, raw=False):
    if not url.startswith("https://"):
        raise EbayError(f"refusing non-HTTPS URL: {url}")
    h = {"Accept": "application/json"}
    if token: h["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None and not raw:
        data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    elif raw:
        data = body
    h.update(headers or {})
    for attempt in range(4):
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                txt = r.read().decode() or "{}"
                return json.loads(txt), dict(r.headers)
        except urllib.error.HTTPError as e:
            raise EbayError(f"{method} {url} -> {e.code}: {e.read().decode()[:1500]}")
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            # connection dropped / timeout: wait and try again (the request did not reach eBay or got no answer)
            if attempt == 3:
                raise EbayError(f"{method} {url} -> network error after 4 tries: {e}")
            wait = 5 * (attempt + 1)
            print(f"  connection problem ({e.__class__.__name__}), retrying in {wait} s...")
            time.sleep(wait)

# ---------- OAuth ----------
def consent_url(c, state):
    if c["ru_name"].startswith("YOUR_"):
        raise SystemExit(f"No RuName for {c['environment']} yet: put it into config/ebay.json -> '{c['environment']}' -> ru_name.")
    q = urllib.parse.urlencode({"client_id": c["client_id"], "redirect_uri": c["ru_name"],
                                "response_type": "code", "scope": " ".join(SCOPES), "state": state},
                               quote_via=urllib.parse.quote)  # eBay wants %20 between scopes, not +
    return f"{hosts(c)['auth']}/oauth2/authorize?{q}"

def new_state():
    return secrets.token_urlsafe(24)

def _token_call(c, form):
    basic = base64.b64encode(f"{c['client_id']}:{_client_secret(c)}".encode()).decode()
    req = urllib.request.Request(f"{hosts(c)['api']}/identity/v1/oauth2/token", method="POST",
        data=urllib.parse.urlencode(form).encode(),
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        # eBay error bodies do not echo credentials; still keep it short
        raise EbayError(f"token -> {e.code}: {e.read().decode()[:400]}")

_ACCESS = {}  # access token lives only in memory for the current run

def exchange_code(c, code):
    t = _token_call(c, {"grant_type": "authorization_code", "code": code, "redirect_uri": c["ru_name"]})
    secret_set(c, "refresh_token", t["refresh_token"])
    secret_set(c, "refresh_token_expires_at", str(int(time.time() + t.get("refresh_token_expires_in", 0))))
    _ACCESS[c["environment"]] = (t["access_token"], time.time() + t["expires_in"] - 120)
    return True

def access_token(c):
    cached = _ACCESS.get(c["environment"])
    if cached and time.time() < cached[1]:
        return cached[0]
    rt = secret_get(c, "refresh_token")
    if not rt:
        raise SystemExit(f"Not connected to eBay ({c['environment']}). Run:  python ebay_login.py")
    n = _token_call(c, {"grant_type": "refresh_token", "refresh_token": rt, "scope": " ".join(SCOPES)})
    _ACCESS[c["environment"]] = (n["access_token"], time.time() + n["expires_in"] - 120)
    return n["access_token"]

# ---------- Taxonomy ----------
def category_tree_id(c, tok):
    r, _ = _request("GET", f"{hosts(c)['api']}/commerce/taxonomy/v1/get_default_category_tree_id?marketplace_id={c['marketplace_id']}", tok)
    return r["categoryTreeId"]

def suggest_categories(c, tok, tree, query):
    q = urllib.parse.quote(query)
    r, _ = _request("GET", f"{hosts(c)['api']}/commerce/taxonomy/v1/category_tree/{tree}/get_category_suggestions?q={q}", tok,
                    headers={"Accept-Language": c["content_language"]})
    return [(s["category"]["categoryId"], " > ".join([a["categoryName"] for a in reversed(s.get("categoryTreeNodeAncestors", []))] + [s["category"]["categoryName"]]))
            for s in r.get("categorySuggestions", [])]

def category_aspects(c, tok, tree, category_id):
    r, _ = _request("GET", f"{hosts(c)['api']}/commerce/taxonomy/v1/category_tree/{tree}/get_item_aspects_for_category?category_id={category_id}", tok,
                    headers={"Accept-Language": c["content_language"]})
    out = []
    for a in r.get("aspects", []):
        con = a.get("aspectConstraint", {})
        out.append({"name": a["localizedAspectName"], "required": con.get("aspectRequired", False),
                    "mode": con.get("aspectMode", "FREE_TEXT"),
                    "values": [v["localizedValue"] for v in a.get("aspectValues", [])]})
    return out

# ---------- Media ----------
def upload_image(c, tok, path):
    boundary = uuid.uuid4().hex
    data = path.read_bytes()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: image/jpeg\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    _, headers = _request("POST", f"{hosts(c)['apim']}/commerce/media/v1_beta/image/create_image_from_file", tok,
                          body=body, raw=True, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    loc = headers.get("Location") or headers.get("location")
    r, _ = _request("GET", loc, tok)
    return r["imageUrl"]

# ---------- Account (policies) ----------
def list_policies(c, tok):
    out = {}
    for kind in ["fulfillment", "payment", "return"]:
        r, _ = _request("GET", f"{hosts(c)['api']}/sell/account/v1/{kind}_policy?marketplace_id={c['marketplace_id']}", tok)
        out[kind] = [(p[f"{kind}PolicyId"], p["name"]) for p in r.get(f"{kind}Policies", [])]
    return out

def create_policy(c, tok, kind, body):
    """kind: fulfillment | payment | return. Returns the new policy ID."""
    body = dict(body, marketplaceId=c["marketplace_id"], categoryTypes=[{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}])
    r, _ = _request("POST", f"{hosts(c)['api']}/sell/account/v1/{kind}_policy", tok, body)
    return r[f"{kind}PolicyId"]

def opt_in_policies(c, tok):
    return _request("POST", f"{hosts(c)['api']}/sell/account/v1/program/opt_in", tok, {"programType": "SELLING_POLICY_MANAGEMENT"})

# ---------- Inventory ----------
def ensure_location(c, tok):
    L = c["location"]
    try:
        _request("GET", f"{hosts(c)['api']}/sell/inventory/v1/location/{L['key']}", tok); return
    except EbayError:
        pass
    _request("POST", f"{hosts(c)['api']}/sell/inventory/v1/location/{L['key']}", tok, {
        "location": {"address": {"city": L["city"], "postalCode": L["postal_code"], "country": L["country"]}},
        "name": L["name"], "merchantLocationStatus": "ENABLED", "locationTypes": ["WAREHOUSE"]})

def put_inventory_item(c, tok, sku, title, description, aspects, condition, image_urls):
    _request("PUT", f"{hosts(c)['api']}/sell/inventory/v1/inventory_item/{sku}", tok, {
        "availability": {"shipToLocationAvailability": {"quantity": 1}},
        "condition": condition,
        "product": {"title": title[:80], "description": description, "aspects": aspects, "imageUrls": image_urls}},
        headers={"Content-Language": c["content_language"]})

def find_offer(c, tok, sku):
    """Existing offer ID for this SKU on this marketplace, or None."""
    url = f"{hosts(c)['api']}/sell/inventory/v1/offer?sku={urllib.parse.quote(sku)}&marketplace_id={c['marketplace_id']}"
    for attempt in range(3):
        try:
            r, _ = _request("GET", url, tok)
            break
        except EbayError as e:
            if "-> 404" in str(e) or "25713" in str(e):   # really no offer for this SKU
                return None
            if attempt == 2:
                raise                                     # eBay did not answer: do NOT pretend there is no offer
            time.sleep(3)
    offers = r.get("offers", [])
    return offers[0]["offerId"] if offers else None

def create_offer(c, tok, sku, category_id, description, price, fulfillment_policy_id=None):
    """Create the offer, or update it if this SKU already has one (price, text, category, policies)."""
    P = dict(c["policies"])
    if fulfillment_policy_id:
        P["fulfillment_policy_id"] = fulfillment_policy_id
    body = {
        "sku": sku, "marketplaceId": c["marketplace_id"], "format": "FIXED_PRICE", "availableQuantity": 1,
        "categoryId": category_id, "listingDescription": description,
        "listingPolicies": {"fulfillmentPolicyId": P["fulfillment_policy_id"], "paymentPolicyId": P["payment_policy_id"],
                            "returnPolicyId": P["return_policy_id"],
                            **({"bestOfferTerms": {"bestOfferEnabled": True}} if c.get("best_offer") else {})},
        "pricingSummary": {"price": {"value": f"{float(price):.2f}", "currency": c["currency"]}},
        "merchantLocationKey": c["location"]["key"]}
    existing = find_offer(c, tok, sku)
    if existing:
        _request("PUT", f"{hosts(c)['api']}/sell/inventory/v1/offer/{existing}", tok, body,
                 headers={"Content-Language": c["content_language"]})
        return existing
    try:
        r, _ = _request("POST", f"{hosts(c)['api']}/sell/inventory/v1/offer", tok, body,
                        headers={"Content-Language": c["content_language"]})
        return r["offerId"]
    except EbayError as e:
        m = re.search(r'"offerId"\s*,\s*"value"\s*:\s*"(\d+)"', str(e)) or re.search(r"already exists.*?(\d{9,})", str(e))
        if not m:
            raise
        _request("PUT", f"{hosts(c)['api']}/sell/inventory/v1/offer/{m.group(1)}", tok, body,
                 headers={"Content-Language": c["content_language"]})
        return m.group(1)

def publish_offer(c, tok, offer_id):
    r, _ = _request("POST", f"{hosts(c)['api']}/sell/inventory/v1/offer/{offer_id}/publish", tok, {})
    return r.get("listingId")

def list_inventory(c, tok):
    """All SKUs in your eBay inventory (one page of up to 200)."""
    r, _ = _request("GET", f"{hosts(c)['api']}/sell/inventory/v1/inventory_item?limit=200", tok)
    return [(i["sku"], i.get("product", {}).get("title", "")) for i in r.get("inventoryItems", [])]

def get_offer(c, tok, offer_id):
    r, _ = _request("GET", f"{hosts(c)['api']}/sell/inventory/v1/offer/{offer_id}", tok)
    return r

def withdraw_offer(c, tok, offer_id):
    """End the live listing. The offer stays as an unpublished draft and can be published again."""
    _request("POST", f"{hosts(c)['api']}/sell/inventory/v1/offer/{offer_id}/withdraw", tok, {})

def item_url(c, listing_id):
    return (f"https://www.sandbox.ebay.com/itm/{listing_id}" if c["environment"] == "sandbox"
            else f"https://www.ebay.de/itm/{listing_id}")

