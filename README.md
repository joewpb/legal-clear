# Legal Clear — Florida Pro Se Court Form Assistant

AI-powered tools for self-represented litigants in Florida. Helps people who can't afford an attorney find, understand, and fill out the right court forms.

Covers all 20 judicial circuits and 67 counties.

## What's Here

This repo is both a **knowledge base** (Obsidian-compatible wiki) and a **toolkit** for working with Florida court forms. It has five main components:

| Component | What it does | Entry point |
|-----------|-------------|-------------|
| **Form Finder** | Decision-tree interview → identifies your case type and required forms with plain-English explanations | `scripts/form_finder.py` |
| **Auto-Fill Engine** | Interactive interview → extracts form fields → fills PDFs ready for e-filing | `scripts/auto_fill.py` |
| **Web Frontend** | Dark-mode bento grid UI with county lookup, circuit info, and form browsing | `index.html` (nginx :8088) |
| **File Browser** | Navigate, preview, and search all wiki files — PDFs, markdown, images, code | `fileserver.py` (:8099) |
| **Crawler** | Bulk harvest form links from 117 source URLs across county clerk websites using Camofox anti-detection browser | `scripts/fl_forms_crawler.py` |

Also: **Quartz** static site generator serves the wiki as a linked knowledge graph on port 8100.

## Project Structure

```
├── scripts/
│   ├── form_finder.py          # Decision tree: 13 case types, 40+ plain-English form explanations
│   ├── auto_fill.py            # Full pipeline: interview → field mapping → PDF fill
│   ├── form_filler.py          # Lower-level: fill a single form with a JSON payload
│   ├── fl_forms_crawler.py     # Bulk crawler (validate + crawl + consolidate via Camofox)
│   └── sources.json            # 117 entry-point URLs (state portals + county clerk sites)
│
├── raw/
│   ├── forms/                  # 125 downloaded PDFs (98MB total)
│   │   ├── circuits/           #  52 circuit-specific local forms (Circuits 5, 11, 19)
│   │   ├── full_catalog.json   #  71 forms indexed with download URLs and metadata
│   │   ├── form_fields.json    #  Extracted AcroForm field names/types (10 forms, ~400 fields)
│   │   └── downloads.json      #  Manifest: form ID → local path → official source URL
│   └── articles/
│       └── florida-court-forms-dataset.json  # Master dataset: 13 case types, 20 circuits, 67 counties
│
├── concepts/                   # Wiki: Florida court system, workflows
├── entities/                   # Wiki: DIY Florida, form directory reference
├── projects/                   # Wiki: Legal Clear project overview and roadmap
├── docs/                       # Additional documentation
│
├── SCHEMA.md                   # Wiki conventions: frontmatter, tags, page types, update policy
├── log.md                      # Append-only action log (ingest, create, update, lint, archive)
├── index.md                    # Wiki hub: links to all pages by section
│
├── index.html                  # Dark-mode bento grid frontend (served by nginx)
├── file-browser.html           # File browser UI (served by fileserver.py)
├── fileserver.py               # Python stdlib HTTP server with markdown rendering + directory listing
├── nginx.conf                  # Two virtual hosts: Legal Clear (:8088) + Quartz wiki (:8100)
└── .gitignore
```

## Quick Start

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install pymupdf pdfplumber httpx

# Find forms for your situation
python3 scripts/form_finder.py
# Or directly:
python3 scripts/form_finder.py --case divorce-with-children --county "Miami-Dade"

# Fill out forms (interactive)
python3 scripts/auto_fill.py divorce-with-children
# Output: filled PDFs in /tmp/legal_clear_YYYYMMDD_HHMMSS/

# Fill a single form with a JSON payload
python3 scripts/form_filler.py --form 12.901_b__1_.pdf --data my_fields.json

# Serve the web frontend + file browser
nginx -c "$(pwd)/nginx.conf"     # frontend on :8088, wiki on :8100
python3 fileserver.py             # file browser on :8099
```

## Case Types Covered

| Category | Case Types |
|----------|-----------|
| **Family** | Divorce with children, divorce without children, child custody/time-sharing, child support modification, name change (adult) |
| **Protection** | Domestic violence injunction (family/dating/cohabitant) |
| **Housing** | Eviction (landlord), eviction defense (tenant) |
| **Money** | Small claims — auto damage, unpaid goods, unpaid work, unpaid loans, security deposits, promissory notes |
| **Estate** | Small estate probate (<$75K), full probate, guardianship |
| **Criminal** | Expungement / record sealing |

## Data Layers

The project organizes Florida's fragmented court form system into a unified dataset:

| Layer | Source | Coverage |
|-------|--------|----------|
| **Supreme Court forms** | flcourts.gov | Statewide family law, small claims, probate, domestic violence |
| **DIY Florida** | myflcourtaccess.com | Interactive form builder for 5 case types with auto-fill + e-file |
| **Circuit-specific forms** | 20 circuit court websites | Local forms from Circuits 5, 11, 19 (52 forms) |
| **County clerk sites** | 67 county websites | Fee schedules, procedural forms, self-help pages |

Master dataset: `raw/articles/florida-court-forms-dataset.json` — 13 case types, 20 circuits with self-help URLs, 67 counties with clerk URLs, 10 centralized resource links.

## Crawler (fl_forms_crawler.py)

Three-phase pipeline designed for the Camofox anti-detection browser:

1. **VALIDATE** — Check every URL in an existing index, flag dead links → CSV report
2. **CRAWL** — Render each source page via Camofox, harvest every form link, download + hash PDFs, deduplicate
3. **CONSOLIDATE** — Emit canonical index with file hashes, detect PDF/DOCX format mismatches (revision drift)

```bash
python3 scripts/fl_forms_crawler.py validate --index index.json
python3 scripts/fl_forms_crawler.py crawl --sources scripts/sources.json
python3 scripts/fl_forms_crawler.py all --index index.json --sources scripts/sources.json
```

Requires Camofox running on localhost:9377 (`systemctl --user start camofox.service`).

## Wiki

This repo is an Obsidian-compatible knowledge base:

- **[[wikilinks]]** connect pages — minimum 2 outbound links per page
- **YAML frontmatter** on every page with type, tags, confidence, status
- **Append-only log** (`log.md`) tracking all actions
- **Tag taxonomy** in `SCHEMA.md` — 20 tags across domain, content-type, and quality categories
- **Quartz** serves the wiki as a static site on port 8100

Page types: entity, concept, comparison, query, project, decision, tool.

## Known Issues & Path Hardcoding

Several files contain absolute paths to `/home/hermes/wiki/`. These need to be made relative or configurable before the project can be cloned and run elsewhere:

| File | Hardcoded Path |
|------|---------------|
| `fileserver.py` | `ROOT_DIR = Path("/home/hermes/wiki")` |
| `nginx.conf` | `root /home/hermes/wiki` ×2 |
| `scripts/auto_fill.py` | `FORMS_DIR = Path("/home/hermes/wiki/raw/forms")`, `VENV = "/home/hermes/wiki/venv/bin/python3"` |
| `scripts/form_filler.py` | likely similar |
| `scripts/fl_forms_crawler.py` | `FORMS_DIR = Path("/home/hermes/wiki/raw/forms")` |

## Important

- **This is NOT legal advice.** Forms, fees, and procedures change. Always verify with the official source.
- DIY Florida (myflcourtaccess.com DIY tab) covers 5 case types but is not being updated and is unreliable.
- Domestic violence injunctions have **NO filing fee**.
- Eviction defense: only **5 business days** to respond.
- You represent yourself — the court expects you to follow all rules correctly. When in doubt, consult an attorney.

## License

MIT — see [LICENSE](LICENSE).
