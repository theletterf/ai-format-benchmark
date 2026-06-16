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


def _score_icon(avg_score: float) -> str:
    if avg_score >= 1.67:
        return "✅"
    elif avg_score >= 1.0:
        return "⚠️"
    else:
        return "❌"


def _efficiency_rank(formats: dict) -> str:
    def tpp(fd):
        s = fd["total_score"]
        return fd["token_count"] / s if s > 0 else float("inf")
    return min(formats.items(), key=lambda kv: tpp(kv[1]))[0]


def generate_report(results: dict) -> str:
    answer_model = results.get("answer_model", results.get("model", "unknown"))
    judge_model  = results.get("judge_model", "unknown")
    n_samples    = results.get("n_samples", 1)
    run_id       = results["run_id"]
    doc_url      = results["doc_url"]
    formats: dict = results["formats"]
    fmt_names     = list(formats.keys())
    num_tasks     = len(list(formats.values())[0]["tasks"])

    lines: list[str] = []

    lines += [
        "# Doc Format Benchmark",
        "",
        "| | |",
        "|---|---|",
        f"| **Run** | `{run_id}` |",
        f"| **Answer model** | `{answer_model}` |",
        f"| **Judge model** | `{judge_model}` |",
        f"| **Samples / task** | {n_samples} |",
        f"| **Document** | {doc_url} |",
        f"| **Formats** | {', '.join(f'`{f}`' for f in fmt_names)} |",
        f"| **Tasks** | {num_tasks} × {n_samples} samples, averaged score (0–2) |",
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
        delta = "—" if tc == min_tokens else f"+{round((tc / min_tokens - 1) * 100)}%"
        lines.append(f"| `{fn}` | {tc:,} | {delta} |")
    lines.append("")

    # ------------------------------------------------------------------
    # Accuracy summary
    # ------------------------------------------------------------------
    lines += [
        "## Evaluation Accuracy",
        "",
        f"Scores are averaged over {n_samples} answer samples per task.",
        "",
        "| Format | Score | Accuracy | Tokens / pt ↓ |",
        "|--------|------:|---------:|--------------:|",
    ]
    for fn, fd in sorted(formats.items(), key=lambda kv: -kv[1]["accuracy"]):
        score = fd["total_score"]
        max_s = fd["max_total_score"]
        acc   = fd["accuracy"]
        tpp   = round(fd["token_count"] / score) if score > 0 else "∞"
        lines.append(f"| `{fn}` | {score:.1f}/{max_s} | {acc:.0%} | {tpp} |")
    lines.append("")

    # ------------------------------------------------------------------
    # Per-task breakdown
    # ------------------------------------------------------------------
    lines += ["## Per-Task Results", ""]
    header_cols = " | ".join(f"`{fn}`" for fn in fmt_names)
    sep_cols    = " | ".join(":-:" for _ in fmt_names)
    lines += [
        f"| Task | Category | {header_cols} |",
        f"|------|----------|{sep_cols}|",
    ]
    first_tasks = list(formats.values())[0]["tasks"]
    for task in first_tasks:
        tid  = task["id"]
        cat  = task["category"]
        cells = []
        for fn in fmt_names:
            t = next((t for t in formats[fn]["tasks"] if t["id"] == tid), None)
            avg = t["avg_score"] if t else 0.0
            icon = _score_icon(avg)
            cells.append(f"{icon} {avg:.2f}")
        lines.append(f"| `{tid}` | {cat} | {' | '.join(cells)} |")
    lines.append("")

    # ------------------------------------------------------------------
    # Per-sample reasoning (collapsible)
    # ------------------------------------------------------------------
    lines += [
        "## Judge Reasoning",
        "",
        "<details>",
        "<summary>Expand per-format, per-task, per-sample reasoning</summary>",
        "",
    ]
    for fn, fd in formats.items():
        lines.append(f"### `{fn}`")
        lines.append("")
        for t in fd["tasks"]:
            lines.append(f"#### `{t['id']}` — avg {t['avg_score']:.2f}/2")
            lines.append("")
            lines.append("| Sample | Score | Reasoning |")
            lines.append("|-------:|------:|-----------|")
            for i, s in enumerate(t.get("samples", []), 1):
                icon      = _score_icon(s["score"])
                reasoning = s["reasoning"].replace("|", "\\|")
                lines.append(f"| {i} | {icon} {s['score']}/2 | {reasoning} |")
            lines.append("")
    lines += ["</details>", ""]

    # ------------------------------------------------------------------
    # Key findings
    # ------------------------------------------------------------------
    best_name  = max(formats.items(), key=lambda kv: kv[1]["accuracy"])[0]
    best_acc   = formats[best_name]["accuracy"]
    small_name = min(formats.items(), key=lambda kv: kv[1]["token_count"])[0]
    small_tok  = formats[small_name]["token_count"]
    eff_name   = _efficiency_rank(formats)
    eff_fd     = formats[eff_name]

    lines += [
        "## Key Findings",
        "",
        f"- **Highest accuracy:** `{best_name}` at {best_acc:.0%}",
        f"- **Smallest token footprint:** `{small_name}` — {small_tok:,} input tokens",
        (
            f"- **Most token-efficient:** `{eff_name}` — "
            f"{eff_fd['token_count']:,} tokens for {eff_fd['total_score']:.1f}/{eff_fd['max_total_score']} score"
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
            sc = sum(t["avg_score"] for t in cat_tasks)
            mx = sum(t["max_score"] for t in cat_tasks)
            cells.append(f"{sc:.1f}/{mx}")
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
