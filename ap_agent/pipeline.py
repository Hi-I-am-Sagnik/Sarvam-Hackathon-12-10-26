"""End-to-end orchestration: extract -> validate -> match -> approve -> post.

`run()` processes a list of invoice files and returns a result object plus a
human-readable report. It is deliberately linear and side-effect-free apart
from the mock ERP ledger, so it is easy to test and extend.
"""
from __future__ import annotations

import glob
import json
import os

from .approval import decide_approval
from .config import CONFIG
from .erp import MockERP
from .extraction import extract_invoice
from .matching import duplicate_key, match_invoice
from .models import PurchaseOrder, POLine
from .validation import has_blocking_issue, validate


def load_vendors(path: str) -> tuple[dict, dict]:
    with open(path) as fh:
        vendors = json.load(fh)
    by_gstin = {v["gstin"]: v for v in vendors}
    by_name = {v["name"].strip().lower(): v for v in vendors}
    by_id = {v["vendor_id"]: v for v in vendors}
    return by_gstin, by_name, by_id


def load_pos(path: str) -> dict:
    with open(path) as fh:
        raw = json.load(fh)
    out = {}
    for p in raw:
        out[p["po_number"]] = PurchaseOrder(
            po_number=p["po_number"],
            vendor_id=p["vendor_id"],
            vendor_name=p["vendor_name"],
            currency=p.get("currency", "INR"),
            lines=[POLine(**l) for l in p["lines"]],
            status=p.get("status", "OPEN"),
        )
    return out


def process_invoice(path, vendors_by_gstin, vendors_by_name, pos_by_number, seen_keys):
    inv = extract_invoice(path)
    validate(inv, vendors_by_gstin, vendors_by_name)
    blocking = has_blocking_issue(inv.validation_issues)
    match = match_invoice(inv, pos_by_number, seen_keys)
    decision = decide_approval(inv, match, blocking)
    # register the invoice so later duplicates are caught
    seen_keys.add(duplicate_key(inv))
    return {"invoice": inv, "match": match, "decision": decision, "blocking": blocking}


def run(data_dir: str, invoice_dir: str) -> dict:
    vendors_by_gstin, vendors_by_name, vendors_by_id = load_vendors(
        os.path.join(data_dir, "vendors.json"))
    pos_by_number = load_pos(os.path.join(data_dir, "purchase_orders.json"))
    erp = MockERP(vendors_by_id)

    files = sorted(glob.glob(os.path.join(invoice_dir, "*.pdf")) +
                   glob.glob(os.path.join(invoice_dir, "*.txt")))
    seen_keys: set = set()
    results = []
    for path in files:
        results.append(process_invoice(
            path, vendors_by_gstin, vendors_by_name, pos_by_number, seen_keys))

    # post + pay only those that cleared the pipeline
    approved = [r["invoice"] for r in results if r["decision"].status == "AUTO_APPROVED"]
    postings = [erp.post_invoice(inv) for inv in approved]
    payment_batch = erp.build_payment_batch(approved)

    return {
        "results": results,
        "postings": postings,
        "payment_batch": payment_batch,
        "summary": _summarise(results, postings, payment_batch),
    }


def _summarise(results, postings, batch) -> dict:
    by_status = {}
    for r in results:
        by_status[r["decision"].status] = by_status.get(r["decision"].status, 0) + 1
    match_by_status = {}
    for r in results:
        match_by_status[r["match"].status] = match_by_status.get(r["match"].status, 0) + 1
    touchless = by_status.get("AUTO_APPROVED", 0)
    return {
        "invoices_processed": len(results),
        "touchless": touchless,
        "touchless_rate_pct": round(100 * touchless / len(results), 1) if results else 0.0,
        "by_decision": by_status,
        "by_match": match_by_status,
        "posted": len(postings),
        "payment_lines": len(batch),
        "payment_value": round(sum(p.amount for p in batch), 2),
    }


def format_report(run_result: dict) -> str:
    L = []
    L.append("=" * 74)
    L.append("  ACCOUNTS PAYABLE AGENT — RUN REPORT")
    L.append("=" * 74)
    for r in run_result["results"]:
        inv, match, dec = r["invoice"], r["match"], r["decision"]
        L.append("")
        L.append(f"  {os.path.basename(inv.source_file)}")
        L.append(f"    Vendor     : {inv.vendor_name}  [{inv.vendor_id or 'UNKNOWN'}]")
        L.append(f"    Invoice No : {inv.invoice_no}   Date: {inv.invoice_date}   "
                 f"PO: {inv.po_number or '—'}")
        L.append(f"    Total      : {inv.currency} {inv.total:,.2f}" if inv.total is not None
                 else "    Total      : —")
        L.append(f"    Extraction : confidence {inv.field_confidence.get('_overall')} "
                 f"({inv.field_confidence.get('line_items_found')} line items)")
        L.append(f"    Match      : {match.status}")
        for d in match.discrepancies:
            L.append(f"        - [{d.severity}] {d.code}: {d.detail}")
        for v in inv.validation_issues:
            L.append(f"        - [{v['severity']}] {v['code']}: {v['detail']}")
        line = f"    Decision   : {dec.status}"
        if dec.approvers:
            line += f"  (approvers: {', '.join(dec.approvers)})"
        L.append(line)
        L.append(f"    Reason     : {dec.reason}")

    s = run_result["summary"]
    L.append("")
    L.append("-" * 74)
    L.append("  SUMMARY")
    L.append("-" * 74)
    L.append(f"    Invoices processed : {s['invoices_processed']}")
    L.append(f"    Touchless          : {s['touchless']}  ({s['touchless_rate_pct']}%)")
    L.append(f"    By decision        : {s['by_decision']}")
    L.append(f"    By match           : {s['by_match']}")
    L.append(f"    Posted to ERP      : {s['posted']}")
    L.append(f"    Payment batch      : {s['payment_lines']} lines, "
             f"INR {s['payment_value']:,.2f}")
    L.append("")
    if run_result["payment_batch"]:
        L.append("  PAYMENT BATCH (prepared, awaiting release)")
        L.append(f"    {'Vendor':<28}{'Invoice':<12}{'Terms':<8}{'Due':<12}{'Amount':>12}")
        for p in run_result["payment_batch"]:
            L.append(f"    {p.vendor_name[:27]:<28}{p.invoice_no:<12}"
                     f"{p.payment_terms:<8}{p.due_date:<12}{p.amount:>12,.2f}")
    L.append("=" * 74)
    return "\n".join(L)
