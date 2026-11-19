"""Renders the same invoice with xhtml2pdf, WeasyPrint, pdfkit (wkhtmltopdf) and Playwright.

Every library gets the same finished HTML (compare/build_html.py) and adds page numbers in its own way, the
way its documentation describes. A second, tiny page checks whether the library runs JavaScript.
Results go to compare/out: one PDF and one image of page 1 per library, plus results.json.

Runs in GitHub Actions (.github/workflows/compare.yml); see compare/README.md to run it yourself.
"""

import json
import platform
import shutil
import subprocess
import time
import traceback
from importlib.metadata import version
from pathlib import Path

import pypdfium2 as pdfium

from build_html import OUT, build

FOOTER_LEFT = "Northwind Outdoor Supply · Invoice INV-2026-0418"
JS_TEST = """<!DOCTYPE html><html><body style="font: 16pt sans-serif">
<p>JavaScript ran: <b id="js">no</b></p>
<script>document.getElementById("js").textContent = "yes";</script>
</body></html>"""


def render_xhtml2pdf(html: str, target: Path) -> None:
    from xhtml2pdf import pisa

    # xhtml2pdf needs its own frame syntax and <pdf:pagenumber> tags for page numbers.
    frame_css = """<style>
      @page { size: letter; margin: 16mm 16mm 22mm 16mm;
        @frame footer { -pdf-frame-content: pagefooter; bottom: 8mm; margin-left: 16mm; margin-right: 16mm; height: 8mm; } }
    </style>"""
    footer = f'<div id="pagefooter" style="font-size: 7pt">{FOOTER_LEFT} · Page <pdf:pagenumber> of <pdf:pagecount></div>'
    html = html.replace("</head>", frame_css + "</head>").replace("<body>", "<body>" + footer)
    with target.open("wb") as f:
        result = pisa.CreatePDF(html, dest=f)
    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} errors")


def render_weasyprint(html: str, target: Path) -> None:
    from weasyprint import CSS, HTML

    # Page size, margins and page numbers through CSS paged media (@page margin boxes).
    page_css = CSS(string=f"""
      @page {{ size: Letter; margin: 16mm 16mm 20mm 16mm;
        @bottom-left {{ content: "{FOOTER_LEFT}"; font: 7pt Arial, sans-serif; }}
        @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font: 7pt Arial, sans-serif; }} }}
    """)
    HTML(string=html).write_pdf(target, stylesheets=[page_css])


def render_pdfkit(html: str, target: Path) -> None:
    import pdfkit

    options = {
        "page-size": "Letter",
        "margin-top": "16mm",
        "margin-right": "16mm",
        "margin-bottom": "20mm",
        "margin-left": "16mm",
        "encoding": "UTF-8",
        "footer-left": FOOTER_LEFT,
        "footer-right": "Page [page] of [topage]",
        "footer-font-size": "7",
        "quiet": "",
    }
    pdfkit.from_string(html, str(target), options=options)


def render_playwright(html: str, target: Path) -> None:
    from playwright.sync_api import sync_playwright

    footer = (
        '<div style="font-size: 7pt; width: 100%; margin: 0 16mm; display: flex; justify-content: space-between">'
        f'<span>{FOOTER_LEFT}</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>'
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(
            path=str(target),
            format="Letter",
            margin={"top": "16mm", "right": "16mm", "bottom": "20mm", "left": "16mm"},
            print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=footer,
        )
        browser.close()


LIBRARIES = {
    "xhtml2pdf": (render_xhtml2pdf, "xhtml2pdf"),
    "weasyprint": (render_weasyprint, "weasyprint"),
    "pdfkit": (render_pdfkit, "pdfkit"),
    "playwright": (render_playwright, "playwright"),
}


def page_count(pdf: Path) -> int:
    return len(pdfium.PdfDocument(str(pdf)))


def pdf_text(pdf: Path) -> str:
    doc = pdfium.PdfDocument(str(pdf))
    return " ".join(page.get_textpage().get_text_range() for page in doc)


def save_page_images(pdf: Path, stem: str) -> list[str]:
    names = []
    for i, page in enumerate(pdfium.PdfDocument(str(pdf)), 1):
        name = f"{stem}-page-{i}.webp"
        page.render(scale=1.5).to_pil().save(OUT / name, "WEBP", quality=82, method=6)
        names.append(name)
    return names


def wkhtmltopdf_version() -> str:
    exe = shutil.which("wkhtmltopdf")
    if not exe:
        return "not installed"
    return subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.strip()


def chromium_size_mb() -> float | None:
    cache = Path.home() / ".cache" / "ms-playwright"
    if not cache.exists():
        return None
    size = sum(f.stat().st_size for f in cache.rglob("*") if f.is_file())
    return round(size / 1_000_000, 1)


def main() -> None:
    html = build().read_text(encoding="utf-8")
    results = {
        "python": platform.python_version(),
        "system": platform.platform(),
        "wkhtmltopdf": wkhtmltopdf_version(),
        "playwright_browsers_mb": chromium_size_mb(),
        "libraries": {},
    }
    for name, (render, package) in LIBRARIES.items():
        entry = {"version": version(package)}
        target = OUT / f"{name}.pdf"
        try:
            started = time.perf_counter()
            render(html, target)
            entry["seconds"] = round(time.perf_counter() - started, 2)
            entry["pages"] = page_count(target)
            entry["has_page_numbers"] = "Page 1 of" in " ".join(pdf_text(target).split())
            entry["images"] = save_page_images(target, name)
        except Exception as error:  # record the failure and keep going with the next library
            entry["error"] = f"{type(error).__name__}: {error}"
            entry["traceback"] = traceback.format_exc()

        js_target = OUT / f"{name}-js.pdf"
        try:
            render(JS_TEST, js_target)
            entry["runs_javascript"] = "JavaScript ran: yes" in pdf_text(js_target)
        except Exception as error:
            entry["runs_javascript"] = f"error: {error}"
        results["libraries"][name] = entry
        print(name, {k: v for k, v in entry.items() if k != "traceback"})

    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
