# Evaluation results

How to run:

```bash
uvicorn app.main:app --port 8000
python evaluation/evaluate.py
```

The script posts every question in `evaluation/questions.json` to the
running API and reports intent accuracy, failure count, and p95 latency.

## Baselines

| Run | Intent accuracy | Failures | p95 latency | Notes |
|---|---|---|---|---|
| Keyword mock (no LLM key) | 10/12 (83.3%) | 0 | 5 ms | Deterministic mock; misses are phrasing variants the keywords don't cover |
| Real LLM (`OPENAI_API_KEY` set) | — | — | — | Fill in after running with a key |

The two mock misses ("My card was declined but I have funds",
"Does this phone support wireless charging") are phrasing the keyword
list doesn't cover. They are the cases a real LLM call should fix,
which makes this a useful before/after comparison.

## Recording a new run

1. Run the eval script against the deployment you want to measure.
2. Add a row to the table above with the numbers you actually saw.
3. Only commit measured numbers. Targets from the design doc
   (intent accuracy above 90%, p95 under 3s) stay targets until a run
   proves them.
