"""End-to-end run: load, validate, calculate, summarize, draft, write outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook as load_xlsx
from openpyxl.styles import Font

from .loader import load_input
from .messages import build_drafts
from .reconcile import RESULT_COLUMNS, product_summary, reconcile
from .summary import ai_summary, build_facts, deterministic_summary
from .validation import Issue, validate

DEFAULT_THRESHOLD = 0.95
DEFAULT_MODEL = "claude-haiku-5-5"


@dataclass
class RunResult:
    output_dir: Path
    results: pd.DataFrame
    issues: list[Issue]
    product: pd.DataFrame
    files: dict[str, Path] = field(default_factory=dict)


def _issues_frame(issues: list[Issue]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Excel Row": i.excel_row, "Check": i.check, "Severity": i.severity, "Message": i.message} for i in issues],
        columns=["Excel Row", "Check", "Severity", "Message"],
    )


def _write_workbook(path: Path, results: pd.DataFrame, product: pd.DataFrame, issues: pd.DataFrame) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        results.to_excel(writer, sheet_name="Results", index=False)
        product.to_excel(writer, sheet_name="Product Summary", index=False)
        issues.to_excel(writer, sheet_name="Validation Issues", index=False)

    workbook = load_xlsx(path)
    for sheet in workbook.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        sheet.freeze_panes = "A2"
        for column in sheet.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max(width + 2, 10), 60)
    results_sheet = workbook["Results"]
    headers = [cell.value for cell in results_sheet[1]]
    accuracy_col = headers.index("Accuracy") + 1
    for row in results_sheet.iter_rows(min_row=2, min_col=accuracy_col, max_col=accuracy_col):
        for cell in row:
            cell.number_format = "0.0%"
    workbook.save(path)


def run_pipeline(
    input_path: str | Path,
    output_dir: str | Path,
    threshold: float = DEFAULT_THRESHOLD,
    use_llm: bool = False,
    model: str = DEFAULT_MODEL,
    client=None,
) -> RunResult:
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be greater than 0 and at most 1")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    inp = load_input(input_path)
    work, issues = validate(inp)
    results = reconcile(work, threshold)
    product = product_summary(results)

    facts = build_facts(results, issues, threshold)
    summary_md = deterministic_summary(facts)
    if use_llm:
        try:
            if client is None:
                import anthropic  # optional dependency, needed only for --llm
                client = anthropic.Anthropic()
            narrative = ai_summary(facts, client, model)
        except Exception as exc:  # the deterministic outputs still stand
            narrative = f"AI summary unavailable: {exc}"
        summary_md += (
            "\n## AI summary\n\n" + narrative +
            "\n\n_Generated from the calculated facts above only. Verify before sharing._\n"
        )

    drafts_md = build_drafts(results, threshold)

    workbook_path = output_dir / "reconciliation_results.xlsx"
    summary_path = output_dir / "summary.md"
    drafts_path = output_dir / "follow_up_drafts.md"
    _write_workbook(workbook_path, results[RESULT_COLUMNS], product, _issues_frame(issues))
    summary_path.write_text(summary_md, encoding="utf-8")
    drafts_path.write_text(drafts_md, encoding="utf-8")

    return RunResult(
        output_dir=output_dir,
        results=results,
        issues=issues,
        product=product,
        files={"workbook": workbook_path, "summary": summary_path, "drafts": drafts_path},
    )
