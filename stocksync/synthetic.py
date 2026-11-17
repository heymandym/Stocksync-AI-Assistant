"""Build a synthetic demonstration workbook. All names, IDs and quantities are fictional."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# 27 EU member states plus 9 other European countries = 36 (fictional scope).
EUROPEAN_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia", "Finland",
    "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
    "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
    "Albania", "Bosnia and Herzegovina", "Iceland", "Montenegro", "North Macedonia", "Norway", "Serbia",
    "Switzerland", "United Kingdom",
]
MONTHS = ["2026-01", "2026-02", "2026-03"]
PRODUCTS = [f"PR{n:03d}" for n in range(1, 9)]
PARTNER_COUNT = 72
MANAGER_COUNT = 12
COLUMNS = [
    "Month", "Partner ID", "Country", "Product ID", "Units Sold",
    "Expected Inventory Quantity", "Reported Inventory Quantity",
    "Inventory Difference", "Inventory Reconciliation Accuracy",
]


def _accuracy(expected, reported):
    if expected == 0:
        return None
    return round(1 - abs(expected - reported) / expected, 10)


def _row(month, partner, country, product, units, expected, reported):
    numeric = all(isinstance(v, int) for v in (expected, reported))
    return {
        "Month": month, "Partner ID": partner, "Country": country, "Product ID": product,
        "Units Sold": units, "Expected Inventory Quantity": expected,
        "Reported Inventory Quantity": reported,
        "Inventory Difference": reported - expected if numeric else None,
        "Inventory Reconciliation Accuracy": _accuracy(expected, reported) if numeric else None,
    }


def build_sample_workbook(path: str | Path, seed: int = 7) -> Path:
    """Write a workbook with an Inventory sheet, a Countries sheet and a Partner Managers sheet."""
    rng = np.random.default_rng(seed)
    rows = []
    for n in range(1, PARTNER_COUNT + 1):
        partner = f"P{n:03d}"
        country = EUROPEAN_COUNTRIES[(n - 1) // 2]  # two partners per country
        for month in MONTHS:
            for product in PRODUCTS:
                expected = int(rng.integers(20, 400))
                roll = rng.random()
                if roll < 0.70:
                    delta = 0
                elif roll < 0.80:
                    delta = int(round(expected * rng.uniform(-0.03, 0.03)))
                else:
                    delta = int(round(expected * rng.uniform(-0.25, 0.25)))
                reported = max(expected + delta, 0)
                rows.append(_row(month, partner, country, product, int(rng.integers(0, 80)), expected, reported))

    # Deliberate edge cases so every validation and status path appears in the demo.
    edge = [
        _row("2026-01", "P001", "Belgium", "PR090", 5, 100, 95),       # exactly 95% -> OK (threshold case)
        _row("2026-01", "P002", "Belgium", "PR091", 5, 0, 0),          # zero expected -> Review required
        _row("2026-01", "P002", "Belgium", "PR092", 5, 10, 40),        # accuracy -200% -> Review required
        _row("2026-01", "P003", "France", "PR093", 5, 100, 80),        # 80% -> Below threshold
        _row("2026-01", "P004", "France", "PR094", 5, None, 50),       # blank expected -> invalid
        _row("2026-01", "P005", "France", "PR095", 5, 50, "abc"),      # non-numeric -> invalid
        _row("2026-01", "P006", "Italy", "PR096", 5, 50, 50),          # fine
        _row("2026/01", "P006", "Italy", "PR097", 5, 50, 50),          # bad month format -> invalid
        _row("2026-01", "P099", "Germany", "PR098", 5, 50, 30),        # no account manager, 60% -> routed to UNASSIGNED
        _row("2026-01", "P007", "Narnia", "PR099", 5, 50, 50),         # unknown country -> invalid
    ]
    rows.extend(edge)
    rows.append(dict(rows[0]))  # exact duplicate of the first random row -> both copies excluded

    inventory = pd.DataFrame(rows, columns=COLUMNS)
    countries = pd.DataFrame({"Country": EUROPEAN_COUNTRIES})
    managers = pd.DataFrame({
        "Partner ID": [f"P{n:03d}" for n in range(1, PARTNER_COUNT + 1)],
        "Country": [EUROPEAN_COUNTRIES[(n - 1) // 2] for n in range(1, PARTNER_COUNT + 1)],
        "Account Manager": [f"AM-{((n - 1) % MANAGER_COUNT) + 1:02d}" for n in range(1, PARTNER_COUNT + 1)],
    })

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        inventory.to_excel(writer, sheet_name="Inventory", index=False)
        countries.to_excel(writer, sheet_name="Countries", index=False)
        managers.to_excel(writer, sheet_name="Partner Managers", index=False)
    return path
