#!/usr/bin/env python3
"""
fl_forms_crawler.py — Camofox Edition
--------------------------------------
Crawl Florida court forms using Camofox (anti-detection Firefox browser)
instead of Playwright Chromium. No extra browser install needed.

Three jobs:
  1. VALIDATE   — check every URL in an existing index, flag dead links
  2. CRAWL      — render each source page via Camofox, harvest every form link
  3. CONSOLIDATE — download, hash, DEDUPE, emit canonical index + PDF archive

Usage:
    python3 fl_forms_crawler.py validate --index fl_courts_forms_index.json
    python3 fl_forms_crawler.py crawl --sources sources.json
    python3 fl_forms_crawler.py all --index fl_courts_forms_index.json --sources sources.json
"""

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CAMOFOX_URL = os.environ.get("CAMOFOX_URL", "http://localhost:9377")
FORMS_DIR = Path("/home/hermes/wiki/raw/forms")

USER_AGENT = (
    "FL-Court-Forms-Indexer/1.0 (public-records link indexer; "
    "contact: hermes@localhost)"
)
PER_DOMAIN_DELAY = 1.5       # seconds between hits to the same domain
GLOBAL_CONCURRENCY = 2       # how many tabs open at once in Camofox
NAV_TIMEOUT = 45             # seconds for page load
PAGE_SETTLE = 3.0            # extra wait after navigation for lazy JS
DOWNLOAD_TIMEOUT = 60        # seconds for PDF/DOCX download

# Florida form-number patterns: 12.901(a), 1.997, 12.902(f)(1), DH 430, etc.
FORM_NUM_RE = re.compile(
    r"\b(\d{1,2}\.\d{3}(?:\([a-z0-9]+\))*|[A-Z]{2,4}[\s\-]?\d{2,4})\b"
)

# ---------------------------------------------------------------------------
# robots + rate limiting
# ---------------------------------------------------------------------------

_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
_last_hit: dict[str, float] = {}


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower()


async def _allowed(url: str) -> bool:
    dom = _domain(url)
    if dom not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{urlparse(url).scheme}://{dom}/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots_cache[dom] = rp
    rp = _robots_cache[dom]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


async def _throttle(url: str):
    dom = _domain(url)
    now = time.monotonic()
    wait = PER_DOMAIN_DELAY - (now - _last_hit.get(dom, 0))
    if wait > 0:
        await asyncio.sleep(wait)
    _last_hit[dom] = time.monotonic()


# ---------------------------------------------------------------------------
# Camofox API helpers
# ---------------------------------------------------------------------------

class CamofoxClient:
    """Thin async wrapper around Camofox REST API."""

    def __init__(self, base_url: str = CAMOFOX_URL, user_id: str = "fl-crawler", session_key: str = "crawl-001"):
        self.base = base_url.rstrip("/")
        self.user_id = user_id
        self.session_key = session_key
        self._client = httpx.AsyncClient(timeout=NAV_TIMEOUT)

    async def new_tab(self, url: str) -> str | None:
        """Open a tab, navigate to URL, return tabId."""
        try:
            resp = await self._client.post(
                f"{self.base}/tabs",
                json={"userId": self.user_id, "sessionKey": self.session_key, "url": url},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tabId")
            print(f"  [camofox] new_tab HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  [camofox] new_tab error: {e}")
        return None

    async def get_links(self, tab_id: str) -> list[dict]:
        """Get all links from the current page."""
        try:
            resp = await self._client.get(
                f"{self.base}/tabs/{tab_id}/links",
                params={"userId": self.user_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("links", [])
        except Exception as e:
            print(f"  [camofox] get_links error: {e}")
        return []

    async def close_tab(self, tab_id: str):
        try:
            await self._client.delete(
                f"{self.base}/tabs/{tab_id}",
                params={"userId": self.user_id},
            )
        except Exception:
            pass

    async def health(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base}/health")
            return resp.status_code == 200 and resp.json().get("ok") is True
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()


async def download_file(client: httpx.AsyncClient, url: str, dest: Path) -> tuple[int, str]:
    """Download a file directly (PDFs are static, no browser needed)."""
    try:
        resp = await client.get(url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True)
        if resp.status_code == 200:
            body = resp.content
            dest.write_bytes(body)
            file_hash = hashlib.sha256(body).hexdigest()
            return 200, file_hash
        return resp.status_code, ""
    except Exception as e:
        return -1, f"ERR:{type(e).__name__}"


# ---------------------------------------------------------------------------
# extraction helpers (unchanged from original)
# ---------------------------------------------------------------------------

def guess_form_number(text: str, href: str) -> str | None:
    for blob in (text or "", Path(urlparse(href).path).name):
        m = FORM_NUM_RE.search(blob)
        if m:
            return m.group(1).strip()
    return None


def is_form_link(href: str, text: str) -> bool:
    low = href.lower()
    if low.endswith(".pdf") or low.endswith(".doc") or low.endswith(".docx"):
        return True
    return bool(re.search(r"\bform\b|petition|motion|summons|complaint", (text or ""), re.I))


# ---------------------------------------------------------------------------
# VALIDATE
# ---------------------------------------------------------------------------

async def validate_index(index_path: Path, out_dir: Path):
    data = json.loads(index_path.read_text())
    rows = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent": USER_AGENT}) as client:
        for entry in data:
            url = entry.get("url")
            if not url:
                continue
            await _throttle(url)
            status, final = 0, url
            try:
                resp = await client.get(url)
                status = resp.status_code
                final = str(resp.url)
            except Exception as e:
                status = -1
                final = f"ERR:{type(e).__name__}"

            verdict = ("ok" if status == 200 else
                       "moved" if final != url and status == 200 else
                       "dead" if status in (404, 410, -1) else
                       "challenge" if status in (403, 406, 429) else "check")
            rows.append({
                "form_number": entry.get("form_number"),
                "name": entry.get("name", ""),
                "url": url,
                "status": status,
                "final_url": final,
                "verdict": verdict,
            })
            print(f"[{verdict:9}] {status:>4}  {entry.get('form_number') or '?':<12} {url}")

    report = out_dir / "dead_links_report.csv"
    with report.open("w", newline="") as fh:
        fieldnames = ["form_number", "name", "url", "status", "final_url", "verdict"]
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    dead = [r for r in rows if r["verdict"] in ("dead", "challenge", "check")]
    print(f"\nValidated {len(rows)} links. {len(dead)} need attention. -> {report}")
    return rows


# ---------------------------------------------------------------------------
# CRAWL
# ---------------------------------------------------------------------------

async def crawl_source(camo: CamofoxClient, source: dict, sem: asyncio.Semaphore):
    county = source.get("county", "STATE")
    found = []
    async with sem:
        for entry in source.get("entry_urls", []):
            if not await _allowed(entry):
                print(f"[robots]  skipping (disallowed): {entry}")
                continue

            await _throttle(entry)
            print(f"[crawl]   {county}: opening {entry}")

            tab_id = await camo.new_tab(entry)
            if not tab_id:
                print(f"[error]   {county}: failed to open tab for {entry}")
                continue

            await asyncio.sleep(PAGE_SETTLE)

            links = await camo.get_links(tab_id)
            for link in links:
                href = link.get("href", "")
                text = link.get("text", "")
                if not href:
                    continue
                full_url = urljoin(entry, href)
                if not is_form_link(full_url, text):
                    continue
                found.append({
                    "county": county,
                    "name": (text or "")[:200] or Path(urlparse(full_url).path).name,
                    "form_number": guess_form_number(text, full_url),
                    "url": full_url,
                    "source_url": entry,
                })

            await camo.close_tab(tab_id)
            print(f"[crawl]   {county}: {len(found)} candidate links from {entry}")

    return found


async def crawl_sources(sources_path: Path, out_dir: Path):
    sources = json.loads(sources_path.read_text())
    pdf_dir = out_dir / "downloaded_pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(GLOBAL_CONCURRENCY)

    camo = CamofoxClient()
    if not await camo.health():
        print("ERROR: Camofox is not reachable at", CAMOFOX_URL)
        print("Start it with: systemctl --user start camofox.service")
        sys.exit(1)
    print(f"Camofox healthy — engine: {camo.base}")

    # Phase 1: crawl all sources
    results = await asyncio.gather(
        *(crawl_source(camo, s, sem) for s in sources)
    )
    candidates = [c for group in results for c in group]
    print(f"\nCrawled {len(sources)} sources -> {len(candidates)} candidate forms")

    # Phase 2: download + hash each candidate
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True,
                                 headers={"User-Agent": USER_AGENT}) as dl_client:
        downloaded = []
        for c in candidates:
            await _throttle(c["url"])
            url = c["url"]
            ext = (Path(urlparse(url).path).suffix or "").lower().lstrip(".")
            fmt = ext if ext in ("pdf", "doc", "docx") else "pdf"
            orig_name = Path(urlparse(url).path).name or f"form.{fmt}"
            tmp_path = pdf_dir / f"_tmp_{orig_name}"

            print(f"[dl]      {c.get('form_number') or '?'} <- {url[:100]}")
            status, file_hash = await download_file(dl_client, url, tmp_path)

            if status == 200:
                size = tmp_path.stat().st_size
                final_name = f"{file_hash[:16]}_{orig_name}"
                final_path = pdf_dir / final_name
                tmp_path.rename(final_path)

                c["http_status"] = 200
                c["file_hash"] = file_hash
                c["bytes"] = size
                c["format"] = fmt
                c["archived_path"] = str(final_path)
                downloaded.append(c)
                print(f"  ✓ {size:,} bytes -> {final_name}")
            else:
                c["http_status"] = status
                downloaded.append(c)
                tmp_path.unlink(missing_ok=True)
                print(f"  ✗ HTTP {status}")

    await camo.close()

    # CONSOLIDATE: dedupe by form_number + file_hash
    forms: dict[tuple, dict] = {}
    for c in downloaded:
        if c.get("http_status") != 200:
            continue
        fn = c.get("form_number")
        key = (fn,) if fn else (c.get("county"), c.get("name"))
        rec = forms.get(key)
        if rec is None:
            rec = {
                "county": c.get("county"),
                "name": c.get("name"),
                "form_number": fn,
                "source_url": c.get("source_url"),
                "files": [],
            }
            forms[key] = rec

        fmt = c.get("format", "pdf")
        if any(f.get("file_hash") == c.get("file_hash") for f in rec["files"]):
            continue
        if any(f.get("format") == fmt for f in rec["files"]):
            continue
        rec["files"].append({
            "format": fmt,
            "url": c.get("url"),
            "file_hash": c.get("file_hash"),
            "bytes": c.get("bytes"),
            "archived_path": c.get("archived_path"),
        })

    canonical = list(forms.values())
    for rec in canonical:
        fmts = {f["format"] for f in rec["files"]}
        if {"pdf", "docx"} <= fmts or {"pdf", "doc"} <= fmts:
            hashes = {f["format"]: f["file_hash"] for f in rec["files"]}
            rec["format_revision_flag"] = len(set(hashes.values())) > 1

    out = out_dir / "fl_forms_index_crawled.json"
    out.write_text(json.dumps(canonical, indent=2))
    flagged = sum(1 for r in canonical if r.get("format_revision_flag"))
    print(f"\nCrawled {len(candidates)} candidates -> {len(canonical)} canonical forms")
    print(f"{flagged} form(s) have pdf/docx hash mismatch (possible revision drift)")
    print(f"Index: {out}\nPDFs:  {pdf_dir}")
    return canonical


# ---------------------------------------------------------------------------
# sources.json template
# ---------------------------------------------------------------------------

SOURCES_TEMPLATE = [
    {
        "county": "STATE",
        "entry_urls": [
            "https://www.flcourts.gov/Resources-Services/Court-Improvement/Family-Courts/Family-Law-Forms"
        ],
    },
    {
        "county": "EXAMPLE_COUNTY",
        "entry_urls": [
            "https://REPLACE-with-real-clerk-forms-page"
        ],
    },
]


def ensure_sources(path: Path):
    if not path.exists():
        path.write_text(json.dumps(SOURCES_TEMPLATE, indent=2))
        print(f"Wrote template -> {path}\nFill in the county entry URLs, then re-run.")
        return False
    return True


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Index FL court forms via Camofox")
    p.add_argument("mode", choices=["validate", "crawl", "all"])
    p.add_argument("--index", type=Path, help="existing forms index to validate")
    p.add_argument("--sources", type=Path, default=Path("sources.json"))
    p.add_argument("--out", type=Path, default=Path("./out"))
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.mode in ("validate", "all"):
        if not args.index:
            sys.exit("--index required for validate")
        asyncio.run(validate_index(args.index, args.out))

    if args.mode in ("crawl", "all"):
        if not ensure_sources(args.sources):
            return
        asyncio.run(crawl_sources(args.sources, args.out))


if __name__ == "__main__":
    main()
