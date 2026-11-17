"""Follow-up message drafts for account managers. Drafts state observed numbers only."""

from __future__ import annotations

import pandas as pd

from .reconcile import BELOW, REVIEW


def _line(row: pd.Series) -> str:
    accuracy = "n/a" if pd.isna(row["Accuracy"]) else f"{row['Accuracy']:.1%}"
    expected = int(row["Expected Inventory Quantity"])
    reported = int(row["Reported Inventory Quantity"])
    return (
        f"- {row['Month']} | {row['Partner ID']} ({row['Country']}) | {row['Product ID']}: "
        f"expected {expected}, reported {reported}, accuracy {accuracy} ({row['Status']})"
    )


def build_drafts(results: pd.DataFrame, threshold: float) -> str:
    """One draft per account manager covering their flagged rows. Nothing is sent automatically."""
    flagged = results[results["Status"].isin([BELOW, REVIEW])]
    header = (
        "# Follow-up message drafts\n\n"
        "> DRAFTS FOR REVIEW. These have not been sent. Each draft lists observed numbers only; "
        "possible causes are not established by this run.\n"
    )
    if flagged.empty:
        return header + "\nNo rows were flagged, so no drafts were generated.\n"

    sections = [header]
    for manager, group in flagged.sort_values(["Account Manager", "Month", "Partner ID", "Product ID"]).groupby("Account Manager"):
        lines = "\n".join(_line(row) for _, row in group.iterrows())
        if manager == "UNASSIGNED":
            subject = "Routing needed: partner lines without an account manager"
            greeting = "Hello,"
            intro = "The following reconciliation lines have no assigned account manager and need routing:"
        else:
            subject = f"Inventory reconciliation follow-up: {len(group)} line(s) to confirm"
            greeting = f"Hello {manager},"
            intro = (f"The reconciliation run flagged {len(group)} partner-product line(s) "
                     f"below the {threshold:.0%} threshold or needing review:")
        sections.append(
            f"\n## Draft for {manager}\n\n"
            f"**Subject:** {subject}\n\n"
            f"{greeting}\n\n{intro}\n\n{lines}\n\n"
            "Please confirm the reported inventory for these lines, or tell us the counts you have verified. "
            "We are not assuming a cause; we would like your confirmation of the figures.\n\n"
            "Thank you.\n"
        )
    return "\n".join(sections)
