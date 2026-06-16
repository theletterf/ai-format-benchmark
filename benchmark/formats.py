"""
Fetch and convert the benchmark document into four formats:

  annotated_md  — Elastic's rich source Markdown (frontmatter + custom directives)
  vanilla_md    — Standard Markdown: no frontmatter, no Elastic directives
  html          — Main-content HTML extracted from the live web page
  doclang       — DocTags produced by Docling (loaded from committed fixture)

The doclang fixture is generated once via benchmark/generate_fixture.py and
committed to the repo so CI never needs Docling as a runtime dependency.
"""

import os
import re
from typing import Optional

import requests
import yaml
from bs4 import BeautifulSoup

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DOCLANG_FIXTURE = os.path.join(FIXTURE_DIR, "doc.doctags")

DOC_MD_URL = (
    "https://www.elastic.co/docs/solutions/observability"
    "/get-started/opentelemetry/custom-metrics-quickstart.md"
)
DOC_HTML_URL = (
    "https://www.elastic.co/docs/solutions/observability"
    "/get-started/opentelemetry/custom-metrics-quickstart"
)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DocFormatBenchmark/1.0)"}

# Template variables used in Elastic docs
_TEMPLATE_VARS = {
    "{{product.observability}}": "Elastic Observability",
    "{{product.elasticsearch}}": "Elasticsearch",
    "{{product.kibana}}": "Kibana",
}


def _apply_template_vars(text: str) -> str:
    for k, v in _TEMPLATE_VARS.items():
        text = text.replace(k, v)
    return text


def _parse_frontmatter(text: str) -> dict:
    """
    Lenient frontmatter parser that handles unquoted colons in scalar values,
    which strict PyYAML rejects (e.g. 'title: Foo: Bar').
    Supports: scalar values, unordered lists (- item), and list-of-mappings
    (- Key: Value) at one level of indentation.
    """
    try:
        result = yaml.safe_load(text)
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        pass

    result: dict = {}
    current_key: Optional[str] = None
    current_list: Optional[list] = None

    for line in text.split("\n"):
        if not line.strip():
            continue

        # List item (indented with - )
        list_m = re.match(r"^\s+-\s+(.+)$", line)
        if list_m and current_key is not None:
            if current_list is None:
                current_list = []
                result[current_key] = current_list
            item = list_m.group(1).strip()
            # list-of-mappings: "Key: Value"
            kv_m = re.match(r"^([^:]+):\s+(.+)$", item)
            if kv_m:
                current_list.append({kv_m.group(1): kv_m.group(2)})
            else:
                current_list.append(item)
            continue

        # Top-level key (no leading whitespace)
        kv_m = re.match(r"^([\w][\w\s]*):\s*(.*)?$", line)
        if kv_m:
            current_key = kv_m.group(1).strip()
            value = (kv_m.group(2) or "").strip()
            current_list = None
            if value:
                result[current_key] = value
            # else: expect list items or sub-keys to follow
            continue

    return result


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------


def fetch_annotated_md(url: str = DOC_MD_URL) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    # decode with utf-8-sig to transparently strip any UTF-8 BOM
    text = resp.content.decode("utf-8-sig")
    return _apply_template_vars(text)


def fetch_html(url: str = DOC_HTML_URL) -> str:
    # Explicit Accept: text/html — the site does content negotiation and returns
    # Markdown for text/plain or text/markdown requests.
    resp = requests.get(url, headers={**_HEADERS, "Accept": "text/html"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Remove chrome that has nothing to do with the doc content
    for tag in soup.find_all(["nav", "header", "footer", "script", "style", "noscript"]):
        tag.decompose()

    # Prefer semantic content containers
    for selector in ["main", "article", '[role="main"]', ".content", "#content"]:
        el = soup.select_one(selector)
        if el:
            return _apply_template_vars(str(el))

    body = soup.find("body")
    return _apply_template_vars(str(body) if body else resp.text)


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _clean_inline(text: str) -> str:
    """Strip inline Markdown formatting, leaving plain text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    return text.strip()


# ---------------------------------------------------------------------------
# DocLang body processing
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)


def _process_text_segment(text: str, indent: str) -> list[str]:
    """Convert a Markdown text block (no code fences) to DocLang XML lines."""
    out: list[str] = []
    list_type: Optional[str] = None
    list_items: list[str] = []

    def _flush_list() -> None:
        nonlocal list_type, list_items
        if list_items:
            out.append(f"{indent}<list type=\"{list_type}\">")
            for item in list_items:
                clean = _xml_escape(_clean_inline(item))
                out.append(f"{indent}  <list-item>{clean}</list-item>")
            out.append(f"{indent}</list>")
        list_type = None
        list_items = []

    for raw_line in text.split("\n"):
        line = raw_line.strip()

        if not line:
            _flush_list()
            continue

        # Heading
        hm = re.match(r"^(#{1,6})\s+(.+)$", line)
        if hm:
            _flush_list()
            level = len(hm.group(1))
            content = _xml_escape(_clean_inline(hm.group(2)))
            out.append(f"{indent}<heading level=\"{level}\">{content}</heading>")
            continue

        # Ordered list
        om = re.match(r"^\d+\.\s+(.+)$", line)
        if om:
            if list_type != "ordered":
                _flush_list()
                list_type = "ordered"
            list_items.append(om.group(1))
            continue

        # Unordered list
        um = re.match(r"^[-*+]\s+(.+)$", line)
        if um:
            if list_type != "unordered":
                _flush_list()
                list_type = "unordered"
            list_items.append(um.group(1))
            continue

        # Paragraph
        _flush_list()
        content = _xml_escape(_clean_inline(line))
        out.append(f"{indent}<paragraph>{content}</paragraph>")

    _flush_list()
    return out


def _process_body_segment(text: str, indent: str) -> list[str]:
    """
    Convert a Markdown body segment (may contain fenced code blocks) to
    DocLang XML lines. Code blocks are preserved as <code-block> elements.
    """
    out: list[str] = []
    parts = _CODE_FENCE_RE.split(text)
    # split() with 2 groups yields [text, lang, code, text, lang, code, ...]
    i = 0
    while i < len(parts):
        if i % 3 == 0:
            seg = parts[i]
            if seg.strip():
                out.extend(_process_text_segment(seg, indent))
        elif i % 3 == 1:
            lang = parts[i] or "text"
            code = parts[i + 1].strip() if i + 1 < len(parts) else ""
            out.append(f"{indent}<code-block language=\"{lang}\">")
            out.append(_xml_escape(code))
            out.append(f"{indent}</code-block>")
            i += 1  # skip the code capture group
        i += 1
    return out


_STEP_RE = re.compile(r'<step\s+title="([^"]+)">(.*?)</step>', re.DOTALL)


def _convert_stepper(stepper_inner: str, indent: str) -> list[str]:
    out = [f"{indent}<section type=\"procedure\">"]
    for step_num, sm in enumerate(_STEP_RE.finditer(stepper_inner), start=1):
        title = _xml_escape(sm.group(1))
        content = sm.group(2).strip()
        out.append(f"{indent}  <step>")
        out.append(f"{indent}    <heading level=\"3\">Step {step_num}: {title}</heading>")
        out.extend(_process_body_segment(content, indent + "    "))
        out.append(f"{indent}  </step>")
    out.append(f"{indent}</section>")
    return out


# ---------------------------------------------------------------------------
# DocLang converter
# ---------------------------------------------------------------------------


def convert_to_doclang(annotated_md: str) -> str:
    """Convert Elastic annotated Markdown to DocLang XML."""
    lines = annotated_md.split("\n")

    # Extract YAML frontmatter
    frontmatter: dict = {}
    body_lines = lines
    if lines and lines[0].strip() == "---":
        try:
            end = lines.index("---", 1)
            frontmatter = _parse_frontmatter("\n".join(lines[1:end]))
            body_lines = lines[end + 1 :]
        except ValueError:
            pass

    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append('<document xmlns="https://doclang.ai/schema/v1">')

    # <head>
    out.append("  <head>")
    if frontmatter.get("title"):
        out.append(f"    <title>{_xml_escape(frontmatter['title'])}</title>")
    if frontmatter.get("description"):
        out.append(f"    <description>{_xml_escape(frontmatter['description'])}</description>")
    if frontmatter.get("products"):
        products = ", ".join(str(p) for p in frontmatter["products"])
        out.append(f'    <meta name="products" content="{_xml_escape(products)}"/>')
    if frontmatter.get("applies_to"):
        at = frontmatter["applies_to"]
        if isinstance(at, list):
            parts = []
            for item in at:
                if isinstance(item, dict):
                    parts.extend(f"{k}: {v}" for k, v in item.items())
                else:
                    parts.append(str(item))
            applies = "; ".join(parts)
        elif isinstance(at, dict):
            applies = "; ".join(f"{k}: {v}" for k, v in at.items())
        else:
            applies = str(at)
        out.append(f'    <meta name="applies_to" content="{_xml_escape(applies)}"/>')
    out.append("  </head>")

    # <body> — interleave non-stepper markdown and stepper blocks
    out.append("  <body>")

    body_text = "\n".join(body_lines)
    stepper_re = re.compile(r"<stepper>(.*?)</stepper>", re.DOTALL)
    last_end = 0

    for m in stepper_re.finditer(body_text):
        before = body_text[last_end : m.start()]
        if before.strip():
            out.extend(_process_body_segment(before, "    "))
        out.extend(_convert_stepper(m.group(1), "    "))
        last_end = m.end()

    after = body_text[last_end:]
    if after.strip():
        out.extend(_process_body_segment(after, "    "))

    out.append("  </body>")
    out.append("</document>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Plain text converter
# ---------------------------------------------------------------------------


def strip_to_vanilla_md(annotated_md: str) -> str:
    """
    Remove frontmatter and Elastic-specific directives, keep standard Markdown.

    This represents what the document would look like written in plain Markdown
    without any proprietary tooling: headings, bold, code fences, and lists are
    preserved; <stepper>/<step> are converted to ### Step N headings.
    """
    lines = annotated_md.split("\n")

    # Remove frontmatter
    body_lines = lines
    if lines and lines[0].strip() in ("---", "﻿---"):
        try:
            end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
            body_lines = lines[end + 1 :]
        except StopIteration:
            pass

    text = "\n".join(body_lines)

    # Remove <stepper> wrapper tags
    text = re.sub(r"</?stepper>\s*", "", text)

    # Convert <step title="X"> to a numbered ### heading
    _counter: list[int] = [0]

    def _step_to_heading(m: re.Match) -> str:
        _counter[0] += 1
        return f"### Step {_counter[0]}: {m.group(1)}"

    text = re.sub(r'<step\s+title="([^"]+)">', _step_to_heading, text)
    text = re.sub(r"</step>", "", text)

    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_doclang_fixture(doc_id: str) -> Optional[str]:
    """Load the committed Docling DocTags fixture for a document. Returns None if missing."""
    path = os.path.join(FIXTURE_DIR, f"{doc_id}.doctags")
    if not os.path.exists(path):
        print(f"  WARNING: doclang fixture missing for '{doc_id}' ({path}). Skipping.", flush=True)
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def get_formats_for_doc(doc: dict) -> dict[str, str]:
    """
    Return benchmark formats for a document config dict.
    doclang is loaded from the committed fixture (skipped if not present).
    """
    md_url = doc["md_url"]
    html_url = doc["html_url"]
    doc_id = doc["id"]

    print(f"  Fetching annotated_md...", flush=True)
    annotated_md = fetch_annotated_md(md_url)

    print(f"  Fetching html...", flush=True)
    html = fetch_html(html_url)

    print(f"  Loading doclang fixture...", flush=True)
    doclang = load_doclang_fixture(doc_id)

    print(f"  Converting → vanilla_md...", flush=True)
    vanilla_md = strip_to_vanilla_md(annotated_md)

    formats = {
        "annotated_md": annotated_md,
        "vanilla_md": vanilla_md,
        "html": html,
    }
    if doclang is not None:
        formats["doclang"] = doclang
    return formats


# ---------------------------------------------------------------------------
# Backward-compatible alias (kept for local testing / generate_fixture.py)
# ---------------------------------------------------------------------------

def get_all_formats(
    md_url: str = DOC_MD_URL,
    html_url: str = DOC_HTML_URL,
) -> dict[str, str]:
    doc = {"id": "doc", "md_url": md_url, "html_url": html_url}
    return get_formats_for_doc(doc)
