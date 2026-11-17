"""Read the reconciliation workbook and its lookup sheets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATA_SHEET = "Inventory"
COUNTRY_SHEET = "Countries"
MANAGER_SHEET = "Partner Managers"

REQUIRED_COLUMNS = [
    "Month",
    "Partner ID",
    "Country",
    "Product ID",
    "Units Sold",
    "Expected Inventory Quantity",
    "Reported Inventory Quantity",
]


@dataclass
class ReconciliationInput:
    """Raw rows plus the lookup data read from the same workbook."""

    data: pd.DataFrame
    countries: set[str] | None
    account_managers: dict[str, str] = field(default_factory=dict)


def clean_text(value) -> str | None:
    """Return a stripped string, or None for blank cells."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def load_input(path: str | Path) -> ReconciliationInput:
    """Load the Inventory sheet plus the optional Countries and Partner Managers sheets."""
    path = Path(path)
    workbook = pd.ExcelFile(path)
    if DATA_SHEET not in workbook.sheet_names:
        raise ValueError(f"Workbook has no '{DATA_SHEET}' sheet: {path}")

    # dtype=object keeps raw cell values so validation can see bad input.
    data = pd.read_excel(workbook, sheet_name=DATA_SHEET, dtype=object)
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"'{DATA_SHEET}' sheet is missing required columns: {missing}")

    countries = None
    if COUNTRY_SHEET in workbook.sheet_names:
        country_df = pd.read_excel(workbook, sheet_name=COUNTRY_SHEET, dtype=object)
        column = "Country" if "Country" in country_df.columns else country_df.columns[0]
        countries = {name for name in (clean_text(v) for v in country_df[column]) if name}

    managers: dict[str, str] = {}
    if MANAGER_SHEET in workbook.sheet_names:
        manager_df = pd.read_excel(workbook, sheet_name=MANAGER_SHEET, dtype=object)
        for _, row in manager_df.iterrows():
            partner = clean_text(row.get("Partner ID"))
            manager = clean_text(row.get("Account Manager"))
            if partner and manager:
                managers[partner] = manager

    return ReconciliationInput(data=data, countries=countries, account_managers=managers)
