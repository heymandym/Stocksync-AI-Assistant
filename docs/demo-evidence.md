# Demo evidence and interview walkthrough

## Observed in Microsoft Fabric

- Workspace: `Demo AI Workspace`; Lakehouse: `LH_Reconciliation`.
- Pipeline: `PL_StockSync_Reconciliation`, with HTTP **Copy data → Notebook** success dependency. A manual run completed successfully.
- Notebook: `NB_Stocksync_reconciliation`. Its table listing showed `bronze_inventory_movements`, `bronze_partner_inventory`, `bronze_st`, `silver_st_validated`, and `gold_inventory_reconciliation`. Later cells created `gold_manager_alerts`, `gold_manager_messages_routed`, and `gold_ai_prompt_requests`.
- The displayed Gold snapshot for 2026-11-22 showed theoretical 86, actual 70, variance 16 and accuracy 0.813953488372093 (81.4%). The alert table flagged `BELOW_TARGET` at 0.90.
- The 08:00 daily pipeline schedule now displays **Active** in the Amsterdam/Berlin time zone. Its card shows **Last successful update: Not available**, so a scheduled run has not yet been verified. The successful run described above was manual.
- Fabric's built-in AI call returned `FTL64 SKU Not Supported`, with `ai_message=NULL`. The manager draft in the README was created separately with ChatGPT; no outgoing manager email was observed.

## Demo sequence

1. Open the synthetic [v2 JSON](../data/mock/StockSync_mock_api_v2.json) and explain sale date versus submission date, rejected ST-002, corrected ST-003 and duplicate ST-004.
2. Show the Fabric pipeline's Copy data success link to the notebook and its successful manual run.
3. In the Lakehouse notebook, list Bronze, Silver and Gold tables; display Gold snapshots and the below-target alert.
4. Run `python scripts/reconcile_demo.py` locally to independently verify the fixture's quantities.
5. Show the prepared AI prompt facts and the manager draft. Explain that quantities are deterministic and the draft needs analyst approval.
6. Show the active 08:00 schedule and explain that its first successful scheduled run still needs verification. Describe the planned reviewer view, supported model integration, audit history and email action.

## Validation cases

| Case | Expected effect |
| --- | --- |
| ST-001 accepted on 2026-11-20 | Opening 100 decreases to theoretical 90. |
| ST-002 rejected | No decrease; reported 86 produces variance 4. |
| ST-003 accepted on 2026-11-21 for a 2026-11-20 sale | Theoretical falls to 86 on submission date. |
| ST-004 duplicate accepted sale | Deduplicated; no second four-unit decrease. |
| 2026-11-21 partner snapshot | 86 versus 86, accuracy 100%. |
| 2026-11-22 partner snapshot | 86 versus 70, 81.4% accuracy, below 90%. |

The local checker asserts each expected quantity and variance from the fixture. This is a small synthetic case, not a measured production benchmark.

## Next implementation steps

Export the Fabric notebook and pipeline configuration with environment parameters; add independent data quality assertions, persistent run history, an analyst review view, a supported LLM endpoint with numeric guardrails, and a gated email activity. Verify the next scheduled run, then test idempotency and manager routing before enabling email delivery.
