import pandas as pd
import pytest

from stocksync.reconcile import BELOW, INVALID, OK, REVIEW, accuracy, product_summary, reconcile


@pytest.mark.parametrize(
    "expected, reported, expected_accuracy",
    [
        (100, 100, 1.0),   # README table row 1
        (100, 80, 0.8),    # README table row 2
        (100, 120, 0.8),   # README table row 3: over-reporting is penalised the same way
    ],
)
def test_accuracy_matches_readme_examples(expected, reported, expected_accuracy):
    assert accuracy(expected, reported) == pytest.approx(expected_accuracy)


def _work(rows):
    """Build a working table the way validate() does, for rows that already passed validation."""
    frame = pd.DataFrame(rows)  # rows carry their own "valid" flag
    frame["units_sold"] = 0
    frame["account_manager"] = "AM-01"
    return frame


def _row(excel_row, expected, reported, valid=True):
    return {
        "excel_row": excel_row, "month": "2026-01", "partner_id": "P001", "country": "Germany",
        "product_id": "PR001", "expected": expected, "reported": reported,
        "valid": valid,
    }


def test_exactly_at_threshold_is_not_flagged():
    results = reconcile(_work([_row(2, 100, 95)]), threshold=0.95)
    assert results.loc[0, "Accuracy"] == pytest.approx(0.95)
    assert results.loc[0, "Status"] == OK


def test_just_below_threshold_is_flagged():
    results = reconcile(_work([_row(2, 100, 94)]), threshold=0.95)
    assert results.loc[0, "Status"] == BELOW


def test_negative_accuracy_is_preserved_and_flagged():
    results = reconcile(_work([_row(2, 10, 40)]), threshold=0.95)
    assert results.loc[0, "Accuracy"] == pytest.approx(-2.0)
    assert results.loc[0, "Status"] == REVIEW


def test_zero_expected_is_flagged_for_review_without_accuracy():
    results = reconcile(_work([_row(2, 0, 0)]), threshold=0.95)
    assert pd.isna(results.loc[0, "Accuracy"])
    assert results.loc[0, "Status"] == REVIEW


def test_invalid_rows_are_excluded_from_calculation():
    results = reconcile(_work([_row(2, 100, 80, valid=False)]), threshold=0.95)
    assert results.loc[0, "Status"] == INVALID
    assert pd.isna(results.loc[0, "Accuracy"])


@pytest.mark.parametrize("expected, reported, direction", [(100, 100, "Matching"),
                                                          (100, 80, "Under-reported"),
                                                          (100, 120, "Over-reported")])
def test_discrepancy_direction(expected, reported, direction):
    results = reconcile(_work([_row(2, expected, reported)]), threshold=0.95)
    assert results.loc[0, "Discrepancy"] == direction


def test_product_summary_shows_net_and_gross_so_offsets_are_visible():
    rows = [_row(2, 100, 110), _row(3, 100, 90)]  # +10 and -10 offset in the net figure
    results = reconcile(_work(rows), threshold=0.95)
    summary = product_summary(results).iloc[0]
    assert summary["Net Difference"] == 0
    assert summary["Gross Absolute Difference"] == 20
