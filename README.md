# Legal Clear — Florida Pro Se Court Form Assistant

AI-powered tool for self-represented litigants in Florida. Two-phase pipeline:

1. **Form Finder** — interview users, identify their case type, and show required forms with plain-English explanations
2. **Auto-Fill Engine** — download fillable PDFs, extract form fields, interview the user, and generate ready-to-submit court documents

Covers all 20 circuits and 67 counties.

## How It Works

```
User describes their situation
        ↓
Form Finder (decision tree + county lookup)
        ↓
Auto-Fill Engine (pymupdf extracts AcroForm fields)
        ↓
User interview (plain-English questions)
        ↓
Filled PDFs ready for e-filing at myflcourtaccess.com
```

## Features

- **107+ Supreme Court forms** cataloged across 20 form categories
- **52 circuit-specific local forms** from Circuits 5, 10, 11, and 19
- **2,000+ extracted form fields** with types (text, checkbox, radio)
- **County picker** with circuit lookup for all 67 Florida counties
- **Dark-mode web frontend** served at http://100.103.42.109:8088 (Tailscale)
- **Bulk crawler** for harvesting forms from county clerk websites
- **Plain-English explanations** — no legalese required

## Project Structure

```
wiki/
├── scripts/
│   ├── form_finder.py          # Phase 1 — what forms do I need?
│   ├── auto_fill.py            # Phase 2+3 — interview → fill → output PDFs
│   ├── fl_forms_crawler.py     # Bulk crawler (all 67 counties + 20 circuits)
│   └── sources.json            # 117 entry-point URLs for the crawler
├── raw/
│   ├── forms/                  # 68 Supreme Court fillable PDFs
│   │   ├── circuits/           # 52 circuit-specific local PDFs
│   │   └── form_fields.json    # Extracted field names/types for all forms
│   └── articles/
│       └── florida-court-forms-dataset.json  # Cases, circuits, counties
├── index.html                  # Dark-mode bento grid frontend
├── nginx.conf                  # Serves frontend on Tailscale
├── concepts/                   # Wiki: court system, workflows
├── entities/                   # Wiki: DIY Florida, form directory
└── projects/                   # Wiki: Legal Clear overview
```

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install pymupdf pdfplumber httpx

# Find forms for a case type
python3 scripts/form_finder.py --case divorce-with-children --county "Miami-Dade"

# Fill out forms (interactive interview)
python3 scripts/auto_fill.py divorce-with-children
# Output: filled PDFs in /tmp/legal_clear_YYYYMMDD_HHMMSS/
```

## Case Types Supported

| Category | Case Types |
|----------|-----------|
| Family | Divorce (with/without children), child custody, child support modification, name change, domestic violence injunction |
| Housing | Eviction (landlord), eviction defense (tenant) |
| Money | Small claims |
| Estate | Probate (small estate), full probate, guardianship |
| Criminal | Expungement/sealing |

## Important

- **This is NOT legal advice.** Forms and fees change. Always verify with your county clerk.
- DIY Florida (myflcourtaccess.com DIY tab) is not being updated and is unreliable.
- Domestic violence injunctions have NO filing fee.
- Eviction defense: only 5 business days to respond.

## License

MIT
