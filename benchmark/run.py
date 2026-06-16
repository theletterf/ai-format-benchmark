#!/usr/bin/env python3
"""
Main benchmark runner.

Usage:
    python benchmark/run.py [--output results.json]

Environment variables:
    GITHUB_TOKEN        required — provided automatically in GitHub Actions
    BENCHMARK_DOC_URL   override the annotated-MD source URL (optional)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Make benchmark package importable when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.formats import DOC_MD_URL, DOC_HTML_URL, get_all_formats
from benchmark.judge import DEFAULT_MODEL, make_client, evaluate_format
from benchmark.tasks import TASKS


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the doc-format benchmark")
    parser.add_argument("--output", default="results.json", help="Output JSON path")
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        sys.exit("Error: GITHUB_TOKEN environment variable is not set.")

    md_url = os.environ.get("BENCHMARK_DOC_URL") or DOC_MD_URL

    client = make_client(github_token)
    model = DEFAULT_MODEL

    print(f"=== Doc Format Benchmark ===")
    print(f"Model  : {model} (GitHub Models)")
    print(f"Tasks  : {len(TASKS)}")
    print(f"Doc URL: {md_url}")
    print()

    # ------------------------------------------------------------------ #
    # 1. Fetch & prepare all formats                                       #
    # ------------------------------------------------------------------ #
    print("Fetching document formats...")
    formats_content = get_all_formats(md_url=md_url, html_url=DOC_HTML_URL)

    for name, content in formats_content.items():
        print(f"  {name:<14} {len(content):>7,} chars")
    print()

    # ------------------------------------------------------------------ #
    # 2. Evaluate each format                                             #
    # ------------------------------------------------------------------ #
    results_by_format: dict = {}
    for fmt_name, doc_content in formats_content.items():
        print(f"Evaluating: {fmt_name}")
        result = evaluate_format(client, model, fmt_name, doc_content, TASKS)
        results_by_format[fmt_name] = result
        print(
            f"  → {result['total_score']}/{result['max_total_score']} "
            f"({result['accuracy']:.0%} accuracy), "
            f"{result['token_count']:,} input tokens"
        )
        print()

    # ------------------------------------------------------------------ #
    # 3. Persist results                                                  #
    # ------------------------------------------------------------------ #
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "run_id": run_id,
        "model": model,
        "doc_url": md_url,
        "formats": results_by_format,
    }

    with open(args.output, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"Results saved → {args.output}")
    print()

    print(f"{'Format':<16} {'Score':>7}  {'Accuracy':>9}  {'Tokens':>8}")
    print("-" * 50)
    for fn, fd in sorted(results_by_format.items(), key=lambda kv: -kv[1]["accuracy"]):
        print(
            f"  {fn:<14} {fd['total_score']:>3}/{fd['max_total_score']:<3}  "
            f"{fd['accuracy']:>8.0%}  {fd['token_count']:>8,}"
        )


if __name__ == "__main__":
    main()
