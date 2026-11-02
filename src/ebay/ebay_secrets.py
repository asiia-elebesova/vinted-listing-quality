"""Manage eBay secrets in Windows Credential Manager (via keyring).

  python ebay_secrets.py set      # store Cert ID (Client Secret); typing is hidden
  python ebay_secrets.py status   # what is stored (never prints the values)
  python ebay_secrets.py forget   # delete Cert ID and eBay login for the current environment
"""
import sys, time, getpass
from ebay_api import cfg, banner, secret_get, secret_set, secret_delete

c = cfg(); banner(c)
cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
if cmd == "set":
    s = getpass.getpass(f"Paste Cert ID (Client Secret) for {c['environment']} (input is hidden), then Enter: ").strip()
    pref = "SBX-" if c["environment"] == "sandbox" else "PRD-"
    s = s.strip().strip('"').strip("'").strip()
    if not s.startswith(pref):
        hint = "nothing was pasted" if not s else f"got {len(s)} characters starting with '{s[:4]}'"
        sys.exit(f"This does not look like a {c['environment']} Cert ID (should start with {pref}; {hint}). Nothing saved.")
    secret_set(c, "client_secret", s); print("Saved.")
elif cmd == "status":
    print("Cert ID:     ", "stored" if secret_get(c, "client_secret") else "MISSING")
    exp = secret_get(c, "refresh_token_expires_at")
    if secret_get(c, "refresh_token"):
        days = (int(exp) - time.time()) / 86400 if exp and exp != "0" else None
        print("eBay login:   connected" + (f", valid ~{days:.0f} more days" if days else ""))
    else:
        print("eBay login:   not connected")
elif cmd == "forget":
    for n in ["client_secret", "refresh_token", "refresh_token_expires_at"]: secret_delete(c, n)
    print("Deleted. To also revoke access on eBay's side: eBay > Konto > Einstellungen > 'Drittanbieter-Apps' / developer.ebay.com > Application Keys > reset Cert ID.")
else:
    sys.exit(__doc__)
