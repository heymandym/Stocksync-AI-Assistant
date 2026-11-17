"""Row-level validation. Rows with error-level issues are excluded from calculation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd

from .loader import ReconciliationInput, clean_text

UNASSIGNED = "UNASSIGNED"
MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
EXPECTED = "Expected Inventory Quantity"
REPORTED = "Reported Inventory Quantity"
DIFFERENCE = "Inventory Difference"


@dataclass(frozen=True)
class Issue:
    excel_row: int
    check: str
    severity: str  # "error" excludes the row; "warning" keeps it
    message: str


def _to_number(value) -> tuple[float | None, str | None]:
    """Parse a cell as a whole number. Returns (number, problem) where problem is None on success."""
    if value is None or (not isinstance(value, bool) and pd.isna(value)):
        return None, "missing"
    if isinstance(value, str) and not value.strip():
        return None, "missing"
    if isinstance(value, bool):
        return None, "not a number"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, "not a number"
    if not math.isfinite(number):
        return None, "not a number"
    if not number.is_integer():
        return None, "not a whole number"
    return number, None


def validate(inp: ReconciliationInput) -> tuple[pd.DataFrame, list[Issue]]:
    """Check every input row. Returns a working table (one row per input row) and the issues found."""
    issues: list[Issue] = []
    rows: list[dict] = []

    def add(excel_row: int, check: str, severity: str, message: str) -> None:
        issues.append(Issue(excel_row, check, severity, message))

    for index, raw in inp.data.iterrows():
        excel_row = int(index) + 2  # row 1 is the header
        month = clean_text(raw["Month"])
        partner = clean_text(raw["Partner ID"])
        country = clean_text(raw["Country"])
        product = clean_text(raw["Product ID"])

        for label, value in (("Month", month), ("Partner ID", partner),
                             ("Country", country), ("Product ID", product)):
            if value is None:
                add(excel_row, "missing_value", "error", f"{label} is blank")

        if month is not None and not MONTH_PATTERN.match(month):
            add(excel_row, "invalid_month", "error", f"Month '{month}' is not YYYY-MM")

        if country and inp.countries is not None and country not in inp.countries:
            add(excel_row, "unknown_country", "error", f"Country '{country}' is not in the Countries sheet")

        expected, expected_problem = _to_number(raw[EXPECTED])
        reported, reported_problem = _to_number(raw[REPORTED])
        for label, problem in ((EXPECTED, expected_problem), (REPORTED, reported_problem)):
            if problem == "missing":
                add(excel_row, "missing_value", "error", f"{label} is blank")
            elif problem:
                add(excel_row, "invalid_quantity", "error", f"{label} is {problem}")
        for label, value in ((EXPECTED, expected), (REPORTED, reported)):
            if value is not None and value < 0:
                add(excel_row, "invalid_quantity", "error", f"{label} is negative")

        units, units_problem = _to_number(raw["Units Sold"])
        if units_problem:
            add(excel_row, "units_sold", "warning", f"Units Sold is {units_problem}; not used in calculation")

        if (expected is not None and reported is not None and DIFFERENCE in inp.data.columns):
            provided, provided_problem = _to_number(raw[DIFFERENCE])
            if provided_problem is None and provided != reported - expected:
                add(excel_row, "difference_mismatch", "warning",
                    f"Provided Inventory Difference {int(provided)} differs from recalculated {int(reported - expected)}")

        manager = inp.account_managers.get(partner) if partner else None
        if partner and manager is None:
            add(excel_row, "missing_account_manager", "warning",
                f"Partner '{partner}' has no account manager; routed to {UNASSIGNED}")

        rows.append({
            "excel_row": excel_row,
            "month": month,
            "partner_id": partner,
            "country": country,
            "product_id": product,
            "units_sold": int(units) if units is not None else None,
            "expected": int(expected) if expected is not None else None,
            "reported": int(reported) if reported is not None else None,
            "account_manager": manager or UNASSIGNED,
        })

    work = pd.DataFrame(rows)
    for column in ("units_sold", "expected", "reported"):
        work[column] = work[column].astype("Int64")  # whole numbers, with <NA> for blanks

    # Duplicates: every row sharing a (Month, Partner ID, Product ID) key is excluded, not silently dropped.
    if not work.empty:
        keyed = work.dropna(subset=["month", "partner_id", "product_id"])
        key_counts = keyed.groupby(["month", "partner_id", "product_id"])["excel_row"].transform("size")
        for excel_row in keyed.loc[key_counts > 1, "excel_row"]:
            add(int(excel_row), "duplicate_record", "error",
                "Duplicate Month / Partner ID / Product ID; all copies excluded until resolved")

    error_rows = {issue.excel_row for issue in issues if issue.severity == "error"}
    work["valid"] = ~work["excel_row"].isin(error_rows)

    zero_expected = (work["expected"] == 0).fillna(False).astype(bool)
    for _, row in work[work["valid"] & zero_expected].iterrows():
        add(int(row["excel_row"]), "zero_expected", "warning", "Expected inventory is zero; accuracy cannot be calculated")

    issues.sort(key=lambda issue: (issue.excel_row, issue.check))
    return work, issues
