"""
LLM-based answering and judging via GitHub Models (OpenAI-compatible API).

Token counting is done locally with tiktoken — no extra API call required.
The GITHUB_TOKEN provided automatically in Actions is used as the bearer token.
"""

import json
import re

import tiktoken
from openai import OpenAI

GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"
DEFAULT_MODEL = "gpt-4o-mini"

_ENCODING = tiktoken.get_encoding("cl100k_base")

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


def make_client(github_token: str) -> OpenAI:
    return OpenAI(base_url=GITHUB_MODELS_BASE_URL, api_key=github_token)


def count_doc_tokens(doc_content: str) -> int:
    """Count input tokens for a document+question pair using tiktoken (local, free)."""
    system_tokens = len(_ENCODING.encode(_ANSWER_SYSTEM))
    user_tokens = len(
        _ENCODING.encode(
            f"<document>\n{doc_content}\n</document>\n\n"
            "How many steps does this quickstart have?"
        )
    )
    return system_tokens + user_tokens


def answer_question(
    client: OpenAI,
    model: str,
    doc_content: str,
    question: str,
) -> tuple[str, int]:
    """Return (answer_text, completion_tokens)."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=512,
        messages=[
            {"role": "system", "content": _ANSWER_SYSTEM},
            {
                "role": "user",
                "content": f"<document>\n{doc_content}\n</document>\n\n{question}",
            },
        ],
    )
    return response.choices[0].message.content, response.usage.completion_tokens


def judge_answer(
    client: OpenAI,
    model: str,
    question: str,
    ground_truth: str,
    answer: str,
) -> dict:
    """Return {"score": 0|1|2, "reasoning": str}."""
    prompt = _JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        answer=answer,
    )
    response = client.chat.completions.create(
        model=model,
        max_tokens=256,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()
    m = re.search(r"\{.*?\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {"score": 0, "reasoning": f"[judge parse error] {raw[:120]}"}


def evaluate_format(
    client: OpenAI,
    model: str,
    format_name: str,
    doc_content: str,
    tasks: list[dict],
) -> dict:
    """Run the full evaluation pipeline for one document format."""
    print(f"    counting tokens (local)...", flush=True)
    token_count = count_doc_tokens(doc_content)

    task_results = []
    for task in tasks:
        print(f"    [{task['id']}] answering...", flush=True)
        answer, answer_tokens = answer_question(client, model, doc_content, task["question"])

        print(f"    [{task['id']}] judging...", flush=True)
        judgment = judge_answer(
            client, model, task["question"], task["ground_truth"], answer
        )

        task_results.append(
            {
                "id": task["id"],
                "category": task["category"],
                "question": task["question"],
                "ground_truth": task["ground_truth"],
                "answer": answer,
                "answer_tokens": answer_tokens,
                "score": judgment.get("score", 0),
                "max_score": 2,
                "reasoning": judgment.get("reasoning", ""),
            }
        )

    total_score = sum(t["score"] for t in task_results)
    max_total = sum(t["max_score"] for t in task_results)
    total_answer_tokens = sum(t["answer_tokens"] for t in task_results)

    return {
        "format": format_name,
        "token_count": token_count,
        "total_answer_tokens": total_answer_tokens,
        "tasks": task_results,
        "total_score": total_score,
        "max_total_score": max_total,
        "accuracy": round(total_score / max_total, 4) if max_total else 0.0,
    }
