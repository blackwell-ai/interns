#!/usr/bin/env python3
"""Render a digest markdown file to a clean, email-ready HTML body.

Usage: render_email.py <markdown-file>   (prints HTML to stdout)

The brain digest stays markdown (the source of truth for git); this is the
delivery-layer rendering so the email reads as formatted text, not raw `#`/`**`.
"""

import sys

from markdown_it import MarkdownIt

_CSS = """
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
         Helvetica, Arial, sans-serif; color: #1a1a1a; line-height: 1.55;
         max-width: 640px; margin: 0 auto; padding: 16px 18px; }
  h1 { font-size: 20px; margin: 0 0 6px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .05em;
       color: #6b7280; border-bottom: 1px solid #ececec; padding-bottom: 5px;
       margin: 26px 0 10px; }
  p { margin: 8px 0; }
  ul { padding-left: 18px; margin: 8px 0; }
  li { margin: 0 0 12px; }
  a { color: #2563eb; word-break: break-word; }
"""


def render(markdown_text: str) -> str:
    try:  # linkify makes bare "Source: ... https://..." URLs clickable
        body = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("linkify").render(markdown_text)
    except (ModuleNotFoundError, ImportError):  # linkify-it-py missing: still render, links just stay plain
        body = MarkdownIt("commonmark", {"html": False}).render(markdown_text)
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<style>{_CSS}</style></head><body>\n{body}\n</body></html>"
    )


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: render_email.py <markdown-file>")
    with open(sys.argv[1], encoding="utf-8") as f:
        sys.stdout.write(render(f.read()))


if __name__ == "__main__":
    main()
