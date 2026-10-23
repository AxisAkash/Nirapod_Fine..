"""Measures how well Nirapod Fine works, and draws the charts and tables for the paper.

Run (from backend/):
    .venv/bin/python scripts/evaluate.py                      rule engine only: free, instant, no network
    .venv/bin/python scripts/evaluate.py --ai                 also read the receipt pictures with the AI and run end to end
    .venv/bin/python scripts/evaluate.py --ai --baseline      also ask the AI for a verdict on its own (no rule engine)
    options:  --reuse (score the readings saved by the last --ai run instead of reading again)    --cases PATH  --receipts DIR  --out DIR  --limit N (use only the first N pictures)  --passes N (AI readings per picture)

--ai and --baseline call the real AI service (OPENROUTER_API_KEY in backend/.env) and cost a small amount per picture.

Stages
  A  rule engine      the typed fields of each case go straight into the engine (no AI)
  B  receipt reading  the AI reads each receipt picture; compared field by field with the known answer
  C  end to end       what the AI read goes through the engine; compared with the correct verdict
  D  baseline         the AI is given the legal table and asked for the verdict itself, without the rule engine

Everything is written to data/eval/results/: figures as PDF (vector, for the paper) and PNG, tables as CSV, summary.json
and results.md. The correct answers come from data/eval/cases.csv (see data/eval/build_testset.py for how they were made).
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from app.engine import ReceiptInput, load_default_dataset, validate  # noqa: E402
from app.engine.normalize import normalize  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
NOW = datetime(2026, 10, 12, 12, 0)
DATASET = load_default_dataset()

VERDICTS = ["VALID", "INVALID_FINE_TOO_HIGH", "VALID_BUT_EXCEPTION_POSSIBLE", "INVALID_EXCEPTION_NOT_APPLICABLE", "INVALID_REASON_MISMATCH", "NEEDS_MANUAL_REVIEW"]
SHORT = {"VALID": "Valid", "INVALID_FINE_TOO_HIGH": "Fine too high", "VALID_BUT_EXCEPTION_POSSIBLE": "Exception\npossible",
         "INVALID_EXCEPTION_NOT_APPLICABLE": "Exception\nrejected", "INVALID_REASON_MISMATCH": "Section\nmismatch", "NEEDS_MANUAL_REVIEW": "Manual\nreview"}
GROUP_ORDER = ["standard", "boundary", "paraphrase", "bangla", "mismatch", "exception", "exception_rejected", "no_amount", "no_ceiling", "below_minimum", "unknown"]
FIELDS = ["reason", "amount", "section", "vehicle", "date", "location", "receipt_number", "notes"]

# ------------------------------------------------------------------------------------------------ plot style for a paper
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight", "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})
# colour-blind safe (Okabe-Ito) and distinguishable in greyscale
BLUE, ORANGE, GREEN, GREY = "#0072B2", "#E69F00", "#009E73", "#8c8c8c"
ONE_COL, TWO_COL = 3.4, 7.0


# ---------------------------------------------------------------------------------------------------------- metrics
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a proportion, honest even for small samples."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def confusion(labels: list[str], truth: list[str], pred: list[str]) -> np.ndarray:
    idx = {l: i for i, l in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(truth, pred):
        if t in idx and p in idx:
            m[idx[t], idx[p]] += 1
    return m


def prf(m: np.ndarray) -> list[dict[str, float]]:
    out = []
    for i in range(len(m)):
        tp, fp, fn = m[i, i], m[:, i].sum() - m[i, i], m[i, :].sum() - m[i, i]
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        out.append(dict(precision=p, recall=r, f1=2 * p * r / (p + r) if p + r else 0.0, support=int(m[i, :].sum())))
    return out


def save(fig: plt.Figure, out: Path, name: str) -> None:
    fig.savefig(out / f"{name}.pdf")
    fig.savefig(out / f"{name}.png")
    plt.close(fig)


def heatmap(ax, m: np.ndarray, xlabels: list[str], ylabels: list[str], *, annotate: bool = True, fontsize: int = 7) -> None:
    norm = m / np.maximum(m.sum(axis=1, keepdims=True), 1)
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(xlabels)), xlabels, rotation=45 if len(xlabels) > 8 else 0, ha="right" if len(xlabels) > 8 else "center")
    ax.set_yticks(range(len(ylabels)), ylabels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Correct")
    ax.spines[:].set_visible(False)
    if annotate:
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                if m[i, j]:
                    ax.text(j, i, str(m[i, j]), ha="center", va="center", fontsize=fontsize, color="white" if norm[i, j] > 0.55 else "black")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(dict.fromkeys(k for r in rows for k in r))  # rows may carry different columns
    with path.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------------------------------------- the engine
def run_engine(fields: dict[str, Any]) -> dict[str, Any]:
    amount = fields.get("amount")
    r = validate(ReceiptInput(
        reason=str(fields.get("reason") or ""), amount=int(amount) if amount not in (None, "") else None,
        section=fields.get("section") or None, vehicle=fields.get("vehicle") or None, notes=fields.get("notes") or None,
        checked_at=NOW), DATASET, [])
    ranked = [c.rule.section for c in r.candidates if c.total > 0]
    return dict(status=r.status.value, section=r.matched_rule.section if r.matched_rule else "none", top3=ranked[:3],
                reason_top3=[c.rule.section for c in sorted(r.candidates, key=lambda c: c.reason_score, reverse=True) if c.reason_score > 0][:3])


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf8") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------------------------------------------------ stage A
def stage_a(cases: list[dict[str, str]], out: Path) -> dict[str, Any]:
    for c in cases:
        c["pred"] = run_engine(dict(reason=c["reason"], amount=c["amount"], section=c["section_cited"], vehicle=c["vehicle"], notes=c["notes"]))
    truth = [c["true_verdict"] for c in cases]
    pred = [c["pred"]["status"] for c in cases]
    ok = sum(t == p for t, p in zip(truth, pred))
    lo, hi = wilson(ok, len(cases))
    labels = [v for v in VERDICTS if v in set(truth) | set(pred)]
    m = confusion(labels, truth, pred)
    per_class = prf(m)

    # verdict confusion matrix
    fig, ax = plt.subplots(figsize=(TWO_COL * 0.8, TWO_COL * 0.68))
    heatmap(ax, m, [SHORT[l] for l in labels], [SHORT[l] for l in labels], fontsize=8)
    ax.set_title(f"Verdict confusion matrix (n = {len(cases)}, accuracy {100 * ok / len(cases):.1f}%)")
    save(fig, out, "fig_verdict_confusion")

    # precision / recall / F1 per class
    fig, ax = plt.subplots(figsize=(TWO_COL * 0.8, 2.6))
    x = np.arange(len(labels))
    for k, (name, colour) in enumerate([("precision", BLUE), ("recall", ORANGE), ("f1", GREEN)]):
        ax.bar(x + (k - 1) * 0.26, [c[name] for c in per_class], 0.26, label=name.capitalize() if name != "f1" else "F1", color=colour)
    ax.set_xticks(x, [SHORT[l] for l in labels])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score")
    ax.legend(ncol=3, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    save(fig, out, "fig_verdict_prf")

    # verdict accuracy by case group
    groups = [g for g in GROUP_ORDER if any(c["group"] == g for c in cases)]
    gstats = []
    for g in groups:
        sub = [c for c in cases if c["group"] == g]
        k = sum(c["true_verdict"] == c["pred"]["status"] for c in sub)
        lo_g, hi_g = wilson(k, len(sub))
        gstats.append(dict(group=g, n=len(sub), correct=k, accuracy=k / len(sub), ci_low=lo_g, ci_high=hi_g))
    fig, ax = plt.subplots(figsize=(TWO_COL * 0.8, 2.6))
    acc = np.array([s["accuracy"] for s in gstats])
    err = np.array([[s["accuracy"] - s["ci_low"] for s in gstats], [s["ci_high"] - s["accuracy"] for s in gstats]])
    ax.bar(range(len(gstats)), acc, yerr=err, capsize=2, color=BLUE, error_kw=dict(lw=0.8))
    ax.set_xticks(range(len(gstats)), [f"{s['group'].replace('_', ' ')}\n(n={s['n']})" for s in gstats], rotation=30, ha="right")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Verdict accuracy (95% CI)")
    save(fig, out, "fig_verdict_by_group")

    # section matching: top-1 / top-3 by wording group, on cases that do not cite a section (so the wording alone decides)
    sec_groups = ["standard", "boundary", "paraphrase", "bangla"]
    sstats = []
    for g in sec_groups + ["all uncited"]:
        sub = [c for c in cases if c["true_section"] != "none" and not c["section_cited"] and (g == "all uncited" or c["group"] == g)]
        if not sub:
            continue
        t1 = sum(c["pred"]["section"] == c["true_section"] for c in sub)
        t3 = sum(c["true_section"] in c["pred"]["reason_top3"] for c in sub)
        sstats.append(dict(group=g, n=len(sub), top1=t1 / len(sub), top3=t3 / len(sub), top1_ci_low=wilson(t1, len(sub))[0], top1_ci_high=wilson(t1, len(sub))[1]))
    cited = [c for c in cases if c["true_section"] != "none" and c["section_cited"] and c["group"] != "mismatch"]
    if cited:
        t1 = sum(c["pred"]["section"] == c["true_section"] for c in cited)
        sstats.append(dict(group="all cited", n=len(cited), top1=t1 / len(cited), top3=sum(c["true_section"] in c["pred"]["top3"] for c in cited) / len(cited),
                           top1_ci_low=wilson(t1, len(cited))[0], top1_ci_high=wilson(t1, len(cited))[1]))
    fig, ax = plt.subplots(figsize=(TWO_COL * 0.8, 2.6))
    x = np.arange(len(sstats))
    ax.bar(x - 0.2, [s["top1"] for s in sstats], 0.4, label="Top-1", color=BLUE,
           yerr=np.array([[s["top1"] - s["top1_ci_low"] for s in sstats], [s["top1_ci_high"] - s["top1"] for s in sstats]]), capsize=2, error_kw=dict(lw=0.8))
    ax.bar(x + 0.2, [s["top3"] for s in sstats], 0.4, label="Top-3", color=ORANGE)
    ax.set_xticks(x, [f"{s['group']}\n(n={s['n']})" for s in sstats])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Section matching accuracy")
    ax.legend(ncol=2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    save(fig, out, "fig_section_accuracy")

    # section confusion matrix (appendix), cases without a citation
    sub = [c for c in cases if c["true_section"] != "none" and not c["section_cited"]]
    secs = sorted({c["true_section"] for c in sub}, key=lambda s: int(s.split("(")[0])) + ["none"]
    pred_secs = [c["pred"]["section"] for c in sub]
    secs = secs + [s for s in sorted(set(pred_secs)) if s not in secs]
    ms = confusion(secs, [c["true_section"] for c in sub], pred_secs)
    fig, ax = plt.subplots(figsize=(TWO_COL, TWO_COL * 0.9))
    heatmap(ax, ms, secs, secs, annotate=True, fontsize=5)
    ax.set_title(f"Section matching confusion matrix, receipts without a cited section (n = {len(sub)})")
    save(fig, out, "fig_section_confusion")

    write_csv(out / "table_verdict_per_class.csv", [dict(verdict=l, **{k: round(v, 4) if isinstance(v, float) else v for k, v in c.items()}) for l, c in zip(labels, per_class)])
    write_csv(out / "table_verdict_by_group.csv", [{k: round(v, 4) if isinstance(v, float) else v for k, v in s.items()} for s in gstats])
    write_csv(out / "table_section_accuracy.csv", [{k: round(v, 4) if isinstance(v, float) else v for k, v in s.items()} for s in sstats])
    write_csv(out / "stage_a_predictions.csv", [dict(id=c["id"], group=c["group"], reason=c["reason"], amount=c["amount"], cited=c["section_cited"],
                                                    true_section=c["true_section"], pred_section=c["pred"]["section"], true_verdict=c["true_verdict"],
                                                    pred_verdict=c["pred"]["status"], correct=c["true_verdict"] == c["pred"]["status"]) for c in cases])
    macro_f1 = float(np.mean([c["f1"] for c in per_class]))
    return dict(n=len(cases), verdict_accuracy=ok / len(cases), verdict_ci=[lo, hi], macro_f1=macro_f1, labels=labels, confusion=m.tolist(),
                per_class=dict(zip(labels, per_class)), by_group=gstats, section=sstats)


# ------------------------------------------------------------------------------------------------------------ stage B
def same_text(expected: str, got: str | None) -> bool:
    if not got:
        return False
    e, g = normalize(expected), normalize(got)
    if e in g or g in e:
        return True
    words = [w for w in e.split() if len(w) >= 3]
    return bool(words) and sum(w in g for w in words) / len(words) >= 0.6


def judge(field: str, expected: Any, got: Any) -> str:
    """ok | wrong | missed (a value was expected, none read) | spurious (none expected, one read)"""
    if expected is None:
        return "ok" if got in (None, "") else "spurious"
    if got in (None, ""):
        return "missed"
    if field in {"reason", "location", "vehicle", "receipt_number", "notes"}:
        return "ok" if same_text(str(expected), str(got)) else "wrong"
    return "ok" if str(expected) == str(got) else "wrong"


def stage_b(manifest: list[dict[str, Any]], folder: Path, passes: int | None) -> list[dict[str, Any]]:
    from app.core.config import get_settings
    from app.services.openrouter import AIError, OpenRouterClient
    from app.services.receipt_reader import extract_from_file
    from app.services.storage import sniff_type

    settings = get_settings()
    if passes:
        settings.ai_read_passes = passes
    if not settings.ai_enabled:
        sys.exit("No OPENROUTER_API_KEY configured in backend/.env.")
    client = OpenRouterClient(settings)
    results = []
    print(f"reading {len(manifest)} pictures with {settings.openrouter_model} ({settings.ai_read_passes} pass(es) each)")
    for i, item in enumerate(manifest, 1):
        data = (folder / item["file"]).read_bytes()
        t0 = time.time()
        try:
            ex = extract_from_file(client, data, sniff_type(data) or "image/jpeg", settings)
            got = {f: ex["fields"][f]["value"] for f in FIELDS}
            date_first = ex["fields"]["date"].get("first_reading", got["date"])
            usage = ex.get("usage") or {}
            err = None
        except AIError as e:
            got, usage, err, date_first = {f: None for f in FIELDS}, {}, f"{e.code}: {e}", None
        verdicts = {f: judge(f, item["expect"].get(f), got[f]) for f in FIELDS}
        results.append(dict(item, got=got, date_first=date_first, judged=verdicts, seconds=time.time() - t0, cost=float(usage.get("cost") or 0), error=err))
        print(f"  {i:>3}/{len(manifest)} {item['file']:<28} {'ok' if all(v == 'ok' for v in verdicts.values()) else 'errors: ' + ', '.join(f for f, v in verdicts.items() if v != 'ok')}")
    return results


def stage_b_report(results: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    per_field = []
    for f in FIELDS:
        k = sum(r["judged"][f] == "ok" for r in results)
        lo, hi = wilson(k, len(results))
        per_field.append(dict(field=f, n=len(results), correct=k, accuracy=k / len(results), ci_low=lo, ci_high=hi,
                              wrong=sum(r["judged"][f] == "wrong" for r in results), missed=sum(r["judged"][f] == "missed" for r in results),
                              spurious=sum(r["judged"][f] == "spurious" for r in results)))
    fig, ax = plt.subplots(figsize=(TWO_COL * 0.8, 2.6))
    acc = np.array([s["accuracy"] for s in per_field])
    err = np.array([[s["accuracy"] - s["ci_low"] for s in per_field], [s["ci_high"] - s["accuracy"] for s in per_field]])
    ax.bar(range(len(per_field)), acc, yerr=err, capsize=2, color=BLUE, error_kw=dict(lw=0.8))
    ax.set_xticks(range(len(per_field)), [s["field"].replace("_", " ") for s in per_field], rotation=30, ha="right")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel(f"Field accuracy (95% CI), n = {len(results)}")
    save(fig, out, "fig_field_accuracy")

    # accuracy by picture quality and language (all fields pooled)
    def pooled(key: str) -> list[dict[str, Any]]:
        rows = []
        for value in sorted({r[key] for r in results}):
            sub = [r for r in results if r[key] == value]
            k = sum(v == "ok" for r in sub for v in r["judged"].values())
            n = len(sub) * len(FIELDS)
            rows.append(dict(**{key: value}, receipts=len(sub), accuracy=k / n, ci_low=wilson(k, n)[0], ci_high=wilson(k, n)[1]))
        return rows

    by_kind, by_lang = pooled("kind"), pooled("lang")
    fig, axes = plt.subplots(1, 2, figsize=(TWO_COL * 0.8, 2.4), sharey=True, gridspec_kw=dict(width_ratios=[len(by_kind), len(by_lang)]))
    for ax, rows, key, title in [(axes[0], by_kind, "kind", "Picture quality"), (axes[1], by_lang, "lang", "Language")]:
        a = np.array([r["accuracy"] for r in rows])
        ax.bar(range(len(rows)), a, yerr=np.array([[r["accuracy"] - r["ci_low"] for r in rows], [r["ci_high"] - r["accuracy"] for r in rows]]), capsize=2, color=ORANGE, error_kw=dict(lw=0.8))
        ax.set_xticks(range(len(rows)), [f"{r[key]}\n(n={r['receipts']})" for r in rows])
        ax.set_title(title)
        ax.set_ylim(0, 1.08)
    axes[0].set_ylabel("Share of fields read correctly")
    save(fig, out, "fig_field_accuracy_by_condition")

    write_csv(out / "table_field_accuracy.csv", [{k: round(v, 4) if isinstance(v, float) else v for k, v in s.items()} for s in per_field])
    write_csv(out / "table_field_accuracy_by_condition.csv", [{k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()} for r in by_kind + by_lang])
    secs = [r["seconds"] for r in results]
    costs = [r["cost"] for r in results]
    return dict(n=len(results), per_field=per_field, by_kind=by_kind, by_lang=by_lang, mean_seconds=float(np.mean(secs)), median_seconds=float(np.median(secs)),
                mean_cost=float(np.mean(costs)), failed=sum(1 for r in results if r["error"]))


# ------------------------------------------------------------------------------------------------------------ stage C
def stage_c(results: list[dict[str, Any]], cases_by_id: dict[str, dict[str, Any]], out: Path) -> dict[str, Any]:
    rows = []
    for r in results:
        c = cases_by_id[r["case_id"]]
        got = r["got"]
        e2e = run_engine(got)
        rows.append(dict(case_id=c["id"], group=c["group"], true=c["true_verdict"], e2e=e2e["status"], engine_on_truth=c["pred"]["status"],
                         fields_ok=all(v == "ok" for v in r["judged"].values())))
    truth = [r["true"] for r in rows]
    pred = [r["e2e"] for r in rows]
    ok = sum(t == p for t, p in zip(truth, pred))
    labels = [v for v in VERDICTS if v in set(truth) | set(pred)]
    m = confusion(labels, truth, pred)
    fig, ax = plt.subplots(figsize=(TWO_COL * 0.8, TWO_COL * 0.68))
    heatmap(ax, m, [SHORT[l] for l in labels], [SHORT[l] for l in labels], fontsize=8)
    ax.set_title(f"End to end: receipt picture to verdict (n = {len(rows)}, accuracy {100 * ok / len(rows):.1f}%)")
    save(fig, out, "fig_endtoend_confusion")

    # where do the errors come from
    cats = Counter()
    for r in rows:
        right = r["e2e"] == r["true"]
        engine_right = r["engine_on_truth"] == r["true"]
        if right:
            cats["correct"] += 1
        elif engine_right:
            cats["reading error"] += 1
        elif r["fields_ok"]:
            cats["rule-engine error"] += 1
        else:
            cats["both"] += 1
    order = ["correct", "reading error", "rule-engine error", "both"]
    fig, ax = plt.subplots(figsize=(TWO_COL * 0.7, 1.4))
    left = 0
    for name, colour in zip(order, [GREEN, ORANGE, BLUE, GREY]):
        ax.barh([0], [cats[name]], left=left, color=colour, label=f"{name} ({cats[name]})")
        left += cats[name]
    ax.set_yticks([])
    ax.set_xlabel(f"Receipts (n = {len(rows)})")
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.45))
    ax.spines["left"].set_visible(False)
    save(fig, out, "fig_error_sources")
    write_csv(out / "stage_c_predictions.csv", rows)
    lo, hi = wilson(ok, len(rows))
    return dict(n=len(rows), accuracy=ok / len(rows), ci=[lo, hi], error_sources=dict(cats), labels=labels, confusion=m.tolist())


# ------------------------------------------------------------------------------------------------------------ stage D
BASELINE_PROMPT = """You check Bangladesh traffic fine receipts against the Road Transport Act 2018 fines guide below.
Given the details of one receipt, decide which section applies and give ONE verdict:
VALID                             the fine is within the maximum for the section
INVALID_FINE_TOO_HIGH             the fine is above the maximum for the section
VALID_BUT_EXCEPTION_POSSIBLE      within the limit, but a legal exception (ambulance, fire service, government vehicle, natural calamity: route permit rules only) may excuse the offence
INVALID_EXCEPTION_NOT_APPLICABLE  an exception was claimed but the law gives no exemption for this offence
INVALID_REASON_MISMATCH           the section number on the receipt does not match the offence written on it
NEEDS_MANUAL_REVIEW               cannot be decided: offence not in the guide, no amount, no Taka ceiling, or below a statutory minimum
Answer with JSON only: {"section": "<number or none>", "verdict": "<one of the verdicts>"}.

Fines guide (section: offence, maximum Tk, minimum Tk):
"""


def stage_d(results: list[dict[str, Any]], cases_by_id: dict[str, dict[str, Any]], out: Path, e2e: dict[str, Any]) -> dict[str, Any]:
    from app.core.config import get_settings
    from app.services.openrouter import AIError, OpenRouterClient, parse_json

    saved = out / "stage_d_predictions.csv"
    if "--reuse" in sys.argv and saved.exists():  # score the AI-alone answers saved by an earlier run instead of paying again
        with saved.open(encoding="utf8") as f:
            rows = [r for r in csv.DictReader(f) if r["case_id"] in {x["case_id"] for x in results}]
        print(f"stage D: reusing {len(rows)} saved baseline answers")
        return _stage_d_report(rows, out, e2e)
    settings = get_settings()
    client = OpenRouterClient(settings)
    table = "\n".join(f"{r.section}: {r.title}, max {r.max_fine if r.max_fine is not None else 'none stated'}, min {r.min_fine}" for r in DATASET.rules if r.matchable)
    rows = []
    for i, r in enumerate(results, 1):
        got = {k: v for k, v in r["got"].items() if v not in (None, "")}
        try:
            resp = client.complete([{"role": "system", "content": BASELINE_PROMPT + table}, {"role": "user", "content": json.dumps(got, ensure_ascii=False)}], max_tokens=200)
            answer = parse_json(resp.text)
            verdict = answer.get("verdict", "")
        except (AIError, ValueError) as e:
            verdict = f"error: {e}"
        rows.append(dict(case_id=r["case_id"], true=cases_by_id[r["case_id"]]["true_verdict"], baseline=verdict))
        print(f"  baseline {i:>3}/{len(results)}")
    write_csv(saved, rows)
    return _stage_d_report(rows, out, e2e)


def _stage_d_report(rows: list[dict[str, Any]], out: Path, e2e: dict[str, Any]) -> dict[str, Any]:
    ok = sum(r["true"] == r["baseline"] for r in rows)
    lo, hi = wilson(ok, len(rows))
    sys_ok = round(e2e["accuracy"] * e2e["n"])
    fig, ax = plt.subplots(figsize=(ONE_COL, 2.4))
    vals = [ok / len(rows), e2e["accuracy"]]
    cis = [(lo, hi), tuple(e2e["ci"])]
    ax.bar([0, 1], vals, yerr=np.array([[v - c[0] for v, c in zip(vals, cis)], [c[1] - v for v, c in zip(vals, cis)]]), capsize=3, color=[GREY, BLUE], error_kw=dict(lw=0.8))
    ax.set_xticks([0, 1], ["AI alone\n(no rule engine)", "AI + rule engine\n(this system)"])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Verdict accuracy (95% CI)")
    for x, v in enumerate(vals):
        ax.text(x, v + 0.04, f"{100 * v:.1f}%", ha="center", fontsize=7)
    save(fig, out, "fig_baseline_comparison")
    return dict(n=len(rows), baseline_accuracy=ok / len(rows), baseline_ci=[lo, hi], system_accuracy=e2e["accuracy"], system_correct=sys_ok)


# ------------------------------------------------------------------------------------------------------------ stage E
REVIEW = "NEEDS_MANUAL_REVIEW"
WRONG_TO_APPROVE = {"INVALID_FINE_TOO_HIGH", "INVALID_REASON_MISMATCH", "INVALID_EXCEPTION_NOT_APPLICABLE"}


def decision_quality(name: str, pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """How a system's answers split into: right, handed to a person (manual review), and confidently wrong.

    A "confidently wrong" answer is a firm verdict that differs from the correct one. Handing a case to manual review
    when a firm answer existed is a cost (no help), but not a wrong answer. A "false approval" tells the user a fine is
    valid when it is not, which is the most harmful kind of mistake.
    """
    n = len(pairs)
    correct = sum(t == p for t, p in pairs)
    abstained = sum(p == REVIEW and t != REVIEW for t, p in pairs)
    wrong = n - correct - abstained
    decided = [(t, p) for t, p in pairs if p != REVIEW]
    return dict(system=name, n=n, correct=correct, handed_to_review=abstained, confidently_wrong=wrong,
                accuracy=correct / n if n else 0.0, wrong_rate=wrong / n if n else 0.0,
                firm_answers=len(decided), accuracy_of_firm_answers=sum(t == p for t, p in decided) / len(decided) if decided else 0.0,
                false_approvals=sum(p == "VALID" and t in WRONG_TO_APPROVE for t, p in pairs))


def stage_e(cases: list[dict[str, Any]], c_rows: list[dict[str, Any]] | None, d_rows: list[dict[str, Any]] | None,
            kinds: dict[str, str] | None, out: Path) -> dict[str, Any]:
    systems = [decision_quality("Rule engine\n(typed fields)", [(c["true_verdict"], c["pred"]["status"]) for c in cases])]
    if c_rows:
        ids = {r["case_id"] for r in c_rows}
        systems.append(decision_quality("Rule engine, same cases\n(typed fields)", [(c["true_verdict"], c["pred"]["status"]) for c in cases if c["id"] in ids]))
        systems.append(decision_quality("AI + rule engine\n(receipt pictures)", [(r["true"], r["e2e"]) for r in c_rows]))
        if d_rows:
            systems.append(decision_quality("AI alone\n(receipt pictures)", [(r["true"], r["baseline"]) for r in d_rows]))
        if kinds:  # the same, leaving out the blurry pictures the AI declines to read
            keep = lambda r: kinds.get(r["case_id"]) != "blurry"  # noqa: E731
            systems.append(decision_quality("AI + rule engine, legible\npictures only", [(r["true"], r["e2e"]) for r in c_rows if keep(r)]))
            if d_rows:
                systems.append(decision_quality("AI alone, legible\npictures only", [(r["true"], r["baseline"]) for r in d_rows if keep(r)]))

    fig, ax = plt.subplots(figsize=(TWO_COL * 0.85, 0.55 * len(systems) + 1.1))
    y = np.arange(len(systems))[::-1]
    left = np.zeros(len(systems))
    for key, label, colour in [("correct", "Correct", GREEN), ("handed_to_review", "Handed to manual review", GREY), ("confidently_wrong", "Confidently wrong", ORANGE)]:
        share = np.array([s_[key] / s_["n"] for s_ in systems])
        ax.barh(y, share, left=left, color=colour, label=label, height=0.62)
        for yi, l, w, s_ in zip(y, left, share, systems):
            if w > 0.05:
                ax.text(l + w / 2, yi, f"{s_[key]}", ha="center", va="center", fontsize=7, color="white" if colour != GREY else "black")
        left += share
    ax.set_yticks(y, [f"{s_['system']}  (n={s_['n']})" for s_ in systems])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of cases")
    ax.legend(ncol=3, frameon=False, loc="lower center", bbox_to_anchor=(0.45, 1.0))
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, out, "fig_decision_quality")
    write_csv(out / "table_decision_quality.csv", [{**s_, "system": s_["system"].replace("\n", " "), "accuracy": round(s_["accuracy"], 4),
                                                     "wrong_rate": round(s_["wrong_rate"], 4), "accuracy_of_firm_answers": round(s_["accuracy_of_firm_answers"], 4)} for s_ in systems])
    return dict(systems=systems)


# ----------------------------------------------------------------------------------------------------------------- main
def arg(name: str, default: str | None = None) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def write_report(out: Path, summary: dict[str, Any]) -> None:
    a = summary["stage_a"]
    lines = ["# Evaluation results", "", f"Generated {datetime.now():%Y-%m-%d %H:%M}. Dataset: {DATASET.name}.", "",
             "## Stage A: rule engine on typed fields (no AI)", "",
             f"- Cases: {a['n']}", f"- Verdict accuracy: {100 * a['verdict_accuracy']:.1f}% (95% CI {100 * a['verdict_ci'][0]:.1f} to {100 * a['verdict_ci'][1]:.1f})",
             f"- Macro F1: {a['macro_f1']:.3f}", "", "| Verdict | Precision | Recall | F1 | Support |", "|---|---|---|---|---|"]
    for label, c in a["per_class"].items():
        lines.append(f"| {label} | {c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f} | {c['support']} |")
    lines += ["", "| Case group | n | Verdict accuracy |", "|---|---|---|"] + [f"| {g['group']} | {g['n']} | {100 * g['accuracy']:.1f}% |" for g in a["by_group"]]
    lines += ["", "| Section matching | n | Top-1 | Top-3 |", "|---|---|---|---|"] + [f"| {s['group']} | {s['n']} | {100 * s['top1']:.1f}% | {100 * s['top3']:.1f}% |" for s in a["section"]]
    if "stage_b" in summary:
        b = summary["stage_b"]
        lines += ["", "## Stage B: AI receipt reading", "", f"- Pictures: {b['n']} (failed: {b['failed']})", f"- Mean time per picture: {b['mean_seconds']:.1f} s, mean cost: ${b['mean_cost']:.4f}", "",
                  "| Field | Accuracy | Wrong | Missed | Spurious |", "|---|---|---|---|---|"]
        lines += [f"| {f['field']} | {100 * f['accuracy']:.1f}% | {f['wrong']} | {f['missed']} | {f['spurious']} |" for f in b["per_field"]]
    if "stage_c" in summary:
        c = summary["stage_c"]
        lines += ["", "## Stage C: end to end (picture to verdict)", "", f"- Accuracy: {100 * c['accuracy']:.1f}% (95% CI {100 * c['ci'][0]:.1f} to {100 * c['ci'][1]:.1f}), n = {c['n']}", f"- Error sources: {c['error_sources']}"]
    if "stage_d" in summary:
        d = summary["stage_d"]
        lines += ["", "## Stage D: baseline", "", f"- AI alone: {100 * d['baseline_accuracy']:.1f}% (95% CI {100 * d['baseline_ci'][0]:.1f} to {100 * d['baseline_ci'][1]:.1f})", f"- AI + rule engine: {100 * d['system_accuracy']:.1f}%"]
    if "stage_e" in summary:
        lines += ["", "## Decision quality: right, handed to a person, or confidently wrong", "",
                  "| System | n | Correct | Manual review | Confidently wrong | Accuracy of firm answers | False approvals |", "|---|---|---|---|---|---|---|"]
        lines += [f"| {x['system'].replace(chr(10), ' ')} | {x['n']} | {x['correct']} | {x['handed_to_review']} | {x['confidently_wrong']} | {100 * x['accuracy_of_firm_answers']:.1f}% | {x['false_approvals']} |"
                  for x in summary["stage_e"]["systems"]]
        lines += ["", "A *confidently wrong* answer is a firm verdict that differs from the correct one. A *false approval* is telling the user a wrong fine is valid."]
    lines += ["", "## Caveats", "", "- Correct answers were written from the PDFs by the tooling author, not a legal expert. Have them checked before publishing.",
              "- Cases and pictures are synthetic. Add real receipts for stronger evidence.", "- Confidence intervals are Wilson 95% intervals; with few cases they are wide."]
    (out / "results.md").write_text("\n".join(lines) + "\n", encoding="utf8")


def main() -> None:
    cases_path = Path(arg("--cases", str(EVAL_DIR / "cases.csv")))
    folder = Path(arg("--receipts", str(EVAL_DIR / "receipts")))
    out = Path(arg("--out", str(EVAL_DIR / "results")))
    out.mkdir(parents=True, exist_ok=True)
    cases = load_cases(cases_path)
    print(f"stage A: {len(cases)} cases through the rule engine")
    summary: dict[str, Any] = {"stage_a": stage_a(cases, out)}
    a = summary["stage_a"]
    print(f"  verdict accuracy {100 * a['verdict_accuracy']:.1f}%  macro F1 {a['macro_f1']:.3f}")

    if "--ai" in sys.argv:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf8"))
        if arg("--limit"):
            manifest = manifest[: int(arg("--limit"))]
        cases_by_id = {c["id"]: c for c in cases}
        raw = out / "stage_b_raw.json"
        if "--reuse" in sys.argv and raw.exists():  # score the readings saved by an earlier run instead of paying for new ones
            results = json.loads(raw.read_text(encoding="utf8"))[: len(manifest)]
            print(f"stage B: reusing {len(results)} saved readings from {raw.name}")
        else:
            results = stage_b(manifest, folder, int(arg("--passes") or 0) or None)
            raw.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf8")
        summary["stage_b"] = stage_b_report(results, out)
        summary["stage_c"] = stage_c(results, cases_by_id, out)
        print(f"  field accuracy {100 * np.mean([f['accuracy'] for f in summary['stage_b']['per_field']]):.1f}% (mean over fields), end to end {100 * summary['stage_c']['accuracy']:.1f}%")
        if "--baseline" in sys.argv:
            summary["stage_d"] = stage_d(results, cases_by_id, out, summary["stage_c"])
            print(f"  baseline (AI alone) {100 * summary['stage_d']['baseline_accuracy']:.1f}%")

    c_rows = d_rows = kinds = None
    if "stage_c" in summary:
        with (out / "stage_c_predictions.csv").open(encoding="utf8") as f:
            c_rows = list(csv.DictReader(f))
        kinds = {r["case_id"]: r["kind"] for r in results}
        if "stage_d" in summary:
            with (out / "stage_d_predictions.csv").open(encoding="utf8") as f:
                d_rows = list(csv.DictReader(f))
    summary["stage_e"] = stage_e(cases, c_rows, d_rows, kinds, out)

    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf8")
    write_report(out, summary)
    print(f"\nfigures, tables and results.md written to {out}")


if __name__ == "__main__":
    main()
