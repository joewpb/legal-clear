---
title: Legal Clear
created: 2026-05-28
updated: 2026-05-28
type: project
tags: [programming, personal, project, ai-ml]
sources: []
confidence: high
status: active
---

# Legal Clear

An AI-powered tool to help people who can't afford an attorney navigate the
Florida court system on their own (pro se). Explains complicated legal terms in
plain English and directs users to the correct court forms.

## Problem

Florida allows pro se representation, but:
- No centralized database of court forms across 67 counties
- Forms are spread across 4 different layers (Supreme Court, DIY Florida, 20
  circuits, 67 county clerks)
- Legal language is inaccessible to non-lawyers
- People don't know what forms they need or how to fill them out

## Approach

Three-phase plan:

### Phase 1: Smart Directory (done)
Comprehensive [[florida-court-forms-directory]] mapping case types to forms.
JSON dataset at `raw/articles/florida-court-forms-dataset.json`.

### Phase 2: AI Form Finder (next)
Interview-based system that asks about the user's situation and routes them to
the right forms. LLM-powered plain-English explanations of each form.

### Phase 3: Full Platform
Web application with form finder, plain-English walkthroughs, and direct links
to official sources. Does NOT host forms (avoids liability) — always points to
official sources.

## Key Resources
- [[florida-court-system]]
- [[diy-florida]]
- [[florida-court-forms-directory]]
