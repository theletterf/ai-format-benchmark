"""
Generate a Markdown report from benchmark results JSON.

Usage (standalone):
    python benchmark/report.py results.json

Usage (as module):
    from benchmark.report import generate_report
    md = generate_report(results_dict)
"""

import json
import sys

_SCORE_ICON = {2: "✅", 1: "⚠️", 0: "❌"}


def _efficiency_rank(formats: dict) -> str:
    """Format name with best tokens-per-correct-point."""
    def tpp(fd):
        score = fd["total_score"]
        return fd["token_count"] / score if score > 0 else float("inf")
    return min(formats.items(), key=lambda kv: tpp(kv[1]))[0]


def generate_report(results: dict) -> str:
    model = results["model"]
    run_id = results["run_id"]
    doc_url = results["doc_url"]
    formats: dict = results["formats"]
    fmt_names = list(formats.keys())
    num_tasks = len(list(formats.values())[0]["tasks"])

    lines: list[str] = []

    lines += [
        "# Doc Format Benchmark",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Run** | `{run_id}` |",
        f"| **Model** | `{model}` |",
        f"| **Document** | {doc_url} |",
        f"| **Formats** | {', '.join(f'`{f}`' for f in fmt_names)} |",
        f"| **Tasks** | {num_tasks} (scored 0–2 each by LLM judge) |",
        "",
    ]

    # ------------------------------------------------------------------
    # Token consumption
    # ------------------------------------------------------------------
    min_tokens = min(fd["token_count"] for fd in formats.values())
    lines += [
        "## Token Consumption",
        "",
        "Input tokens when answering a representative question (lower = cheaper RAG).",
        "",
        "| Format | Input tokens | vs smallest |",
        "|--------|-------------:|------------:|",
    ]
    for fn, fd in sorted(formats.items(), key=lambda kv: kv[1]["token_count"]):
        tc = fd["token_count"]
        if tc == min_tokens:
            delta = "—"
        else:
            delta = f"+{round((tc / min_tokens - 1) * 100)}%"
        lines.append(f"| `{fn}` | {tc:,} | {delta} |")
    lines.append("")

    # ------------------------------------------------------------------
    # Accuracy summary
    # ------------------------------------------------------------------
    lines += [
        "## Evaluation Accuracy",
        "",
        "| Format | Score | Accuracy | Tokens / correct pt ↓ |",
        "|--------|------:|---------:|----------------------:|",
    ]
    for fn, fd in sorted(formats.items(), key=lambda kv: -kv[1]["accuracy"]):
        score = fd["total_score"]
        max_s = fd["max_total_score"]
        acc = fd["accuracy"]
        tpp = round(fd["token_count"] / score) if score > 0 else "∞"
        lines.append(f"| `{fn}` | {score}/{max_s} | {acc:.0%} | {tpp} |")
    lines.append("")

    # ------------------------------------------------------------------
    # Per-task breakdown
    # ------------------------------------------------------------------
    lines += [
        "## Per-Task Results",
        "",
    ]
    header_cols = " | ".join(f"`{fn}`" for fn in fmt_names)
    sep_cols = " | ".join(":-:" for _ in fmt_names)
    lines += [
        f"| Task | Category | {header_cols} |",
        f"|------|----------|{sep_cols}|",
    ]
    first_tasks = list(formats.values())[0]["tasks"]
    for task in first_tasks:
        tid = task["id"]
        cat = task["category"]
        cells = []
        for fn in fmt_names:
            t = next((t for t in formats[fn]["tasks"] if t["id"] == tid), None)
            s = t["score"] if t else "—"
            icon = _SCORE_ICON.get(s, "?") if isinstance(s, int) else "?"
            cells.append(f"{icon} {s}")
        lines.append(f"| `{tid}` | {cat} | {' | '.join(cells)} |")
    lines.append("")

    # ------------------------------------------------------------------
    # Judge reasoning (collapsible)
    # ------------------------------------------------------------------
    lines += [
        "## Judge Reasoning",
        "",
        "<details>",
        "<summary>Expand per-format, per-task reasoning</summary>",
        "",
    ]
    for fn, fd in formats.items():
        lines.append(f"### `{fn}`")
        lines.append("")
        lines.append("| Task | Score | Reasoning |")
        lines.append("|------|------:|-----------|")
        for t in fd["tasks"]:
            icon = _SCORE_ICON.get(t["score"], "?")
            reasoning = t["reasoning"].replace("|", "\\|")
            lines.append(f"| `{t['id']}` | {icon} {t['score']}/2 | {reasoning} |")
        lines.append("")
    lines += ["</details>", ""]

    # ------------------------------------------------------------------
    # Findings
    # ------------------------------------------------------------------
    best_acc_name = max(formats.items(), key=lambda kv: kv[1]["accuracy"])[0]
    best_acc_val = formats[best_acc_name]["accuracy"]
    smallest_name = min(formats.items(), key=lambda kv: kv[1]["token_count"])[0]
    smallest_tokens = formats[smallest_name]["token_count"]
    efficient_name = _efficiency_rank(formats)
    efficient_fd = formats[efficient_name]

    lines += [
        "## Key Findings",
        "",
        f"- **Highest accuracy:** `{best_acc_name}` at {best_acc_val:.0%}",
        f"- **Smallest token footprint:** `{smallest_name}` — {smallest_tokens:,} input tokens",
        (
            f"- **Most token-efficient:** `{efficient_name}` — "
            f"{efficient_fd['token_count']:,} tokens for "
            f"{efficient_fd['total_score']}/{efficient_fd['max_total_score']} score"
        ),
        "",
    ]

    # Category breakdown
    categories = sorted({t["category"] for t in first_tasks})
    lines += ["### Accuracy by Category", ""]
    cat_header = " | ".join(f"`{fn}`" for fn in fmt_names)
    lines.append(f"| Category | {cat_header} |")
    lines.append(f"|----------|{'|'.join('-----:' for _ in fmt_names)}|")
    for cat in categories:
        cells = []
        for fn in fmt_names:
            cat_tasks = [t for t in formats[fn]["tasks"] if t["category"] == cat]
            if not cat_tasks:
                cells.append("—")
                continue
            sc = sum(t["score"] for t in cat_tasks)
            mx = sum(t["max_score"] for t in cat_tasks)
            cells.append(f"{sc}/{mx}")
        lines.append(f"| {cat} | {' | '.join(cells)} |")
    lines.append("")

    lines += [
        "---",
        f"*Generated by [doc-format-benchmark](../../benchmark/) · run `{run_id}`*",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmark/report.py results.json", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as fh:
        data = json.load(fh)
    print(generate_report(data))
