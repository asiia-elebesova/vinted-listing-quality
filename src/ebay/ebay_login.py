"""Step 1: connect your eBay account (OAuth). Run once per environment (sandbox / production).
The refresh token is saved in Windows Credential Manager, not in a file."""
import urllib.parse, webbrowser
from ebay_api import cfg, banner, consent_url, new_state, exchange_code, _client_secret

c = cfg(); banner(c)
_client_secret(c)  # fail early if the Cert ID is not stored yet
state = new_state()
url = consent_url(c, state)
print("1) A browser window opens. Sign in to eBay", "(SANDBOX test user!)" if c["environment"] == "sandbox" else "", "and click 'I agree'.")
print("   Check the address bar: it must start with https://auth.sandbox.ebay.com or https://auth.ebay.com")
print("2) You land on a page; copy the FULL address from the address bar and paste it here.\n")
print("If the browser shows an error, send this address (no secrets in it):\n" + url + "\n")
webbrowser.open(url)
redirected = input("Paste the full address: ").strip()
q = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
if q.get("state", [""])[0] != state:
    raise SystemExit("Security check failed: this address does not belong to this login attempt. Run ebay_login.py again.")
if "code" not in q:
    raise SystemExit("No authorization code in the address (did you click 'I agree'?). Run again.")
exchange_code(c, q["code"][0])
print("Connected. Token stored in Windows Credential Manager (service 'vinted-listing-quality-ebay').")
