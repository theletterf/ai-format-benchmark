# AI Format Benchmark

Measures how different documentation formats affect LLM token consumption and answer quality, using a real-world technical quickstart as the test document.

## What it benchmarks

Four representations of the same page — [Quickstart: Ingest custom metrics with EDOT](https://www.elastic.co/docs/solutions/observability/get-started/opentelemetry/custom-metrics-quickstart) — are evaluated side by side:

| Format | Description |
|--------|-------------|
| `annotated_md` | Elastic's source Markdown with frontmatter and custom directives (`<stepper>`, `<step>`) |
| `doclang` | [DocLang](https://doclang.ai) XML conversion — semantic tags, procedure steps, code blocks |
| `html` | Main-content HTML extracted from the live web page |
| `plain_text` | Stripped baseline — no markup, just the words |

## Metrics

- **Token consumption** — input tokens for each format (counted locally with `tiktoken`)
- **Answer accuracy** — 10 Q&A tasks scored 0–2 by an LLM judge
- **Token efficiency** — tokens per correct point (lower is better)

### Evaluation tasks

Tasks span five categories: factual retrieval, code extraction, troubleshooting, navigation, metadata, reasoning, and comprehension. Each answer is judged against a ground-truth string on a 0–2 rubric.

## Running the benchmark

### GitHub Actions (recommended)

Trigger manually from the **Actions** tab → **Doc Format Benchmark** → **Run workflow**.

No secrets to configure — the workflow uses `GITHUB_TOKEN` with GitHub Models (Copilot). Requires Copilot access enabled for the organization.

Results are posted as a GitHub issue labelled `benchmark`.

### Locally

```bash
pip install -r benchmark/requirements.txt
GITHUB_TOKEN=<your-pat> python benchmark/run.py --output results.json
python benchmark/report.py results.json
```

## Output

Each run produces a `results.json` artifact and opens a GitHub issue like this:

```
[Benchmark] doc-format · gpt-4o-mini · 2026-06-16
```

The issue contains token counts, accuracy tables, per-task scores, and judge reasoning.

## Structure

```
benchmark/
  tasks.py       10 evaluation tasks with ground-truth answers
  formats.py     Fetchers and converters for all four formats
  judge.py       LLM answering + tiktoken counting + LLM judging
  report.py      Markdown report generator
  run.py         Main orchestrator
.github/workflows/
  doc-format-benchmark.yml   workflow_dispatch trigger
```
