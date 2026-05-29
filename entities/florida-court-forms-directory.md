---
title: Florida Court Forms Directory
created: 2026-05-28
updated: 2026-05-28
type: project
tags: [programming, personal, project]
sources: [raw/articles/florida-court-forms-dataset.json]
confidence: high
status: active
---

# Florida Court Forms Directory

Part of the [[legal-clear]] project. A comprehensive directory mapping every major
pro se (self-represented) case type in Florida to the correct official court forms,
DIY Florida interviews, circuit-specific resources, and county clerk websites.

## What It Solves

Florida allows pro se representation, but there is no centralized database of forms.
The forms exist in 4 places:

1. **Florida Supreme Court** (flcourts.gov) — statewide family law and small claims forms
2. **DIY Florida** (myflcourtaccess.com) — interactive interview-based form builder
3. **20 Circuit Courts** — circuit-specific self-help pages and local forms
4. **67 County Clerks** — county-specific fee schedules and procedural forms

This directory maps case types → forms across all sources.

## Structure

- **`raw/articles/florida-court-forms-dataset.json`** — complete machine-readable dataset
- 13 case types covered: divorce, custody, child support, domestic violence,
  eviction (landlord + tenant), small claims, name change, probate (small + full),
  guardianship, expungement
- 20 circuits with self-help URLs
- 67 counties with clerk website URLs
- 10 centralized resource links

## Key Finding

**You don't need to scrape 67 counties.** The Supreme Court forms + DIY Florida
already cover 80%+ of pro se needs. The real product is not a form repository —
it's a decision engine that routes people to the right forms and explains them
in plain English.

See also: [[legal-clear]], [[florida-court-system]], [[diy-florida]]
