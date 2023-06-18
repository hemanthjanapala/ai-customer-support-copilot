"""Eval script: measures intent classification accuracy against questions.json.

Usage:
    1. Start the API: uvicorn app.main:app --port 8000
    2. Run: python evaluation/evaluate.py [--url http://localhost:8000]

Results are targets until measured on a real run. Do not put unmeasured
numbers on a resume.
"""

import argparse
import json
import sys
import time
import urllib.request

INTENTS = {
    "ORDER_STATUS",
    "DELIVERY_DELAY",
    "REFUND",
    "PAYMENT_PROBLEM",
    "CANCEL_ORDER",
    "PRODUCT_INFORMATION",
    "GENERAL_SUPPORT",
}


def post_chat(base_url: str, question: str) -> dict:
    payload = json.dumps(
        {"customer_id": "eval", "message": question}
    ).encode()
    req = urllib.request.Request(
        f"{base_url}/api/v1/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    return {"intent": body["intent"], "latency_ms": (time.time() - t0) * 1000}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--questions", default="evaluation/questions.json")
    args = parser.parse_args()

    with open(args.questions) as f:
        questions = json.load(f)

    correct = 0
    latencies: list[float] = []
    failures = 0
    for item in questions:
        try:
            result = post_chat(args.url, item["question"])
            latencies.append(result["latency_ms"])
            predicted = result["intent"]
            if predicted not in INTENTS:
                print(f"INVALID INTENT '{predicted}' for: {item['question']}")
            if predicted == item["expected_intent"]:
                correct += 1
            else:
                print(f"MISS: got {predicted}, want {item['expected_intent']}: {item['question']}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR on '{item['question']}': {e}")

    total = len(questions)
    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies)) - 1] if latencies else 0
    print("----")
    print(f"Questions:        {total}")
    print(f"Intent accuracy:  {correct}/{total} = {correct / total:.1%}")
    print(f"Failures:         {failures}")
    print(f"Latency p95:      {p95:.0f} ms")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
