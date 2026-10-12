"""Capability 1a: extract structured invoice data from a document.

Reads a PDF (via pdfplumber) or a plain-text file and returns an `Invoice`
with header fields and line items parsed out, plus a per-field confidence map.

In production this layer would call a document-AI service; the regex parser
here keeps the prototype dependency-free and deterministic for demos.
"""
from __future__ import annotations

import re
from typing import Optional

from .models import Invoice, LineItem

# --- field patterns ----------------------------------------------------------
P_VENDOR = re.compile(r"^\s*Vendor\s*:\s*(.+?)\s*$", re.M | re.I)
P_GSTIN = re.compile(r"^\s*GSTIN\s*:\s*([A-Z0-9]+)\s*$", re.M | re.I)
P_INVNO = re.compile(r"^\s*Invoice\s*No\.?\s*:\s*(\S+)\s*$", re.M | re.I)
P_DATE = re.compile(r"^\s*Invoice\s*Date\s*:\s*(\S+)\s*$", re.M | re.I)
P_PO = re.compile(r"^\s*PO\s*Number\s*:\s*(\S+)\s*$", re.M | re.I)
P_CURR = re.compile(r"^\s*Currency\s*:\s*([A-Za-z]{3})\s*$", re.M | re.I)
P_SUBTOTAL = re.compile(r"^\s*Subtotal\s*:\s*([\d,]+\.?\d*)\s*$", re.M | re.I)
P_TAX = re.compile(r"^\s*Tax[^:]*:\s*([\d,]+\.?\d*)\s*$", re.M | re.I)
P_TOTAL = re.compile(r"^\s*Total\s*:\s*([\d,]+\.?\d*)\s*$", re.M | re.I)
# SKU  description  qty  unit_price  amount
P_LINE = re.compile(
    r"^\s*(\S+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$",
    re.M,
)

REQUIRED_FIELDS = [
    "vendor_name", "vendor_gstin", "invoice_no",
    "invoice_date", "po_number", "subtotal", "tax", "total",
]


def _num(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    return float(s.replace(",", ""))


def read_text(path: str) -> str:
    """Return the plain text of a .pdf or .txt file."""
    if path.lower().endswith(".pdf"):
        import pdfplumber
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def parse_invoice(text: str, source_file: str) -> Invoice:
    inv = Invoice(source_file=source_file, raw_text=text)

    def grab(pattern):
        m = pattern.search(text)
        return m.group(1).strip() if m else None

    inv.vendor_name = grab(P_VENDOR)
    inv.vendor_gstin = grab(P_GSTIN)
    inv.invoice_no = grab(P_INVNO)
    inv.invoice_date = grab(P_DATE)
    inv.po_number = grab(P_PO)
    inv.currency = (grab(P_CURR) or "INR").upper()
    inv.subtotal = _num(grab(P_SUBTOTAL))
    inv.tax = _num(grab(P_TAX))
    inv.total = _num(grab(P_TOTAL))

    for m in P_LINE.finditer(text):
        inv.lines.append(LineItem(
            sku=m.group(1),
            description=m.group(2).strip(),
            qty=float(m.group(3)),
            unit_price=_num(m.group(4)),
            amount=_num(m.group(5)),
        ))

    # crude confidence = share of required header fields present
    present = sum(1 for f in REQUIRED_FIELDS if getattr(inv, f) is not None)
    conf = round(present / len(REQUIRED_FIELDS), 2)
    inv.field_confidence = {f: (1.0 if getattr(inv, f) is not None else 0.0)
                            for f in REQUIRED_FIELDS}
    inv.field_confidence["_overall"] = conf
    inv.field_confidence["line_items_found"] = len(inv.lines)
    return inv


def extract_invoice(path: str) -> Invoice:
    return parse_invoice(read_text(path), path)
