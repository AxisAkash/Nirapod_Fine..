# Evaluation for the paper

| File | What it is |
|---|---|
| `build_testset.py` | Writes `cases.csv` (224 labelled cases) and `receipts/` (56 receipt pictures + `manifest.json`). Deterministic. |
| `cases.csv` | Each case with its correct section and verdict. Check these by hand before publishing. |
| `receipts/` | Pictures: clean, phone-photo, blurry, dim; English and Bangla. |
| `results/` | Figures (PDF + PNG), tables (CSV), `summary.json`, `results.md`. Written by the scripts below. |

## Run

From `backend/`:

```bash
.venv/bin/pip install -r requirements-eval.txt                       # once

.venv/bin/python scripts/evaluate.py                                 # rule engine only: free and instant
.venv/bin/python scripts/evaluate.py --ai                            # + AI reads the pictures + end to end (costs a little)
.venv/bin/python scripts/evaluate.py --ai --baseline                 # + "AI alone" comparison

EVAL_TAMPER_OUT=../data/eval/results/table_tamper_detection.csv .venv/bin/python -m pytest tests/test_eval_tamper.py -q -s
```

## How the correct answers were made

The correct section and verdict were written from the maximum fines in `data/source/Bangladesh_Road_Transport_Act_2018_Traffic_Fines.pdf`
and the exceptions in `Bangladesh_Traffic_Law_Exceptions_and_Exemptions.pdf`, **not** taken from the engine's output. Wordings that the
engine's alias lists do not contain are included on purpose (groups `paraphrase` and `bangla`).

## Limits to state in the paper

- The labels were written by the tooling author, not a legal expert. Have a person who knows the Act review `cases.csv`.
- Everything here is synthetic. Real receipts are stronger evidence; add them to `receipts/` with a manifest entry.
- Do not add the test wordings to the engine's aliases and then re-run: that makes the result circular. Keep a held-out set for any
  tuning, and report the numbers from data the engine has not been tuned on.
