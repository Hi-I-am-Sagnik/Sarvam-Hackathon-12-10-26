"""Capability 3a: decide the approval path for an invoice.

Any exception or blocking validation issue is routed to the human exception
queue. Otherwise the amount determines the approver chain from the configured
matrix; amounts under the first band are auto-approved (touchless).
"""
from __future__ import annotations

from .config import CONFIG
from .models import ApprovalDecision, Invoice, MatchResult


def decide_approval(inv: Invoice, match: MatchResult, blocking_validation: bool) -> ApprovalDecision:
    amount = inv.total or 0.0

    if blocking_validation:
        return ApprovalDecision(
            status="ROUTED_TO_EXCEPTION",
            reason="Blocking validation issue — human review required")

    if match.status in ("EXCEPTION", "UNMATCHED", "DUPLICATE"):
        codes = ", ".join(d.code for d in match.discrepancies) or match.status
        return ApprovalDecision(
            status="ROUTED_TO_EXCEPTION",
            reason=f"Matching issue ({codes}) — human review required")

    for upper, roles in CONFIG["approval_thresholds"]:
        if amount <= upper:
            if not roles:
                return ApprovalDecision(
                    status="AUTO_APPROVED",
                    reason=f"Amount {amount:,.2f} within touchless limit")
            return ApprovalDecision(
                status="PENDING_APPROVAL", approvers=list(roles),
                reason=f"Amount {amount:,.2f} requires {' + '.join(roles)}")

    return ApprovalDecision(status="ROUTED_TO_EXCEPTION", reason="No approval band matched")
