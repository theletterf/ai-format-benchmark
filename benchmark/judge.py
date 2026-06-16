"""
LLM-based answering and judging via Anthropic API.

Answering model  : claude-haiku-4-5  (fast, cheap; default temperature for variation)
Judging model    : claude-sonnet-4-6  (stronger; temperature=0 for determinism)
Token counting   : Anthropic count_tokens API — exact, model-native

Each task is sampled N_SAMPLES times; scores are averaged to a float,
which reduces the effect of single-call judge noise.
"""

import json
import re

import anthropic

ANSWER_MODEL = "claude-haiku-4-5-20251001"
JUDGE_MODEL  = "claude-sonnet-4-6"

N_SAMPLES = 3

_ANSWER_SYSTEM = (
    "You are a technical documentation assistant. "
    "Answer questions using only the provided documentation. "
    "Be concise and precise; cite specific values and commands when relevant."
)

_JUDGE_SYSTEM = (
    "You are an expert technical evaluator. "
    "Score AI-generated answers to documentation questions accurately and consistently."
)

_JUDGE_PROMPT = """\
Evaluate the following answer to a technical documentation question.

**Question:** {question}

**Ground truth** (key information the answer must contain):
{ground_truth}

**Answer to evaluate:**
{answer}

Score on a 0–2 scale:
- 2 = Correct and complete — all key facts from the ground truth are present
- 1 = Partially correct — main idea is right but misses details or has minor errors
- 0 = Incorrect, missing essential information, or not answerable from this document

Respond with valid JSON only — no markdown, no preamble:
{{"score": <0|1|2>, "reasoning": "<one concise sentence>"}}"""


def make_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def count_doc_tokens(client: anthropic.Anthropic, doc_content: str) -> int:
    """Count input tokens using Anthropic's count_tokens API (exact, model-native)."""
    response = client.messages.count_tokens(
        model=ANSWER_MODEL,
        system=_ANSWER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"<document>\n{doc_content}\n</document>\n\n"
                    "How many steps does this quickstart have?"
                ),
            }
        ],
    )
    return response.input_tokens


def answer_question(
    client: anthropic.Anthropic,
    doc_content: str,
    question: str,
) -> tuple[str, int]:
    """Return (answer_text, output_tokens). Default temperature for genuine variation."""
    message = client.messages.create(
        model=ANSWER_MODEL,
        max_tokens=512,
        system=_ANSWER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"<document>\n{doc_content}\n</document>\n\n{question}",
            }
        ],
    )
    return message.content[0].text, message.usage.output_tokens


def judge_answer(
    client: anthropic.Anthropic,
    question: str,
    ground_truth: str,
    answer: str,
) -> dict:
    """Return {"score": 0|1|2, "reasoning": str}. temperature=0 for deterministic scoring."""
    prompt = _JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        answer=answer,
    )
    message = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=256,
        temperature=0,
        system=_JUDGE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    m = re.search(r"\{.*?\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {"score": 0, "reasoning": f"[judge parse error] {raw[:120]}"}


def evaluate_format(
    client: anthropic.Anthropic,
    format_name: str,
    doc_content: str,
    tasks: list[dict],
) -> dict:
    """
    Run the full evaluation pipeline for one document format.
    Each task is answered and judged N_SAMPLES times; scores are averaged.
    """
    print("    counting tokens (Anthropic API)...", flush=True)
    token_count = count_doc_tokens(client, doc_content)

    task_results = []
    for task in tasks:
        samples = []
        for s in range(1, N_SAMPLES + 1):
            print(f"    [{task['id']}] sample {s}/{N_SAMPLES}...", flush=True)
            answer, answer_tokens = answer_question(client, doc_content, task["question"])
            judgment = judge_answer(client, task["question"], task["ground_truth"], answer)
            samples.append(
                {
                    "answer": answer,
                    "answer_tokens": answer_tokens,
                    "score": judgment.get("score", 0),
                    "reasoning": judgment.get("reasoning", ""),
                }
            )

        scores = [s["score"] for s in samples]
        avg_score = round(sum(scores) / len(scores), 3)

        task_results.append(
            {
                "id": task["id"],
                "category": task["category"],
                "question": task["question"],
                "ground_truth": task["ground_truth"],
                "avg_score": avg_score,
                "max_score": 2,
                "samples": samples,
            }
        )

    total_score = round(sum(t["avg_score"] for t in task_results), 2)
    max_total = sum(t["max_score"] for t in task_results)
    total_answer_tokens = sum(
        s["answer_tokens"] for t in task_results for s in t["samples"]
    )

    return {
        "format": format_name,
        "token_count": token_count,
        "total_answer_tokens": total_answer_tokens,
        "n_samples": N_SAMPLES,
        "tasks": task_results,
        "total_score": total_score,
        "max_total_score": max_total,
        "accuracy": round(total_score / max_total, 4) if max_total else 0.0,
    }
