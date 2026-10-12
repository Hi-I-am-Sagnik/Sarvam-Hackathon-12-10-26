"""Capability 3b: post approved invoices and prepare the payment batch.

A mock ERP connector. In production this would call the ERP's API (Tally,
Zoho Books, SAP, NetSuite, …); here it keeps an in-memory ledger so the
workflow is demonstrable end to end.
"""
from __future__ import annotations

from datetime import date, timedelta

from .config import CONFIG
from .models import Invoice, PaymentLine, Posting


def _add_days(iso_or_ddmmyyyy: str, days: int) -> str:
    try:
        d, m, y = (int(x) for x in iso_or_ddmmyyyy.split("/"))
        base = date(y, m, d)
    except Exception:
        base = date.today()
    return (base + timedelta(days=days)).strftime("%d/%m/%Y")


class MockERP:
    """Minimal ERP stand-in: posts invoices and builds payment batches."""

    def __init__(self, vendors_by_id: dict):
        self.vendors_by_id = vendors_by_id
        self.postings: list[Posting] = []
        self._seq = 0

    def post_invoice(self, inv: Invoice) -> Posting:
        self._seq += 1
        posting = Posting(
            posting_id=f"POST-{self._seq:05d}",
            invoice_no=inv.invoice_no,
            vendor_id=inv.vendor_id,
            amount=inv.total or 0.0,
        )
        self.postings.append(posting)
        return posting

    def build_payment_batch(self, approved: list[Invoice]) -> list[PaymentLine]:
        batch: list[PaymentLine] = []
        for inv in approved:
            vendor = self.vendors_by_id.get(inv.vendor_id, {})
            terms = (CONFIG["payment_terms_by_vendor"].get(inv.vendor_id)
                     or vendor.get("payment_terms")
                     or CONFIG["payment_terms_default"])
            days = int(terms.replace("NET", "")) if terms.upper().startswith("NET") else 30
            batch.append(PaymentLine(
                vendor_id=inv.vendor_id,
                vendor_name=vendor.get("name", inv.vendor_name or ""),
                invoice_no=inv.invoice_no,
                amount=inv.total or 0.0,
                due_date=_add_days(inv.invoice_date or "", days),
                payment_terms=terms,
            ))
        return batch
