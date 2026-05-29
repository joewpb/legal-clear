# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-05-28] create | Wiki initialized
- Domain: General personal knowledge base / second brain
- Structure created with SCHEMA.md, index.md, log.md
- Path: /home/hermes/wiki
- Tag taxonomy: 20 tags across domain, content-type, and quality categories
- Git repo initialized for versioning

## [2026-05-28] ingest | Florida court forms research — Legal Clear project
- Researched Florida court system structure: 20 circuits, 67 counties, Supreme Court forms
- Key finding: Supreme Court forms + DIY Florida cover 80%+ of pro se needs
- Created comprehensive JSON dataset: 13 case types, 20 circuits, 67 counties, 10 centralized sources
  - raw/articles/florida-court-forms-dataset.json
- Created wiki pages:
  - projects/legal-clear.md — project overview and 3-phase plan
  - entities/florida-court-forms-directory.md — dataset documentation
  - entities/diy-florida.md — DIY Florida tool overview
  - concepts/florida-court-system.md — court structure for pro se litigants
- Updated index.md: 5 pages total
- Three-phase strategy: (1) Smart Directory ✓, (2) AI Form Finder, (3) Full Platform
