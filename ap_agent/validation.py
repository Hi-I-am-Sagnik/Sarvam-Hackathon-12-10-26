"""Capability 1b: validate extracted invoice data.

Checks structure, arithmetic, formats, and the vendor master. Returns a list
of issue dicts; a non-empty BLOCK-level list means the invoice cannot proceed
without human review.
"""
from __future__ import annotations

import re

from .config import CONFIG, GSTIN_REGEX
from .models import Invoice

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def validate(inv: Invoice, vendors_by_gstin: dict, vendors_by_name: dict) -> list[dict]:
    issues: list[dict] = []

    def add(code, detail, severity):
        issues.append({"code": code, "detail": detail, "severity": severity})

    # --- required fields present ---
    for f in ["vendor_name", "vendor_gstin", "invoice_no", "invoice_date",
              "subtotal", "tax", "total"]:
        if getattr(inv, f) in (None, ""):
            add("MISSING_FIELD", f"Required field '{f}' not found", "BLOCK")

    # --- format checks ---
    if inv.invoice_date and not DATE_RE.match(inv.invoice_date):
        add("BAD_DATE_FORMAT", f"Invoice date '{inv.invoice_date}' is not dd/mm/yyyy", "BLOCK")

    if inv.currency not in CONFIG["valid_currencies"]:
        add("BAD_CURRENCY", f"Currency '{inv.currency}' is not recognised", "BLOCK")

    if inv.vendor_gstin and not re.match(GSTIN_REGEX, inv.vendor_gstin):
        add("BAD_GSTIN", f"GSTIN '{inv.vendor_gstin}' fails format check", "WARN")

    # --- line-item arithmetic ---
    if inv.lines:
        line_sum = round(sum(li.amount for li in inv.lines), 2)
        if inv.subtotal is not None and abs(line_sum - inv.subtotal) > CONFIG["arithmetic_tolerance_abs"]:
            add("LINE_SUM_MISMATCH",
                f"Line items sum to {line_sum:.2f} but subtotal is {inv.subtotal:.2f}", "BLOCK")

    if inv.subtotal is not None and inv.tax is not None and inv.total is not None:
        expected = round(inv.subtotal + inv.tax, 2)
        if abs(expected - inv.total) > CONFIG["arithmetic_tolerance_abs"]:
            add("TOTAL_MISMATCH",
                f"Subtotal+tax = {expected:.2f} but total is {inv.total:.2f}", "BLOCK")

    # --- vendor master check ---
    vendor = None
    if inv.vendor_gstin and inv.vendor_gstin in vendors_by_gstin:
        vendor = vendors_by_gstin[inv.vendor_gstin]
    elif inv.vendor_name and inv.vendor_name.strip().lower() in vendors_by_name:
        vendor = vendors_by_name[inv.vendor_name.strip().lower()]

    if vendor is None:
        add("VENDOR_NOT_FOUND",
            f"Vendor '{inv.vendor_name}' / GSTIN '{inv.vendor_gstin}' not in master", "BLOCK")
    else:
        inv.vendor_id = vendor["vendor_id"]
        if not vendor.get("approved", True):
            add("VENDOR_NOT_APPROVED", f"Vendor {vendor['vendor_id']} is not approved for payment", "BLOCK")

    inv.validation_issues = issues
    return issues


def has_blocking_issue(issues: list[dict]) -> bool:
    return any(i["severity"] == "BLOCK" for i in issues)
