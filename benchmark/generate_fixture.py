#!/usr/bin/env python3
"""
Generate benchmark/fixtures/doc.doctags from the live Elastic docs page.

Uses Docling (not a runtime dependency) to produce an official DocTags
representation of the document. Commit the output; the benchmark reads it
directly without requiring Docling in CI.

Usage:
    pip install docling
    python benchmark/generate_fixture.py
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import DocumentStream
    from docling.document_converter import DocumentConverter
except ImportError:
    sys.exit("Docling is not installed. Run: pip install docling")

from benchmark.formats import DOC_HTML_URL, fetch_html

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "doc.doctags")


def main() -> None:
    print(f"Fetching cleaned HTML from {DOC_HTML_URL}...")
    html_content = fetch_html(DOC_HTML_URL)
    print(f"  {len(html_content):,} chars of main-content HTML")

    print("Converting with Docling (export_to_doctags)...")
    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
    stream = DocumentStream(name="doc.html", stream=io.BytesIO(html_content.encode()))
    result = converter.convert(stream)
    doctags = result.document.export_to_doctags()
    print(f"  {len(doctags):,} chars of DocTags")

    os.makedirs(os.path.dirname(FIXTURE_PATH), exist_ok=True)
    with open(FIXTURE_PATH, "w", encoding="utf-8") as fh:
        fh.write(doctags)

    print(f"Written → {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
