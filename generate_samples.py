"""Generate the sample invoice PDFs used by the demo.

Each invoice is rendered as a simple text PDF so the extraction layer can read
it back. The set deliberately covers the interesting cases: a clean match, a
within-tolerance variance, an over-tolerance price variance, a quantity
mismatch, a missing PO, a duplicate, an unknown vendor, and a high-value
invoice that needs multi-level approval.
"""
from __future__ import annotations

import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "invoices")


def render(path: str, inv: dict) -> None:
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont("Helvetica-Bold", 15)
    c.drawString(60, y, "TAX INVOICE")
    y -= 30
    c.setFont("Helvetica", 10)

    for label, value in [
        ("Vendor", inv["vendor"]),
        ("GSTIN", inv["gstin"]),
        ("Invoice No", inv["invoice_no"]),
        ("Invoice Date", inv["date"]),
        ("PO Number", inv["po"]),
        ("Currency", inv["currency"]),
    ]:
        if value is None:
            continue  # field genuinely absent on the document
        c.drawString(60, y, f"{label}: {value}")
        y -= 16

    y -= 8
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y, "Line Items:")
    y -= 16
    c.setFont("Helvetica", 10)
    for sku, desc, qty, unit, amt in inv["lines"]:
        c.drawString(60, y, f"{sku} {desc} {qty:g} {unit:.2f} {amt:.2f}")
        y -= 15

    y -= 6
    c.drawString(60, y, f"Subtotal: {inv['subtotal']:.2f}"); y -= 15
    c.drawString(60, y, f"Tax (18%): {inv['tax']:.2f}"); y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y, f"Total: {inv['total']:.2f}")
    c.showPage()
    c.save()


def line(sku, desc, qty, unit):
    return (sku, desc, qty, unit, round(qty * unit, 2))


def build_invoices():
    invs = []

    # 1. Clean three-way match -> touchless
    invs.append(dict(
        file="inv_1001_acme_clean.pdf", vendor="Acme Industrial Supplies Pvt Ltd",
        gstin="29ABCDE1234F1Z5", invoice_no="INV-1001", date="05/09/2026",
        po="PO-5001", currency="INR",
        lines=[line("SKU-100", "Steel bolts M8", 100, 12.50),
               line("SKU-205", "Washers 8mm", 200, 3.00)],
        subtotal=1850.00, tax=333.00, total=2183.00))

    # 2. Price variance within tolerance (2.0% <= 3.0%) -> touchless
    invs.append(dict(
        file="inv_1002_acme_tol.pdf", vendor="Acme Industrial Supplies Pvt Ltd",
        gstin="29ABCDE1234F1Z5", invoice_no="INV-1002", date="06/09/2026",
        po="PO-5002", currency="INR",
        lines=[line("SKU-100", "Steel bolts M8", 100, 12.75)],
        subtotal=1275.00, tax=229.50, total=1504.50))

    # 3. Price variance OVER tolerance (10%) -> exception
    invs.append(dict(
        file="inv_1003_bharat_price.pdf", vendor="Bharat Components Ltd",
        gstin="27PQRSX6789L1Z2", invoice_no="INV-1003", date="07/09/2026",
        po="PO-5003", currency="INR",
        lines=[line("SKU-500", "Bearing assembly", 50, 440.00)],
        subtotal=22000.00, tax=3960.00, total=25960.00))

    # 4. Quantity mismatch (120 invoiced vs 100 on PO) -> exception
    invs.append(dict(
        file="inv_1004_acme_qty.pdf", vendor="Acme Industrial Supplies Pvt Ltd",
        gstin="29ABCDE1234F1Z5", invoice_no="INV-1004", date="08/09/2026",
        po="PO-5004", currency="INR",
        lines=[line("SKU-100", "Steel bolts M8", 120, 12.50)],
        subtotal=1500.00, tax=270.00, total=1770.00))

    # 5. No PO reference -> unmatched exception
    invs.append(dict(
        file="inv_1005_chennai_nopo.pdf", vendor="Chennai Tools & Hardware",
        gstin="33LMNOP4567Q1Z8", invoice_no="INV-1005", date="08/09/2026",
        po=None, currency="INR",
        lines=[line("SKU-700", "Drill bit set", 10, 250.00)],
        subtotal=2500.00, tax=450.00, total=2950.00))

    # 6. Duplicate of INV-1001 (different file, same vendor+number+total)
    invs.append(dict(
        file="inv_1006_duplicate.pdf", vendor="Acme Industrial Supplies Pvt Ltd",
        gstin="29ABCDE1234F1Z5", invoice_no="INV-1001", date="09/09/2026",
        po="PO-5001", currency="INR",
        lines=[line("SKU-100", "Steel bolts M8", 100, 12.50),
               line("SKU-205", "Washers 8mm", 200, 3.00)],
        subtotal=1850.00, tax=333.00, total=2183.00))

    # 7. Unknown vendor -> vendor master exception
    invs.append(dict(
        file="inv_1007_unknown_vendor.pdf", vendor="Rogue Traders",
        gstin="27ZZZZZ9999Z9Z9", invoice_no="INV-1007", date="09/09/2026",
        po="PO-5003", currency="INR",
        lines=[line("SKU-800", "Misc fittings", 5, 100.00)],
        subtotal=500.00, tax=90.00, total=590.00))

    # 8. High-value clean match -> multi-level approval (not touchless)
    invs.append(dict(
        file="inv_1008_vertex_capex.pdf", vendor="Vertex Machinery Systems",
        gstin="07UVWXY1234Z1Z1", invoice_no="INV-1008", date="10/09/2026",
        po="PO-5005", currency="INR",
        lines=[line("SKU-900", "CNC spindle unit", 2, 600000.00)],
        subtotal=1200000.00, tax=216000.00, total=1416000.00))

    return invs


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for inv in build_invoices():
        render(os.path.join(OUT_DIR, inv["file"]), inv)
    print(f"Generated {len(build_invoices())} invoice PDFs in {OUT_DIR}")


if __name__ == "__main__":
    main()
