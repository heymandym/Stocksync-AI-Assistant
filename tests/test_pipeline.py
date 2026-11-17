import json
from types import SimpleNamespace

import pandas as pd

from stocksync.cli import main
from stocksync.pipeline import run_pipeline
from stocksync.reconcile import BELOW, INVALID, OK, REVIEW
from stocksync.synthetic import COLUMNS, build_sample_workbook


def _status(results, partner, product):
    row = results[(results["Partner ID"] == partner) & (results["Product ID"] == product)]
    assert len(row) == 1, (partner, product)
    return row.iloc[0]["Status"]


def test_sample_run_covers_every_status_and_writes_outputs(tmp_path):
    workbook = build_sample_workbook(tmp_path / "in" / "sample.xlsx")
    result = run_pipeline(workbook, tmp_path / "out", threshold=0.95)

    assert set(result.files) == {"workbook", "summary", "drafts"}
    for path in result.files.values():
        assert path.exists()

    results = result.results
    assert len(results) == 72 * 8 * 3 + 10 + 1  # random rows + edge cases + one duplicate copy

    assert _status(results, "P001", "PR090") == OK        # exactly 95%
    assert _status(results, "P002", "PR091") == REVIEW    # zero expected
    assert _status(results, "P002", "PR092") == REVIEW    # negative accuracy
    assert _status(results, "P003", "PR093") == BELOW     # 80%
    assert _status(results, "P004", "PR094") == INVALID   # blank expected
    assert _status(results, "P005", "PR095") == INVALID   # non-numeric reported
    assert _status(results, "P006", "PR097") == INVALID   # bad month format
    assert _status(results, "P007", "PR099") == INVALID   # unknown country
    assert results[results["Account Manager"] == "UNASSIGNED"]["Partner ID"].tolist() == ["P099"]

    issues = pd.read_excel(result.files["workbook"], sheet_name="Validation Issues")
    assert {"duplicate_record", "missing_value", "invalid_quantity", "invalid_month",
            "unknown_country", "missing_account_manager", "zero_expected"} <= set(issues["Check"])


def test_drafts_are_marked_unsent_and_state_no_causes(tmp_path):
    workbook = build_sample_workbook(tmp_path / "sample.xlsx")
    result = run_pipeline(workbook, tmp_path / "out")
    drafts = result.files["drafts"].read_text(encoding="utf-8")
    assert "have not been sent" in drafts
    assert "Routing needed" in drafts  # P099 is flagged and has no account manager
    assert "not assuming a cause" in drafts


def test_workbook_accuracy_is_formatted_as_percentage(tmp_path):
    import openpyxl

    workbook = build_sample_workbook(tmp_path / "sample.xlsx")
    result = run_pipeline(workbook, tmp_path / "out")
    sheet = openpyxl.load_workbook(result.files["workbook"])["Results"]
    headers = [c.value for c in sheet[1]]
    col = headers.index("Accuracy") + 1
    assert sheet.cell(row=2, column=col).number_format == "0.0%"


def test_sample_workbook_has_expected_structure(tmp_path):
    path = build_sample_workbook(tmp_path / "sample.xlsx")
    inventory = pd.read_excel(path, sheet_name="Inventory")
    countries = pd.read_excel(path, sheet_name="Countries")
    assert list(inventory.columns) == COLUMNS
    assert len(countries) == 36


class FakeClient:
    """Stands in for anthropic.Anthropic and records what would have been sent."""

    def __init__(self):
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        block = SimpleNamespace(type="text", text="Plain-English summary of the computed facts.")
        return SimpleNamespace(content=[block])


def test_llm_step_receives_only_aggregated_facts(tmp_path):
    workbook = build_sample_workbook(tmp_path / "sample.xlsx")
    client = FakeClient()
    result = run_pipeline(workbook, tmp_path / "out", use_llm=True, client=client)

    assert len(client.calls) == 1
    payload = json.loads(client.calls[0]["messages"][0]["content"])
    assert "lowest_accuracy_rows" in payload
    assert len(payload["lowest_accuracy_rows"]) <= 10
    assert "Plain-English summary" in result.files["summary"].read_text(encoding="utf-8")


def test_llm_failure_keeps_deterministic_outputs(tmp_path):
    class Broken:
        messages = SimpleNamespace(create=lambda **_: (_ for _ in ()).throw(RuntimeError("no network")))

    workbook = build_sample_workbook(tmp_path / "sample.xlsx")
    result = run_pipeline(workbook, tmp_path / "out", use_llm=True, client=Broken())
    text = result.files["summary"].read_text(encoding="utf-8")
    assert "AI summary unavailable: no network" in text
    assert "# Reconciliation summary" in text


def test_cli_run_and_bad_threshold(tmp_path, capsys):
    workbook = build_sample_workbook(tmp_path / "sample.xlsx")
    assert main(["run", "--input", str(workbook), "--out", str(tmp_path / "cli")]) == 0
    assert "Wrote workbook" in capsys.readouterr().out
    assert main(["run", "--input", str(workbook), "--out", str(tmp_path / "cli"), "--threshold", "1.5"]) == 2
