#!/usr/bin/env python3
"""Reproduce the synthetic StockSync reconciliation without external packages."""
import argparse
import json
from pathlib import Path


def reconcile(data):
    results = []
    for snapshot in sorted(data["partner_inventory"], key=lambda x: x["as_of_date"]):
        partner, product, date = (snapshot[k] for k in ("partner_id", "product_id", "as_of_date"))
        opening = sum(
            m["quantity_signed"] for m in data["inventory_movements"]
            if m["partner_id"] == partner and m["product_id"] == product
            and m["movement_date"] <= date
        )
        accepted = {}
        for sale in data["sales"]:
            if (sale["partner_id"], sale["product_id"]) != (partner, product):
                continue
            if sale["status"] != "ACCEPTED" or sale["submitting_date"] > date:
                continue
            key = tuple(sale[k] for k in
                        ("partner_id", "product_id", "serial_number", "contract_po", "reporting_date"))
            accepted.setdefault(key, sale)
        theoretical = opening - sum(s["quantity"] for s in accepted.values())
        actual = snapshot["actual_quantity"]
        variance = theoretical - actual
        accuracy = None if theoretical <= 0 else 1 - abs(variance) / theoretical
        results.append({
            "as_of_date": date, "partner_id": partner, "product_id": product,
            "theoretical_quantity": theoretical, "actual_quantity": actual,
            "variance": variance, "accuracy": accuracy,
            "status": "REVIEW" if accuracy is None else
                      ("BELOW_TARGET" if accuracy < 0.90 else "ACHIEVED_TARGET")
        })
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="data/mock/StockSync_mock_api_v2.json")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    results = reconcile(data)
    expected = {row["as_of_date"]: row for row in data.get("expected_demo_results", [])}
    checked = 0
    for row in results:
        reference = expected.get(row["as_of_date"])
        if reference is not None:
            checked += 1
            for field in ("theoretical_quantity", "actual_quantity", "variance"):
                assert row[field] == reference[field], f"{row['as_of_date']}: {field} mismatch"
        accuracy = "review" if row["accuracy"] is None else f"{row['accuracy']:.1%}"
        print(f"{row['as_of_date']} {row['partner_id']} {row['product_id']}: "
              f"theoretical={row['theoretical_quantity']} actual={row['actual_quantity']} "
              f"variance={row['variance']} accuracy={accuracy} {row['status']}")
    if checked == len(results) and checked > 0:
        print(f"PASS: {checked} snapshots checked against the fixture")
    else:
        print(f"Checked {checked} of {len(results)} snapshots against expected results; no full PASS")


if __name__ == "__main__":
    main()
