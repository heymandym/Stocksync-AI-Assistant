import pandas as pd

from stocksync.loader import REQUIRED_COLUMNS, ReconciliationInput
from stocksync.validation import UNASSIGNED, validate


def _frame(rows):
    base = {
        "Month": "2026-01", "Partner ID": "P001", "Country": "Germany", "Product ID": "PR001",
        "Units Sold": 5, "Expected Inventory Quantity": 100, "Reported Inventory Quantity": 100,
    }
    data = []
    for overrides in rows:
        row = dict(base)
        row.update(overrides)
        data.append(row)
    frame = pd.DataFrame(data, columns=REQUIRED_COLUMNS)
    return frame


def _checks(issues, excel_row):
    return {i.check for i in issues if i.excel_row == excel_row}


def test_clean_row_has_no_issues_and_is_valid():
    inp = ReconciliationInput(data=_frame([{}]), countries={"Germany"}, account_managers={"P001": "AM-01"})
    work, issues = validate(inp)
    assert issues == []
    assert bool(work.loc[0, "valid"]) is True


def test_missing_value_is_an_error():
    inp = ReconciliationInput(data=_frame([{"Partner ID": None}]), countries=None, account_managers={"P001": "AM-01"})
    work, issues = validate(inp)
    assert "missing_value" in _checks(issues, 2)
    assert bool(work.loc[0, "valid"]) is False


def test_non_numeric_and_negative_quantities_are_errors():
    inp = ReconciliationInput(
        data=_frame([{"Reported Inventory Quantity": "abc"}, {"Expected Inventory Quantity": -5}]),
        countries=None, account_managers={"P001": "AM-01"},
    )
    work, issues = validate(inp)
    assert "invalid_quantity" in _checks(issues, 2)
    assert "invalid_quantity" in _checks(issues, 3)
    assert not work["valid"].any()


def test_bad_month_format_is_an_error():
    inp = ReconciliationInput(data=_frame([{"Month": "2026/01"}]), countries=None, account_managers={"P001": "AM-01"})
    _, issues = validate(inp)
    assert "invalid_month" in _checks(issues, 2)


def test_unknown_country_is_an_error_when_country_list_is_given():
    inp = ReconciliationInput(data=_frame([{"Country": "Narnia"}]), countries={"Germany"}, account_managers={"P001": "AM-01"})
    _, issues = validate(inp)
    assert "unknown_country" in _checks(issues, 2)


def test_duplicates_exclude_every_copy():
    inp = ReconciliationInput(data=_frame([{}, {}]), countries=None, account_managers={"P001": "AM-01"})
    work, issues = validate(inp)
    assert {i.excel_row for i in issues if i.check == "duplicate_record"} == {2, 3}
    assert not work["valid"].any()


def test_missing_account_manager_is_a_warning_and_routes_to_unassigned():
    inp = ReconciliationInput(data=_frame([{"Partner ID": "P999"}]), countries=None, account_managers={})
    work, issues = validate(inp)
    issue = next(i for i in issues if i.check == "missing_account_manager")
    assert issue.severity == "warning"
    assert work.loc[0, "account_manager"] == UNASSIGNED
    assert bool(work.loc[0, "valid"]) is True


def test_zero_expected_is_a_warning_not_an_error():
    inp = ReconciliationInput(data=_frame([{"Expected Inventory Quantity": 0, "Reported Inventory Quantity": 0}]),
                              countries=None, account_managers={"P001": "AM-01"})
    work, issues = validate(inp)
    assert "zero_expected" in _checks(issues, 2)
    assert bool(work.loc[0, "valid"]) is True


def test_provided_difference_that_disagrees_is_a_warning():
    frame = _frame([{}])
    frame["Inventory Difference"] = [7]  # recalculated value is 0
    inp = ReconciliationInput(data=frame, countries=None, account_managers={"P001": "AM-01"})
    _, issues = validate(inp)
    assert "difference_mismatch" in _checks(issues, 2)
