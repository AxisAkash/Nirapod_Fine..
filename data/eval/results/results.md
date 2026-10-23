# Evaluation results

Generated 2026-10-23 23:36. Dataset: v1.0 RTA 2018 baseline.

## Stage A: rule engine on typed fields (no AI)

- Cases: 224
- Verdict accuracy: 71.4% (95% CI 65.2 to 76.9)
- Macro F1: 0.722

| Verdict | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| VALID | 0.937 | 0.679 | 0.787 | 109 |
| INVALID_FINE_TOO_HIGH | 1.000 | 0.686 | 0.814 | 70 |
| VALID_BUT_EXCEPTION_POSSIBLE | 1.000 | 0.667 | 0.800 | 6 |
| INVALID_EXCEPTION_NOT_APPLICABLE | 0.800 | 0.667 | 0.727 | 6 |
| INVALID_REASON_MISMATCH | 0.727 | 0.800 | 0.762 | 10 |
| NEEDS_MANUAL_REVIEW | 0.286 | 0.957 | 0.440 | 23 |

| Case group | n | Verdict accuracy |
|---|---|---|
| standard | 54 | 74.1% |
| boundary | 29 | 75.9% |
| paraphrase | 54 | 59.3% |
| bangla | 42 | 66.7% |
| mismatch | 10 | 80.0% |
| exception | 6 | 66.7% |
| exception_rejected | 6 | 66.7% |
| no_amount | 4 | 100.0% |
| no_ceiling | 4 | 100.0% |
| below_minimum | 3 | 100.0% |
| unknown | 12 | 91.7% |

| Section matching | n | Top-1 | Top-3 |
|---|---|---|---|
| standard | 29 | 79.3% | 100.0% |
| boundary | 13 | 84.6% | 100.0% |
| paraphrase | 16 | 56.2% | 81.2% |
| bangla | 23 | 69.6% | 95.7% |
| all uncited | 103 | 78.6% | 96.1% |
| all cited | 99 | 64.6% | 100.0% |

## Stage B: AI receipt reading

- Pictures: 56 (failed: 0)
- Mean time per picture: 7.7 s, mean cost: $0.0011

| Field | Accuracy | Wrong | Missed | Spurious |
|---|---|---|---|---|
| reason | 75.0% | 0 | 14 | 0 |
| amount | 69.6% | 3 | 14 | 0 |
| section | 89.3% | 1 | 5 | 0 |
| vehicle | 73.2% | 1 | 14 | 0 |
| date | 66.1% | 5 | 14 | 0 |
| location | 75.0% | 0 | 14 | 0 |
| receipt_number | 75.0% | 0 | 14 | 0 |
| notes | 96.4% | 0 | 2 | 0 |

## Stage C: end to end (picture to verdict)

- Accuracy: 46.4% (95% CI 34.0 to 59.3), n = 56
- Error sources: {'correct': 26, 'rule-engine error': 13, 'reading error': 12, 'both': 5}

## Stage D: baseline

- AI alone: 71.4% (95% CI 58.5 to 81.6)
- AI + rule engine: 46.4%

## Decision quality: right, handed to a person, or confidently wrong

| System | n | Correct | Manual review | Confidently wrong | Accuracy of firm answers | False approvals |
|---|---|---|---|---|---|---|
| Rule engine (typed fields) | 224 | 160 | 55 | 9 | 93.9% | 2 |
| Rule engine, same cases (typed fields) | 56 | 38 | 15 | 3 | 92.1% | 0 |
| AI + rule engine (receipt pictures) | 56 | 26 | 27 | 3 | 88.5% | 0 |
| AI alone (receipt pictures) | 56 | 40 | 13 | 3 | 92.5% | 0 |
| AI + rule engine, legible pictures only | 42 | 25 | 14 | 3 | 88.5% | 0 |
| AI alone, legible pictures only | 42 | 39 | 0 | 3 | 92.5% | 0 |

A *confidently wrong* answer is a firm verdict that differs from the correct one. A *false approval* is telling the user a wrong fine is valid.

## Caveats

- Correct answers were written from the PDFs by the tooling author, not a legal expert. Have them checked before publishing.
- Cases and pictures are synthetic. Add real receipts for stronger evidence.
- Confidence intervals are Wilson 95% intervals; with few cases they are wide.
