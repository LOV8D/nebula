"""Inline ui/app/ (HTML + CSS + JS) and the collected data into one file.

The result opens by double-click: no server, no build tool, no network
(fonts are optional and fall back to system faces). Data travels as an
`application/json` script block, so no Python value is ever spliced into
JavaScript source — the class of bug that once broke the whole inline script.
"""
import json
from pathlib import Path

APP = Path(__file__).resolve().parent / "app"
MARKERS = ("<!--STYLE-->", "<!--DATA-->", "<!--APP-->")


def bundle(data):
    page = (APP / "index.html").read_text()
    for m in MARKERS:
        if page.count(m) != 1:
            raise SystemExit(f"ui/app/index.html must contain {m} exactly once")
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return (page
            .replace("<!--STYLE-->", "<style>\n" + (APP / "style.css").read_text() + "</style>")
            .replace("<!--DATA-->",
                     f'<script id="wt-data" type="application/json">{payload}</script>')
            .replace("<!--APP-->", "<script>\n" + (APP / "app.js").read_text() + "</script>"))
