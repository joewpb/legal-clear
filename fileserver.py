#!/usr/bin/env python3
"""
File Browser Server — serves a web UI for navigating and previewing files.
No dependencies beyond Python stdlib. Run: python3 fileserver.py
"""

import json
import mimetypes
import os
import re
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

ROOT_DIR = Path("/home/hermes/wiki")
PORT = 8099
HOST = "0.0.0.0"

# Markdown renderer (basic, no external deps)
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
_MD_BOLD_RE = re.compile(r'\*\*([^*]+)\*\*')
_MD_ITALIC_RE = re.compile(r'\*([^*]+)\*')
_MD_CODE_RE = re.compile(r'`([^`]+)`')
_MD_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_MD_HR_RE = re.compile(r'^---$', re.MULTILINE)
_MD_LIST_RE = re.compile(r'^(\s*[-*+]\s+)(.+)$', re.MULTILINE)
_MD_NUMLIST_RE = re.compile(r'^(\s*\d+\.\s+)(.+)$', re.MULTILINE)
_MD_CODEBLOCK_RE = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)


def render_markdown(text: str) -> str:
    """Basic markdown -> HTML without external deps."""
    html = text
    # Code blocks first (before inline replacements)
    html = _MD_CODEBLOCK_RE.sub(
        lambda m: f'<pre><code class="language-{m.group(1)}">{m.group(2)}</code></pre>',
        html)
    # Headings
    html = _MD_HEADING_RE.sub(
        lambda m: f'<h{len(m.group(1))}>{m.group(2)}</h{len(m.group(1))}>',
        html)
    # HR
    html = _MD_HR_RE.sub('<hr>', html)
    # Lists
    html = _MD_LIST_RE.sub(r'<li>\2</li>', html)
    html = _MD_NUMLIST_RE.sub(r'<li>\2</li>', html)
    # Wrap consecutive <li> in <ul>
    html = re.sub(r'(<li>.*?</li>\n?)+', r'<ul>\g<0></ul>', html)
    # Inline
    html = _MD_BOLD_RE.sub(r'<strong>\1</strong>', html)
    html = _MD_ITALIC_RE.sub(r'<em>\1</em>', html)
    html = _MD_CODE_RE.sub(r'<code>\1</code>', html)
    html = _MD_LINK_RE.sub(r'<a href="\2">\1</a>', html)
    # Paragraphs
    paragraphs = html.split('\n\n')
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<h') or p.startswith('<ul') or p.startswith('<pre') or p.startswith('<hr'):
            result.append(p)
        else:
            result.append(f'<p>{p}</p>')
    return '\n'.join(result)


class FileBrowserHandler(SimpleHTTPRequestHandler):
    """Custom handler with API endpoints for file browsing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        # API: list directory
        if path == '/api/list':
            self._api_list(parse_qs(parsed.query))
            return

        # API: render markdown
        if path == '/api/markdown':
            self._api_markdown(parse_qs(parsed.query))
            return

        # Serve the file browser UI at root
        if path == '/' or path == '':
            self._serve_ui()
            return

        # Serve files normally
        super().do_GET()

    def _api_list(self, params):
        dir_path = params.get('path', ['.'])[0]
        # Security: don't escape root
        full_path = (ROOT_DIR / dir_path).resolve()
        if not str(full_path).startswith(str(ROOT_DIR.resolve())):
            self._json({'error': 'Access denied'}, 403)
            return

        if not full_path.is_dir():
            self._json({'error': 'Not a directory'}, 400)
            return

        items = []
        try:
            for entry in sorted(full_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
                if entry.name.startswith('.') and entry.name != '.gitignore':
                    continue
                rel = str(entry.relative_to(ROOT_DIR))
                stat = entry.stat()
                items.append({
                    'name': entry.name,
                    'path': rel,
                    'is_dir': entry.is_dir(),
                    'size': stat.st_size if not entry.is_dir() else 0,
                    'modified': time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime)),
                })
        except PermissionError:
            self._json({'error': 'Permission denied'}, 403)
            return

        self._json({'path': dir_path, 'items': items})

    def _api_markdown(self, params):
        file_path = params.get('path', ['.'])[0]
        full_path = (ROOT_DIR / file_path).resolve()
        if not str(full_path).startswith(str(ROOT_DIR.resolve())):
            self._json({'error': 'Access denied'}, 403)
            return
        if not full_path.is_file():
            self._json({'error': 'Not a file'}, 400)
            return
        try:
            text = full_path.read_text()
            html = render_markdown(text)
            self._json({'html': html})
        except Exception as e:
            self._json({'error': str(e)}, 500)

    def _serve_ui(self):
        ui_path = ROOT_DIR / 'file-browser.html'
        if ui_path.exists():
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(ui_path.read_bytes())
        else:
            self._json({'error': 'UI not found'}, 500)

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # quiet


if __name__ == '__main__':
    server = HTTPServer((HOST, PORT), FileBrowserHandler)
    print(f"File browser at http://{HOST}:{PORT}")
    print(f"Serving: {ROOT_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
