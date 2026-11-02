"""Show or switch which eBay the programs work with.

  python ebay_env.py              # show current
  python ebay_env.py sandbox      # test eBay (nothing is real)
  python ebay_env.py production   # your REAL eBay account
"""
import sys
from ebay_api import raw_cfg, save_raw_cfg, ENVS

raw = raw_cfg()
if len(sys.argv) > 1:
    if sys.argv[1] not in ENVS: sys.exit(__doc__)
    raw["environment"] = sys.argv[1]; save_raw_cfg(raw)
env = raw["environment"]
print("Now working with:", "REAL eBay (production)" if env == "production" else "test eBay (sandbox)")
