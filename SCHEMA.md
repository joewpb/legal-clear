# Wiki Schema

## Domain
General personal knowledge base / second brain. Covers projects, learning, ideas,
research, tools, decisions, and anything worth remembering.

## Conventions
- **File names:** lowercase, hyphens, no spaces (e.g. `transformer-architecture.md`)
- **Every wiki page starts with YAML frontmatter** (see below)
- **Use `[[wikilinks]]` to link between pages** — minimum 2 outbound links per page
- **When updating a page, always bump the `updated` date**
- **Every new page must be added to `index.md`** under the correct section
- **Every action must be appended to `log.md`**
- **Provenance markers:** On pages synthesizing 3+ sources, append `^[raw/articles/source.md]`
  at the end of paragraphs whose claims come from a specific source.
- **Git commit after significant changes** — the wiki is a git repo

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | project | decision | tool
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true              # set when page has unresolved contradictions
contradictions: [other-page] # pages this one conflicts with
status: active | archived | stub | evergreen
---
```

## Tag Taxonomy

### Domain tags
- `ai-ml` — artificial intelligence, machine learning, LLMs
- `programming` — languages, patterns, algorithms, software design
- `devops` — infrastructure, deployment, CI/CD, containers
- `systems` — operating systems, networking, hardware
- `data` — databases, pipelines, analytics, visualization
- `security` — cryptography, auth, vulnerabilities, privacy
- `math` — mathematics, statistics, formal methods
- `design` — UI/UX, visual design, accessibility
- `business` — strategy, management, startups, economics
- `personal` — habits, health, productivity, learning

### Content-type tags
- `project` — active or completed projects
- `idea` — half-formed thoughts, explorations, experiments
- `decision` — architectural decisions, trade-offs, rationale
- `tool` — software, CLI, library, service
- `person` — notable individuals, researchers, creators
- `paper` — academic papers, research
- `concept` — abstract ideas, theories, frameworks
- `howto` — practical guides, tutorials, recipes
- `question` — open questions worth investigating
- `comparison` — side-by-side analysis

### Quality tags
- `evergreen` — timeless knowledge, unlikely to change
- `in-progress` — actively being developed
- `stub` — placeholder, needs expansion
- `review` — needs fact-checking or second pass

**Rule:** Every tag on a page must appear in this taxonomy. Add new tags to
this file first, then use them. This prevents tag sprawl.

## Page Thresholds
- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details, or things outside interest scope
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index

## Entity Pages
One page per notable entity (person, tool, project, company). Include:
- Overview / what it is
- Key facts and dates
- Relationships to other entities (`[[wikilinks]]`)
- Source references

## Concept Pages
One page per concept or topic. Include:
- Definition / explanation
- Current understanding
- Open questions or debates
- Related concepts (`[[wikilinks]]`)

## Project Pages
One page per active or completed project. Include:
- Goal and scope
- Key decisions and rationale
- Technologies used
- Lessons learned
- Status and next steps

## Comparison Pages
Side-by-side analyses. Include:
- What is being compared and why
- Dimensions of comparison (table format preferred)
- Verdict or synthesis
- Sources

## Decision Pages
Architectural or strategic decisions. Include:
- Context and constraints
- Options considered
- Decision and rationale
- Consequences (good and bad)

## Update Policy
When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for review: set `contested: true`

## Obsidian Integration
This directory is an Obsidian vault:
- `[[wikilinks]]` render as clickable links
- Graph View visualizes the knowledge network
- YAML frontmatter powers Dataview queries
- Clone or sync this repo to open in Obsidian on other devices
