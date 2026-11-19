"""Fills invoice.html with jinja2, the same template the API fills, and writes compare/out/invoice.html.

The libraries in this comparison don't have a template language, so they all get this finished HTML.
"""

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "out"
sys.path.insert(0, str(ROOT))

from invoice_data import load_invoice  # noqa: E402


def build() -> Path:
    env = Environment(loader=FileSystemLoader(ROOT), autoescape=select_autoescape(["html"]))
    html = env.get_template("invoice.html").render(**load_invoice())
    OUT.mkdir(exist_ok=True)
    target = OUT / "invoice.html"
    target.write_text(html, encoding="utf-8")
    return target


if __name__ == "__main__":
    print(build())
