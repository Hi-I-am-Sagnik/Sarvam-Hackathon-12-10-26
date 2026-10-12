"""Capability 2: match an invoice against purchase orders and flag discrepancies.

Implements duplicate detection, two-/three-way style line matching against a
PO, configurable price and quantity tolerances, and severity classification.
"""
from __future__ import annotations

from .config import CONFIG
from .models import Discrepancy, Invoice, MatchResult, PurchaseOrder


def duplicate_key(inv: Invoice) -> tuple:
    ident = (inv.vendor_gstin or inv.vendor_name or "").strip().lower()
    return (ident, (inv.invoice_no or "").strip().lower(), round(inv.total or 0, 2))


def match_invoice(
    inv: Invoice,
    pos_by_number: dict[str, PurchaseOrder],
    seen_keys: set,
) -> MatchResult:
    result = MatchResult()

    # --- duplicate screen (before anything else) ---
    key = duplicate_key(inv)
    if key in seen_keys:
        result.status = "DUPLICATE"
        result.discrepancies.append(Discrepancy(
            "DUPLICATE_INVOICE",
            f"Invoice {inv.invoice_no} from {inv.vendor_name} "
            f"(total {inv.total}) already processed", "BLOCK"))
        return result

    # --- find the PO ---
    if not inv.po_number:
        result.status = "UNMATCHED"
        result.discrepancies.append(Discrepancy(
            "NO_PO_REFERENCE", "Invoice carries no PO number", "BLOCK"))
        return result

    po = pos_by_number.get(inv.po_number)
    if po is None:
        result.status = "UNMATCHED"
        result.discrepancies.append(Discrepancy(
            "PO_NOT_FOUND", f"PO {inv.po_number} does not exist", "BLOCK"))
        return result

    result.po_number = po.po_number

    # --- vendor must agree ---
    if inv.vendor_id and po.vendor_id and inv.vendor_id != po.vendor_id:
        result.discrepancies.append(Discrepancy(
            "VENDOR_MISMATCH",
            f"Invoice vendor {inv.vendor_id} != PO vendor {po.vendor_id}", "BLOCK"))

    po_lines = {l.sku: l for l in po.lines}
    inv_lines = {l.sku: l for l in inv.lines}
    price_tol = CONFIG["price_tolerance_pct"]
    qty_tol = CONFIG["qty_tolerance_pct"]
    within_tolerance = True

    for sku, il in inv_lines.items():
        pl = po_lines.get(sku)
        if pl is None:
            result.discrepancies.append(Discrepancy(
                "LINE_NOT_ON_PO", f"{sku} ({il.description}) is not on PO {po.po_number}", "BLOCK"))
            within_tolerance = False
            continue

        if pl.unit_price:
            pvar = (il.unit_price - pl.unit_price) / pl.unit_price * 100
            if abs(pvar) > price_tol:
                sev = "BLOCK" if abs(pvar) > 2 * price_tol else "WARN"
                result.discrepancies.append(Discrepancy(
                    "PRICE_VARIANCE",
                    f"{sku}: invoice {il.unit_price:.2f} vs PO {pl.unit_price:.2f} "
                    f"({pvar:+.1f}%)", sev))
                within_tolerance = False

        if pl.qty:
            qvar = (il.qty - pl.qty) / pl.qty * 100
            if abs(qvar) > qty_tol:
                result.discrepancies.append(Discrepancy(
                    "QTY_VARIANCE",
                    f"{sku}: invoiced {il.qty:g} vs PO {pl.qty:g} ({qvar:+.1f}%)", "BLOCK"))
                within_tolerance = False

    for sku in po_lines:
        if sku not in inv_lines:
            result.discrepancies.append(Discrepancy(
                "LINE_MISSING_FROM_INVOICE",
                f"PO line {sku} not billed on this invoice", "WARN"))

    blocking = any(d.severity == "BLOCK" for d in result.discrepancies)
    if blocking:
        result.status = "EXCEPTION"
    elif result.discrepancies:
        result.status = "MATCHED_TOLERANCE"
        result.matched = True
    else:
        result.status = "MATCHED"
        result.matched = True
    return result
