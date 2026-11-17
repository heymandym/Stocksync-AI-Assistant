"""Deterministic reconciliation rules. No AI is involved in any number produced here."""

from __future__ import annotations

import pandas as pd

OK = "OK"
BELOW = "Below threshold"
REVIEW = "Review required"
INVALID = "Invalid input"

RESULT_COLUMNS = [
    "Excel Row", "Month", "Partner ID", "Country", "Product ID", "Account Manager",
    "Units Sold", "Expected Inventory Quantity", "Reported Inventory Quantity",
    "Inventory Difference", "Discrepancy", "Accuracy", "Status", "Note",
]


def accuracy(expected: int, reported: int) -> float:
    """README formula: 1 - |Expected - Reported| / Expected. Requires expected > 0."""
    return round(1 - abs(expected - reported) / expected, 10)


def reconcile(work: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Apply the fixed rules to every validated row. Returns one result row per input row."""
    limit = round(threshold, 10)
    records = []
    for _, row in work.iterrows():
        record = {
            "Excel Row": int(row["excel_row"]),
            "Month": row["month"],
            "Partner ID": row["partner_id"],
            "Country": row["country"],
            "Product ID": row["product_id"],
            "Account Manager": row["account_manager"],
            "Units Sold": row["units_sold"],
            "Expected Inventory Quantity": row["expected"],
            "Reported Inventory Quantity": row["reported"],
            "Inventory Difference": None,
            "Discrepancy": None,
            "Accuracy": None,
            "Status": INVALID,
            "Note": "Excluded from calculation; see Validation Issues",
        }
        if row["valid"]:
            expected, reported = int(row["expected"]), int(row["reported"])
            record["Expected Inventory Quantity"] = expected
            record["Reported Inventory Quantity"] = reported
            difference = reported - expected
            record["Inventory Difference"] = difference
            record["Discrepancy"] = (
                "Matching" if difference == 0 else "Under-reported" if difference < 0 else "Over-reported"
            )
            if expected == 0:
                record.update({"Status": REVIEW, "Note": "Zero expected inventory"})
            else:
                value = accuracy(expected, reported)
                record["Accuracy"] = value
                if value < 0:
                    record.update({"Status": REVIEW, "Note": "Negative accuracy preserved, not clipped to zero"})
                elif value < limit:
                    record.update({"Status": BELOW, "Note": f"Below {threshold:.0%} threshold"})
                else:
                    record.update({"Status": OK, "Note": ""})
        records.append(record)
    return pd.DataFrame(records, columns=RESULT_COLUMNS)


def product_summary(results: pd.DataFrame) -> pd.DataFrame:
    """Product-level totals. Net and gross differences are both shown so offsetting is visible."""
    valid = results[results["Status"] != INVALID].copy()
    if valid.empty:
        return pd.DataFrame(columns=["Product ID", "Rows", "Flagged Rows", "Expected Total",
                                     "Reported Total", "Net Difference", "Gross Absolute Difference"])
    valid["_flagged"] = valid["Status"].isin([BELOW, REVIEW])
    valid["_abs"] = valid["Inventory Difference"].abs()
    grouped = valid.groupby("Product ID", sort=True).agg(
        **{
            "Rows": ("Status", "size"),
            "Flagged Rows": ("_flagged", "sum"),
            "Expected Total": ("Expected Inventory Quantity", "sum"),
            "Reported Total": ("Reported Inventory Quantity", "sum"),
            "Net Difference": ("Inventory Difference", "sum"),
            "Gross Absolute Difference": ("_abs", "sum"),
        }
    )
    return grouped.reset_index()
