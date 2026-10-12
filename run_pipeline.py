#!/usr/bin/env python3
"""Command-line entry point for the AP Agent prototype.

Usage:
    python run_pipeline.py                 # run on the bundled sample data
    python run_pipeline.py --json out.json # also write machine-readable results
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap_agent.pipeline import run, format_report  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def to_jsonable(run_result):
    out = []
    for r in run_result["results"]:
        inv, match, dec = r["invoice"], r["match"], r["decision"]
        out.append({
            "source_file": os.path.basename(inv.source_file),
            "vendor_name": inv.vendor_name,
            "vendor_id": inv.vendor_id,
            "invoice_no": inv.invoice_no,
            "invoice_date": inv.invoice_date,
            "po_number": inv.po_number,
            "currency": inv.currency,
            "total": inv.total,
            "extraction_confidence": inv.field_confidence.get("_overall"),
            "validation_issues": inv.validation_issues,
            "match_status": match.status,
            "discrepancies": [d.__dict__ for d in match.discrepancies],
            "decision_status": dec.status,
            "approvers": dec.approvers,
            "decision_reason": dec.reason,
        })
    return {
        "summary": run_result["summary"],
        "invoices": out,
        "postings": [p.__dict__ for p in run_result["postings"]],
        "payment_batch": [p.__dict__ for p in run_result["payment_batch"]],
    }


def main():
    ap = argparse.ArgumentParser(description="Run the Accounts Payable Agent pipeline.")
    ap.add_argument("--data", default=os.path.join(HERE, "data"))
    ap.add_argument("--invoices", default=os.path.join(HERE, "data", "invoices"))
    ap.add_argument("--json", default=None, help="write results to this JSON path")
    args = ap.parse_args()

    result = run(args.data, args.invoices)
    print(format_report(result))

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(to_jsonable(result), fh, indent=2)
        print(f"\nJSON results written to {args.json}")


if __name__ == "__main__":
    main()
