import os
import re
import sys
from dataclasses import dataclass
from typing import Any


PROJECT_ROOT = os.path.dirname(__file__)
APP_DIR = os.path.join(PROJECT_ROOT, "real_estate_agent")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from graph import graph  # noqa: E402


@dataclass
class EvalCase:
    question: str
    expected_intent: str | None = None
    expected_numbers: list[float] | None = None


EVAL_CASES: list[EvalCase] = [
    EvalCase(
        question="What is total P&L for Building 180 in 2025?",
        expected_intent="pl",
    ),
    EvalCase(
        question="Compare Building 180 vs Building 140 in 2025.",
        expected_intent="compare",
    ),
    EvalCase(
        question="Show tenant-level details for Building 140 in 2025 Q1.",
        expected_intent="property",
    ),
    EvalCase(
        question="What does cap rate mean in real estate?",
        expected_intent="general",
    ),
]


def _normalize_text(value: str) -> str:
    value = value or ""
    value = value.lower().strip()
    return re.sub(r"\s+", " ", value)


def _extract_numbers(text: str) -> list[float]:
    # Matches values like 1200, 1,200.75, -900.5 and optional leading $.
    matches = re.findall(r"\$?-?\d[\d,]*(?:\.\d+)?", text or "")
    numbers: list[float] = []
    for token in matches:
        cleaned = token.replace("$", "").replace(",", "")
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue
    return numbers


def _run_case(case: EvalCase) -> dict[str, Any]:
    initial_state = {
        "question": case.question,
        "intent": "",
        "filters": {},
        "data": None,
        "answer": "",
        "error": "",
    }
    result = graph.invoke(initial_state)
    return {
        "intent": result.get("intent"),
        "answer": result.get("answer", "") or "",
        "error": result.get("error", "") or "",
    }


def evaluate(cases: list[EvalCase]) -> dict[str, Any]:
    total = len(cases)
    intent_checks = 0
    intent_hits = 0
    answer_non_empty = 0
    number_checks = 0
    number_hits = 0
    failures: list[dict[str, Any]] = []

    for idx, case in enumerate(cases, start=1):
        try:
            result = _run_case(case)
            predicted_intent = _normalize_text(str(result["intent"]))
            answer = str(result["answer"])
            error = str(result["error"])

            if answer.strip():
                answer_non_empty += 1

            if case.expected_intent:
                intent_checks += 1
                if predicted_intent == _normalize_text(case.expected_intent):
                    intent_hits += 1
                else:
                    failures.append(
                        {
                            "id": idx,
                            "question": case.question,
                            "reason": "intent_mismatch",
                            "expected": case.expected_intent,
                            "actual": result["intent"],
                        }
                    )

            if case.expected_numbers:
                number_checks += 1
                found = _extract_numbers(answer)
                # Accept expected numbers when a near-equal value appears in answer.
                has_all = all(
                    any(abs(actual - expected) <= 0.01 for actual in found)
                    for expected in case.expected_numbers
                )
                if has_all:
                    number_hits += 1
                else:
                    failures.append(
                        {
                            "id": idx,
                            "question": case.question,
                            "reason": "number_mismatch",
                            "expected": case.expected_numbers,
                            "actual": found,
                        }
                    )

            if error:
                failures.append(
                    {
                        "id": idx,
                        "question": case.question,
                        "reason": "runtime_error",
                        "expected": "",
                        "actual": error,
                    }
                )

        except Exception as exc:
            failures.append(
                {
                    "id": idx,
                    "question": case.question,
                    "reason": "exception",
                    "expected": "",
                    "actual": str(exc),
                }
            )

    def _pct(numerator: int, denominator: int) -> float:
        return (numerator / denominator * 100.0) if denominator else 0.0

    return {
        "total_cases": total,
        "intent_checks": intent_checks,
        "intent_accuracy": _pct(intent_hits, intent_checks),
        "answer_non_empty_rate": _pct(answer_non_empty, total),
        "number_checks": number_checks,
        "number_match_rate": _pct(number_hits, number_checks),
        "failures": failures,
    }


def print_report(metrics: dict[str, Any]) -> None:
    print("=== Real Estate Agent Evaluation Report ===")
    print(f"Total cases: {metrics['total_cases']}")
    print(
        f"Intent accuracy: {metrics['intent_accuracy']:.2f}% "
        f"({metrics['intent_checks']} checked)"
    )
    print(f"Answer non-empty rate: {metrics['answer_non_empty_rate']:.2f}%")
    print(
        f"Numeric match rate: {metrics['number_match_rate']:.2f}% "
        f"({metrics['number_checks']} checked)"
    )

    failures = metrics["failures"]
    print(f"Failures: {len(failures)}")
    if not failures:
        print("All checks passed.")
        return

    print("\n--- Failed Cases ---")
    for failure in failures:
        print(
            f"[Case {failure['id']}] {failure['reason']} | "
            f"Q: {failure['question']}\n"
            f"  expected: {failure['expected']}\n"
            f"  actual:   {failure['actual']}"
        )


if __name__ == "__main__":
    report = evaluate(EVAL_CASES)
    print_report(report)
