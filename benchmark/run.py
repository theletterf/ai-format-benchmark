#!/usr/bin/env python3
"""
Main benchmark runner.

Usage:
    python benchmark/run.py [--output results.json]

Environment variables:
    LITELLM_API_KEY   required — add as a repository secret
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.documents import DOCUMENTS
from benchmark.formats import get_formats_for_doc
from benchmark.judge import ANSWER_MODEL, JUDGE_MODEL, N_SAMPLES, evaluate_format, make_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the doc-format benchmark")
    parser.add_argument("--output", default="results.json", help="Output JSON path")
    args = parser.parse_args()

    api_key = os.environ.get("LITELLM_API_KEY")
    if not api_key:
        sys.exit("Error: LITELLM_API_KEY environment variable is not set.")

    client = make_client(api_key)

    total_tasks = sum(len(d["tasks"]) for d in DOCUMENTS)
    print("=== Doc Format Benchmark ===")
    print(f"Answer model  : {ANSWER_MODEL}")
    print(f"Judge model   : {JUDGE_MODEL}")
    print(f"Samples/task  : {N_SAMPLES}")
    print(f"Documents     : {len(DOCUMENTS)}")
    print(f"Tasks (total) : {total_tasks}")
    print()

    results_by_doc: dict = {}

    for doc in DOCUMENTS:
        print(f"── Document: {doc['title']} ──")
        print(f"   Fetching formats...")
        formats_content = get_formats_for_doc(doc)
        for name, content in formats_content.items():
            print(f"   {name:<14} {len(content):>8,} chars")
        print()

        doc_results: dict = {}
        for fmt_name, doc_content in formats_content.items():
            print(f"   Evaluating: {fmt_name}")
            result = evaluate_format(client, fmt_name, doc_content, doc["tasks"])
            doc_results[fmt_name] = result
            print(
                f"   → {result['total_score']:.1f}/{result['max_total_score']} "
                f"({result['accuracy']:.0%} accuracy), "
                f"{result['token_count']:,} tokens"
            )
            print()

        results_by_doc[doc["id"]] = {
            "id": doc["id"],
            "title": doc["title"],
            "md_url": doc["md_url"],
            "formats": doc_results,
        }

        print(f"   {'Format':<16} {'Score':>8}  {'Accuracy':>9}  {'Tokens':>8}")
        print("   " + "-" * 48)
        for fn, fd in sorted(doc_results.items(), key=lambda kv: -kv[1]["accuracy"]):
            print(
                f"   {fn:<16} {fd['total_score']:>5.1f}/{fd['max_total_score']:<3}  "
                f"{fd['accuracy']:>8.0%}  {fd['token_count']:>8,}"
            )
        print()

    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "run_id": run_id,
        "answer_model": ANSWER_MODEL,
        "judge_model": JUDGE_MODEL,
        "n_samples": N_SAMPLES,
        "documents": results_by_doc,
    }

    with open(args.output, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"Results saved → {args.output}")


if __name__ == "__main__":
    main()
