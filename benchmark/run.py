#!/usr/bin/env python3
"""
Main benchmark runner.

Usage:
    python benchmark/run.py [--output results.json]

Environment variables:
    ANTHROPIC_API_KEY   required — add as a repository secret
    BENCHMARK_DOC_URL   override the annotated-MD source URL (optional)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Make benchmark package importable when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.formats import DOC_HTML_URL, DOC_MD_URL, get_all_formats
from benchmark.judge import ANSWER_MODEL, JUDGE_MODEL, N_SAMPLES, evaluate_format, make_client
from benchmark.tasks import TASKS


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the doc-format benchmark")
    parser.add_argument("--output", default="results.json", help="Output JSON path")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Error: ANTHROPIC_API_KEY environment variable is not set.")

    md_url = os.environ.get("BENCHMARK_DOC_URL") or DOC_MD_URL
    client = make_client(api_key)

    print("=== Doc Format Benchmark ===")
    print(f"Answer model : {ANSWER_MODEL}")
    print(f"Judge model  : {JUDGE_MODEL}")
    print(f"Samples/task : {N_SAMPLES}")
    print(f"Tasks        : {len(TASKS)}")
    print(f"Doc URL      : {md_url}")
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
        result = evaluate_format(client, fmt_name, doc_content, TASKS)
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
        "answer_model": ANSWER_MODEL,
        "judge_model": JUDGE_MODEL,
        "n_samples": N_SAMPLES,
        "doc_url": md_url,
        "formats": results_by_format,
    }

    with open(args.output, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"Results saved → {args.output}")
    print()
    print(f"{'Format':<16} {'Score':>8}  {'Accuracy':>9}  {'Tokens':>8}")
    print("-" * 52)
    for fn, fd in sorted(results_by_format.items(), key=lambda kv: -kv[1]["accuracy"]):
        print(
            f"  {fn:<14} {fd['total_score']:>5.1f}/{fd['max_total_score']:<3}  "
            f"{fd['accuracy']:>8.0%}  {fd['token_count']:>8,}"
        )


if __name__ == "__main__":
    main()
