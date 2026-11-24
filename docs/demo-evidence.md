# Fabric demo evidence

## What I checked

- In `Demo AI Workspace`, a manual run of `PL_StockSync_Reconciliation` completed the HTTP Copy data → notebook flow into `LH_Reconciliation`.
- The notebook showed Bronze, Silver and Gold tables. For 2026-11-22, `gold_inventory_reconciliation` showed theoretical stock **86**, reported stock **70**, variance **16**, and accuracy **81.4%**. The alert was below the 90% target.
- The daily 08:00 schedule is marked **Active** in the Amsterdam/Berlin time zone, but its card still says **Last successful update: Not available**. A scheduled run has not yet been verified.
- The Fabric AI call returned `FTL64 SKU Not Supported`, so `ai_message` was null. The example manager message was drafted separately with ChatGPT; no email was sent.

## Check the example

Use [v2 JSON](../data/mock/StockSync_mock_api_v2.json) and run `python scripts/reconcile_demo.py` from the repository root. ST-002 is rejected; ST-003 is the accepted correction; ST-004 repeats the same sale and is counted once. The three snapshots produce **90 vs 86** on November 20, **86 vs 86** on November 21, and **86 vs 70** on November 22.

## Still to build

Export the Fabric notebook and pipeline, verify a scheduled run, and add an analyst review step and approved email delivery. These are not part of the current runnable repository.
