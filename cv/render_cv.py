"""Render Sanan_Shahverdi_CV.md to a styled A4 PDF (and HTML) with headless Chromium.

    python3 cv/render_cv.py        # from the repository root; needs `npm ci` for Puppeteer
"""

import subprocess
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "Sanan_Shahverdi_CV.md"
HTML = HERE / "Sanan_Shahverdi_CV.html"
PDF = HERE / "Sanan_Shahverdi_CV.pdf"

STYLE = """
@page { size: A4; margin: 14mm 15mm 13mm; }
:root { --ink: #16202a; --muted: #56616d; --accent: #1f6f5c; --line: #d9dfe3; }
* { box-sizing: border-box; }
body { margin: 0; color: var(--ink); font: 9.6pt/1.42 "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
h1 { font-size: 23pt; letter-spacing: -0.02em; margin: 0; line-height: 1.1; }
h1 + p { margin: 3pt 0 2pt; font-size: 11.5pt; color: var(--accent); }
h1 + p + p { margin: 0 0 8pt; color: var(--muted); font-size: 9pt; }
h2 { font-size: 10.5pt; text-transform: uppercase; letter-spacing: 0.1em; color: var(--accent);
     border-bottom: 1px solid var(--line); padding-bottom: 2pt; margin: 11pt 0 5pt; break-after: avoid; }
h3 { font-size: 10.2pt; margin: 7pt 0 2pt; break-after: avoid; }
p { margin: 0 0 4pt; }
ul { margin: 0 0 3pt; padding-left: 13pt; }
li { margin: 0 0 2pt; }
li, h3 { break-inside: avoid; }
a { color: inherit; text-decoration: none; }
strong { font-weight: 650; }
"""


def clean_metadata() -> None:
    """Replace renderer metadata with neutral document information."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    writer.append(PdfReader(PDF))  # copies pages only, not the renderer's document information
    writer.add_metadata({"/Title": "Sanan Shahverdi - CV", "/Author": "Sanan Shahverdi", "/Producer": ""})
    with PDF.open("wb") as handle:
        writer.write(handle)


def main() -> None:
    body = markdown.markdown(SOURCE.read_text(encoding="utf-8"), extensions=["sane_lists"])
    # Skills lines are separated by single line breaks in Markdown; keep them on separate lines.
    body = body.replace("\n<strong>", "<br><strong>")
    HTML.write_text(f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Sanan Shahverdi · CV</title>"
                    f"<style>{STYLE}</style></head><body>{body}</body></html>", encoding="utf-8")
    script = f"""
import puppeteer from 'puppeteer'
const browser = await puppeteer.launch({{ headless: true, args: ['--no-sandbox'] }})
const page = await browser.newPage()
await page.goto('file://{HTML}', {{ waitUntil: 'load' }})
await page.pdf({{ path: '{PDF}', format: 'A4', printBackground: true, preferCSSPageSize: true }})
await browser.close()
"""
    subprocess.run(["node", "--input-type=module", "-e", script], check=True, cwd=HERE.parent)
    clean_metadata()
    print(f"wrote {PDF.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
