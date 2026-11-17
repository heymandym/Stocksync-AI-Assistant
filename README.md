# StockSync AI
### Inventory Reconciliation Assistant

An AI-assisted workflow for monitoring inventory discrepancies and preparing partner follow-up messages for a fictional large European e-commerce company.

> **Project status:** Design stage. All demonstration data will be synthetic. This repository will not contain company data, internal systems, or confidential materials.

## Business Problem

Operations teams need to compare inventory reported by partners with expected inventory in their systems. Manually consolidating reports, checking discrepancies, and preparing messages for account managers takes time and can lead to inconsistent follow-up.

StockSync AI aims to support this workflow across **36 European countries**, including Germany, France, Italy, the Netherlands, and Belgium.

## Planned Workflow

1. Load sales and inventory data from Excel.
2. Validate required fields, reporting periods, and duplicate records.
3. Calculate inventory differences and reconciliation accuracy using fixed rules.
4. Flag results below a configurable accuracy threshold.
5. Use AI to summarize discrepancies and suggest checks.
6. Generate follow-up message drafts for the relevant account manager.

Messages will be available for review; the demonstration will not send them automatically.

## Dataset Structure

Each row represents one **month, partner, and product**. Inventory quantities must refer to the same reporting date and unit of measure.

| Column | Description |
|---|---|
| Month | Reporting month, formatted as `YYYY-MM` |
| Partner ID | Synthetic partner identifier, such as `P001` |
| Country | Partner’s assigned European country |
| Product ID | Synthetic product identifier |
| Units Sold | Units sold by the partner during the month |
| Expected Inventory Quantity | Inventory quantity recorded as expected in the company system |
| Reported Inventory Quantity | Actual inventory quantity reported by the partner |
| Inventory Difference | Reported quantity minus expected quantity |
| Inventory Reconciliation Accuracy | Accuracy calculated using the formula below |

Partner IDs and country assignments will remain consistent across reporting months. A separate partner-to-manager lookup will support message routing.

## Reconciliation Formula

For a positive expected inventory quantity:

\[
\text{Accuracy} =
1-\frac{|\text{Expected Inventory Quantity}-\text{Reported Inventory Quantity}|}
{\text{Expected Inventory Quantity}}
\]

**Excel formula**, using the column order above:

```excel
=IF(F2=0,"Review required",1-ABS(F2-G2)/F2)
```

Format the accuracy cell as a percentage. Do not multiply the formula by 100.

| Expected Quantity | Reported Quantity | Accuracy |
|---:|---:|---:|
| 100 | 100 | 100% |
| 100 | 80 | 80% |
| 100 | 120 | 80% |

Units Sold provides context for investigating inventory movements; it is not directly used in this formula.

**Calculation boundaries**

- Zero expected inventory is flagged for review.
- Missing or invalid inputs are flagged before calculation.
- Negative calculated accuracy is preserved and flagged for review, rather than silently changed to zero.
- Product-level results are shown separately. Partner and country aggregation rules remain to be finalized, including whether product discrepancies may offset one another.

## AI Responsibilities

The AI component will:

- Summarize calculated results in plain English.
- Highlight partners and products requiring attention.
- Suggest investigation steps based on available evidence.
- Draft concise follow-up messages for account managers.

Calculations and threshold checks will use deterministic logic. AI explanations will distinguish observed discrepancies from possible causes and will not present an unverified cause as fact.

## Planned Validation

The demonstration will include cases covering:

- Matching inventory quantities.
- Underreported and overreported inventory.
- Results exactly at the configured threshold.
- Zero, missing, or invalid inventory values.
- Duplicate records.
- Missing account-manager assignments.
- AI summaries and messages checked against calculated results.

## Portfolio Deliverables

- Synthetic Excel dataset covering 36 European countries.
- Reproducible workflow configuration or implementation.
- Documented prompts and calculation rules.
- Sample analysis and follow-up message drafts.
- Validation cases and recorded results.
- Short demonstration of the complete workflow.

## Intended Outcome

Demonstrate how business analysis, reliable calculations, and AI-generated communication can work together to support inventory reconciliation. Efficiency and accuracy improvements will be measured during testing rather than claimed in advance.
