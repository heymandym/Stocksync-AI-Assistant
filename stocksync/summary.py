"""Summaries of the calculated results. The deterministic summary is always produced; the AI summary is optional."""

from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from .reconcile import BELOW, INVALID, OK, REVIEW
from .validation import Issue

SYSTEM_PROMPT = (
    "You summarize inventory reconciliation results for an operations team. "
    "Use only the facts in the JSON you receive; do not invent numbers, partners or products. "
    "Separate observed discrepancies from possible causes, and do not present any cause as established. "
    "Suggest concrete verification steps. Keep the summary under 200 words."
)


def build_facts(results: pd.DataFrame, issues: list[Issue], threshold: float) -> dict:
    calculated = results[results["Status"] != INVALID]
    flagged = results[results["Status"].isin([BELOW, REVIEW])].copy()
    flagged["_sort"] = flagged["Accuracy"].fillna(float("inf"))
    worst = flagged.sort_values(["_sort", "Excel Row"]).head(10)
    return {
        "threshold": threshold,
        "total_rows": int(len(results)),
        "calculated_rows": int(len(calculated)),
        "invalid_rows": int((results["Status"] == INVALID).sum()),
        "status_counts": {
            OK: int((results["Status"] == OK).sum()),
            BELOW: int((results["Status"] == BELOW).sum()),
            REVIEW: int((results["Status"] == REVIEW).sum()),
        },
        "discrepancy_counts": {
            kind: int((calculated["Discrepancy"] == kind).sum())
            for kind in ("Matching", "Under-reported", "Over-reported")
        },
        "issue_counts": dict(Counter(f"{i.severity}:{i.check}" for i in issues)),
        "lowest_accuracy_rows": [
            {
                "excel_row": int(r["Excel Row"]),
                "month": r["Month"],
                "partner_id": r["Partner ID"],
                "country": r["Country"],
                "product_id": r["Product ID"],
                "account_manager": r["Account Manager"],
                "expected": int(r["Expected Inventory Quantity"]),
                "reported": int(r["Reported Inventory Quantity"]),
                "accuracy": None if pd.isna(r["Accuracy"]) else round(float(r["Accuracy"]), 4),
                "status": r["Status"],
                "note": r["Note"],
            }
            for _, r in worst.iterrows()
        ],
    }


def deterministic_summary(facts: dict) -> str:
    threshold = facts["threshold"]
    status = facts["status_counts"]
    disc = facts["discrepancy_counts"]
    lines = [
        "# Reconciliation summary",
        "",
        f"- Accuracy threshold: {threshold:.0%}",
        f"- Rows in input: {facts['total_rows']} (calculated: {facts['calculated_rows']}, "
        f"invalid and excluded: {facts['invalid_rows']})",
        f"- Status: OK {status[OK]}, below threshold {status[BELOW]}, review required {status[REVIEW]}",
        f"- Direction of differences: matching {disc['Matching']}, under-reported {disc['Under-reported']}, "
        f"over-reported {disc['Over-reported']}",
        "",
        "## Validation issues",
        "",
    ]
    if facts["issue_counts"]:
        for key, count in sorted(facts["issue_counts"].items()):
            lines.append(f"- {key}: {count}")
    else:
        lines.append("- None")

    lines += ["", "## Lowest-accuracy flagged rows (up to 10)", ""]
    if facts["lowest_accuracy_rows"]:
        lines += ["| Excel row | Month | Partner | Product | Expected | Reported | Accuracy | Status |",
                  "|---:|---|---|---|---:|---:|---:|---|"]
        for r in facts["lowest_accuracy_rows"]:
            acc = "n/a" if r["accuracy"] is None else f"{r['accuracy']:.1%}"
            lines.append(f"| {r['excel_row']} | {r['month']} | {r['partner_id']} | {r['product_id']} | "
                         f"{r['expected']} | {r['reported']} | {acc} | {r['status']} |")
    else:
        lines.append("No rows were flagged.")

    lines += ["", "> These are observed discrepancies. This run does not establish causes."]
    return "\n".join(lines) + "\n"


def ai_summary(facts: dict, client, model: str) -> str:
    """Ask a model to narrate the computed facts. The model receives facts only, never raw rows."""
    response = client.messages.create(
        model=model,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(facts, default=str)}],
    )
    return "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
