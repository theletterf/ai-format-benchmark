"""
Generate a Markdown report from multi-document benchmark results JSON.

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


def _fmt_names(doc_result: dict) -> list[str]:
    return list(doc_result["formats"].keys())


def generate_report(results: dict) -> str:
    answer_model = results.get("answer_model", "unknown")
    judge_model  = results.get("judge_model", "unknown")
    n_samples    = results.get("n_samples", 1)
    run_id       = results["run_id"]
    docs: dict   = results["documents"]

    lines: list[str] = []

    lines += [
        "# Doc Format Benchmark",
        "",
        "| | |",
        "|---|---|",
        f"| **Run** | `{run_id}` |",
        f"| **Answer / Judge model** | `{answer_model}` |",
        f"| **Samples / task** | {n_samples} |",
        f"| **Documents** | {len(docs)} |",
        "",
    ]

    # ------------------------------------------------------------------
    # Cross-document summary
    # ------------------------------------------------------------------
    all_fmt_names = list(list(docs.values())[0]["formats"].keys())

    lines += [
        "## Summary: Accuracy by Document",
        "",
        "Scores are averaged over " + str(n_samples) + " samples per task.",
        "",
    ]
    header = " | ".join(f"`{f}`" for f in all_fmt_names)
    sep    = " | ".join("------:" for _ in all_fmt_names)
    lines.append(f"| Document | Tasks | {header} |")
    lines.append(f"|----------|------:|{sep}|")
    for doc_id, doc_result in docs.items():
        n_tasks = len(list(doc_result["formats"].values())[0]["tasks"])
        cells = []
        for fn in all_fmt_names:
            fd = doc_result["formats"].get(fn)
            if fd:
                cells.append(f"{fd['accuracy']:.0%}")
            else:
                cells.append("—")
        lines.append(f"| {doc_result['title']} | {n_tasks} | {' | '.join(cells)} |")
    lines.append("")

    lines += [
        "## Summary: Token Consumption",
        "",
        "| Document | " + " | ".join(f"`{f}`" for f in all_fmt_names) + " |",
        "|----------|" + "|".join("------:" for _ in all_fmt_names) + "|",
    ]
    for doc_id, doc_result in docs.items():
        cells = []
        for fn in all_fmt_names:
            fd = doc_result["formats"].get(fn)
            cells.append(f"{fd['token_count']:,}" if fd else "—")
        lines.append(f"| {doc_result['title']} | {' | '.join(cells)} |")
    lines.append("")

    # ------------------------------------------------------------------
    # Per-document sections
    # ------------------------------------------------------------------
    for doc_id, doc_result in docs.items():
        fmt_names = _fmt_names(doc_result)
        formats   = doc_result["formats"]
        first_tasks = list(formats.values())[0]["tasks"]

        lines += [
            f"---",
            f"",
            f"## {doc_result['title']}",
            f"",
            f"**URL:** {doc_result['md_url']}",
            f"",
        ]

        # Token consumption
        min_tokens = min(fd["token_count"] for fd in formats.values())
        lines += [
            "### Token Consumption",
            "",
            "| Format | Input tokens | vs smallest |",
            "|--------|-------------:|------------:|",
        ]
        for fn, fd in sorted(formats.items(), key=lambda kv: kv[1]["token_count"]):
            tc = fd["token_count"]
            delta = "—" if tc == min_tokens else f"+{round((tc / min_tokens - 1) * 100)}%"
            lines.append(f"| `{fn}` | {tc:,} | {delta} |")
        lines.append("")

        # Accuracy summary
        lines += [
            "### Accuracy",
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

        # Per-task breakdown
        lines += ["### Per-Task Results", ""]
        hdr = " | ".join(f"`{fn}`" for fn in fmt_names)
        sep = " | ".join(":-:" for _ in fmt_names)
        lines += [
            f"| Task | Category | {hdr} |",
            f"|------|----------|{sep}|",
        ]
        for task in first_tasks:
            tid = task["id"]
            cat = task["category"]
            cells = []
            for fn in fmt_names:
                t = next((t for t in formats[fn]["tasks"] if t["id"] == tid), None)
                avg = t["avg_score"] if t else 0.0
                cells.append(f"{_score_icon(avg)} {avg:.2f}")
            lines.append(f"| `{tid}` | {cat} | {' | '.join(cells)} |")
        lines.append("")

        # Per-sample reasoning (collapsible)
        lines += [
            "### Judge Reasoning",
            "",
            "<details>",
            "<summary>Expand per-format, per-task, per-sample reasoning</summary>",
            "",
        ]
        for fn, fd in formats.items():
            lines.append(f"#### `{fn}`")
            lines.append("")
            for t in fd["tasks"]:
                lines.append(f"##### `{t['id']}` — avg {t['avg_score']:.2f}/2")
                lines.append("")
                lines.append("| Sample | Score | Reasoning |")
                lines.append("|-------:|------:|-----------|")
                for i, s in enumerate(t.get("samples", []), 1):
                    reasoning = s["reasoning"].replace("|", "\\|")
                    lines.append(f"| {i} | {_score_icon(s['score'])} {s['score']}/2 | {reasoning} |")
                lines.append("")
        lines += ["</details>", ""]

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
