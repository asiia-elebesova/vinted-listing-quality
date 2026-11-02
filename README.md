# Vinted listing quality checker

An LLM-assisted tool that checks second-hand fashion listings against a seller's own quality checklist,
drafts improved German titles and descriptions, and measures how well the checks work with precision and recall.

Built for my own Vinted (Germany) wardrobe: many of my items come from Russian brands with different size charts,
and buyers need clear information on size, fit, condition and defects to buy without returns.

## What it checks

The checklist lives in `config/checklist.json` and can be edited without touching the code:

| Check | Why it matters |
|---|---|
| Brand | Buyers search by brand |
| Size | Basic filter |
| EU size for non-EU brands | Russian sizes (e.g. Zolla, Love Republic, InCity) do not map 1:1 to EU sizes |
| Fit note | Label sizes vary by cut; the seller's own size and height help buyers judge the fit |
| Colour | Search and expectations |
| Condition in words | Avoids disputes |
| Defects statement | Either describe defects or state there are none |
| Storage note | Non-smoking, pet-free household |
| Contact invitation | Buyers ask for measurements before buying |

Seller-specific information (height, usual size, standard phrases, list of non-EU brands) is in `config/seller_profile.json`.

## Data

- `data/my_listings.csv`: 20 of my real, publicly visible Vinted listings (title, brand, size, condition, material, colour, price, description).
- `data/labels.csv`: my manual labels of which checklist items are missing in each listing (1 = issue present).
- `data/new_listings_template.csv`: template to check new items before uploading them.

## How it works

1. `src/rules_check.py`: rule-based baseline with keywords and regular expressions.
2. `src/llm_review.py`: each listing is sent to Claude via the Anthropic Messages API (standard library only, no SDK)
   with the checklist and seller profile. Claude returns a flag for every check, questions about missing facts,
   and a rewritten German title and description. It must not invent facts: missing information becomes a
   placeholder such as `[BITTE ERGÄNZEN: Mängel ja/nein]`.
3. `src/evaluate.py`: predictions are joined with the labels in SQLite; precision, recall and F1 are computed in SQL.
4. `src/report.py`: a before/after report of all rewrites.

## Results

Rule-based baseline on 20 listings:

| Check | Precision | Recall | F1 |
|---|---|---|---|
| missing_brand | 0.86 | 1.00 | 0.92 |
| missing_eu_size | 0.50 | 1.00 | 0.67 |
| missing_fit_note | 0.83 | 0.62 | 0.71 |
| missing_color | 0.00 | 0.00 | 0.00 |
| missing_condition | 0.00 | 0.00 | 0.00 |
| missing_defects_statement | 0.78 | 0.88 | 0.82 |
| missing_storage_note | 1.00 | 1.00 | 1.00 |
| missing_contact_invite | 1.00 | 1.00 | 1.00 |

Rules work for fixed phrases (non-smoking note, contact invitation) but fail where meaning matters:
"Der Zustand ist auf den Fotos zu sehen" contains the word "Zustand" but does not state the condition, and a fit
can be described in many ways. LLM results: see `outputs/evaluation.md` after running the steps below.

## How to run

Requires Python 3.9+ and an Anthropic API key.

```bash
python src/rules_check.py
# PowerShell: $env:ANTHROPIC_API_KEY="your_key"    bash: export ANTHROPIC_API_KEY=your_key
python src/llm_review.py --limit 3
python src/llm_review.py
python src/evaluate.py outputs/predictions_rules.csv outputs/predictions_llm.csv
python src/report.py
# new items: python src/llm_review.py --input data/new_listings_template.csv
```

The model can be changed with `--model` or `CLAUDE_MODEL`.

## Optional: publish to eBay (official API)

`src/ebay/` turns reviewed listings into eBay.de listings through eBay's official Sell APIs
(OAuth user token, Taxonomy API for category and required item specifics, Media API for photos,
Inventory API for item, offer and publish). It runs in the sandbox by default, creates unpublished
offers unless `--publish` is passed, and skips any listing that still has `[BITTE ERGÄNZEN]`
placeholders, missing photos or missing required item specifics. Vinted and Kleinanzeigen offer no
public seller API, so the project never automates those platforms. Setup steps: `EBAY_RU.md`.

## Limitations

- Photos are not checked; only text and listing fields.
- Labels were made by one person (me) for 20 listings, so the evaluation is small.
- The tool drafts text; I review every rewrite and upload changes manually. It does not interact with Vinted.
