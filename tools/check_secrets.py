"""Run before every GitHub upload:  python tools/check_secrets.py
Looks for eBay Cert IDs, eBay tokens and Anthropic API keys in project files. Prints file + line, never the value."""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {"eBay Cert ID": r"(?<![\w-])(SBX|PRD)-[0-9a-fA-F]{8,}",
            "eBay token": r"v\^1\.1#i\^1",
            "Anthropic API key": r"sk-ant-[A-Za-z0-9_-]{10,}",
            "client_secret value": r'"client_secret"\s*:\s*"[^"Y]'}
SKIP_DIRS = {".git", "photos", "__pycache__", ".venv", "venv"}
hits = 0
for f in ROOT.rglob("*"):
    if not f.is_file() or SKIP_DIRS & set(f.relative_to(ROOT).parts) or f.suffix.lower() in {".jpg", ".jpeg", ".png", ".db", ".sqlite"}:
        continue
    for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        for name, pat in PATTERNS.items():
            if re.search(pat, line):
                hits += 1; print(f"!! {name}: {f.relative_to(ROOT)} line {i}")
ign = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
for must in ["config/ebay.json", ".ebay_token.json", ".env"]:
    if must not in ign: hits += 1; print(f"!! .gitignore is missing {must}")
print("OK: no secrets found." if not hits else f"\n{hits} problem(s). Do NOT upload until fixed.")
sys.exit(1 if hits else 0)
