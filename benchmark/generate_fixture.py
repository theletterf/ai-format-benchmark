#!/usr/bin/env python3
"""
Generate benchmark/fixtures/<doc_id>.doctags for all benchmark documents.

Uses Docling (not a runtime dependency) to produce official DocTags
representations. Commit the output; the benchmark reads it directly
without requiring Docling in CI.

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

from benchmark.documents import DOCUMENTS
from benchmark.formats import FIXTURE_DIR, fetch_html


def generate_for_doc(doc: dict) -> None:
    fixture_path = os.path.join(FIXTURE_DIR, f"{doc['id']}.doctags")
    print(f"\n── {doc['title']} ──")
    print(f"   Fetching HTML from {doc['html_url']}...")
    html_content = fetch_html(doc["html_url"])
    print(f"   {len(html_content):,} chars of main-content HTML")

    print("   Converting with Docling...")
    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
    stream = DocumentStream(name="doc.html", stream=io.BytesIO(html_content.encode()))
    result = converter.convert(stream)
    doctags = result.document.export_to_doctags()
    print(f"   {len(doctags):,} chars of DocTags")

    os.makedirs(FIXTURE_DIR, exist_ok=True)
    with open(fixture_path, "w", encoding="utf-8") as fh:
        fh.write(doctags)
    print(f"   Written → {fixture_path}")


def main() -> None:
    for doc in DOCUMENTS:
        generate_for_doc(doc)
    print("\nAll fixtures generated.")


if __name__ == "__main__":
    main()
