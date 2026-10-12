"""Data model for the AP Agent prototype."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LineItem:
    sku: str
    description: str
    qty: float
    unit_price: float
    amount: float


@dataclass
class Invoice:
    source_file: str
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    currency: str = "INR"
    lines: list[LineItem] = field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    raw_text: str = ""

    # populated downstream
    vendor_id: Optional[str] = None
    field_confidence: dict = field(default_factory=dict)
    validation_issues: list = field(default_factory=list)
    status: str = "NEW"


@dataclass
class POLine:
    sku: str
    description: str
    qty: float
    unit_price: float


@dataclass
class PurchaseOrder:
    po_number: str
    vendor_id: str
    vendor_name: str
    currency: str = "INR"
    lines: list[POLine] = field(default_factory=list)
    status: str = "OPEN"


@dataclass
class Discrepancy:
    code: str
    detail: str
    severity: str  # INFO | WARN | BLOCK


@dataclass
class MatchResult:
    status: str = "UNPROCESSED"   # MATCHED | MATCHED_TOLERANCE | EXCEPTION | UNMATCHED | DUPLICATE
    matched: bool = False
    po_number: Optional[str] = None
    discrepancies: list[Discrepancy] = field(default_factory=list)


@dataclass
class ApprovalDecision:
    status: str = "PENDING"       # AUTO_APPROVED | PENDING_APPROVAL | ROUTED_TO_EXCEPTION
    approvers: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class Posting:
    posting_id: str
    invoice_no: str
    vendor_id: str
    amount: float
    gl_account: str = "2000-Accounts Payable"
    status: str = "POSTED"


@dataclass
class PaymentLine:
    vendor_id: str
    vendor_name: str
    invoice_no: str
    amount: float
    due_date: str
    payment_terms: str
