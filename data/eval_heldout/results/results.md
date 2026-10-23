# Evaluation results

Generated 2026-10-23 23:15. Dataset: v1.0 RTA 2018 baseline.

## Stage A: rule engine on typed fields (no AI)

- Cases: 222
- Verdict accuracy: 70.7% (95% CI 64.4 to 76.3)
- Macro F1: 0.718

| Verdict | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| VALID | 0.937 | 0.679 | 0.787 | 109 |
| INVALID_FINE_TOO_HIGH | 0.978 | 0.662 | 0.789 | 68 |
| VALID_BUT_EXCEPTION_POSSIBLE | 1.000 | 0.667 | 0.800 | 6 |
| INVALID_EXCEPTION_NOT_APPLICABLE | 0.800 | 0.667 | 0.727 | 6 |
| INVALID_REASON_MISMATCH | 0.727 | 0.800 | 0.762 | 10 |
| NEEDS_MANUAL_REVIEW | 0.286 | 0.957 | 0.440 | 23 |

| Case group | n | Verdict accuracy |
|---|---|---|
| standard | 54 | 74.1% |
| boundary | 29 | 75.9% |
| paraphrase | 54 | 59.3% |
| bangla | 40 | 62.5% |
| mismatch | 10 | 80.0% |
| exception | 6 | 66.7% |
| exception_rejected | 6 | 66.7% |
| no_amount | 4 | 100.0% |
| no_ceiling | 4 | 100.0% |
| below_minimum | 3 | 100.0% |
| unknown | 12 | 91.7% |

| Section matching | n | Top-1 | Top-3 |
|---|---|---|---|
| standard | 30 | 66.7% | 100.0% |
| boundary | 13 | 84.6% | 100.0% |
| paraphrase | 23 | 65.2% | 82.6% |
| bangla | 21 | 47.6% | 85.7% |
| all uncited | 110 | 71.8% | 93.6% |
| all cited | 90 | 70.0% | 100.0% |

## Stage B: AI receipt reading

- Pictures: 56 (failed: 0)
- Mean time per picture: 8.3 s, mean cost: $0.0011

| Field | Accuracy | Wrong | Missed | Spurious |
|---|---|---|---|---|
| reason | 73.2% | 1 | 14 | 0 |
| amount | 73.2% | 1 | 14 | 0 |
| section | 85.7% | 2 | 6 | 0 |
| vehicle | 75.0% | 0 | 14 | 0 |
| date | 64.3% | 6 | 14 | 0 |
| location | 75.0% | 0 | 14 | 0 |
| receipt_number | 75.0% | 0 | 14 | 0 |
| notes | 94.6% | 0 | 3 | 0 |

## Stage C: end to end (picture to verdict)

- Accuracy: 48.2% (95% CI 35.7 to 61.0), n = 56
- Error sources: {'correct': 27, 'reading error': 14, 'rule-engine error': 9, 'both': 6}

## Decision quality: right, handed to a person, or confidently wrong

| System | n | Correct | Manual review | Confidently wrong | Accuracy of firm answers | False approvals |
|---|---|---|---|---|---|---|
| Rule engine (typed fields) | 222 | 157 | 55 | 10 | 93.1% | 2 |
| Rule engine, same cases (typed fields) | 56 | 41 | 9 | 6 | 86.4% | 1 |
| AI + rule engine (receipt pictures) | 56 | 27 | 22 | 7 | 77.4% | 1 |
| AI + rule engine, legible pictures only | 42 | 26 | 9 | 7 | 77.4% | 1 |

A *confidently wrong* answer is a firm verdict that differs from the correct one. A *false approval* is telling the user a wrong fine is valid.

## Caveats

- Correct answers were written from the PDFs by the tooling author, not a legal expert. Have them checked before publishing.
- Cases and pictures are synthetic. Add real receipts for stronger evidence.
- Confidence intervals are Wilson 95% intervals; with few cases they are wide.
