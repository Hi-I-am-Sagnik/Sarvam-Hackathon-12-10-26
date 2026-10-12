"""Configuration for the AP Agent prototype.

All business rules live here so finance can tune them without touching code.
"""

CONFIG = {
    # --- Matching tolerances -------------------------------------------------
    # A line is "within tolerance" if the variance is <= these values.
    "price_tolerance_pct": 3.0,      # allowed unit-price variance vs. PO
    "qty_tolerance_pct": 0.0,        # allowed quantity variance vs. PO
    "amount_tolerance_abs": 1.00,    # absolute rounding tolerance (currency units)
    "arithmetic_tolerance_abs": 0.01,

    # --- Approval matrix -----------------------------------------------------
    # (upper_bound_inclusive, [approver roles]); first band that fits wins.
    "approval_thresholds": [
        (100_000,     []),                                  # touchless auto-approval
        (1_000_000,   ["Manager"]),
        (5_000_000,   ["Manager", "Finance Head"]),
        (float("inf"), ["Manager", "Finance Head", "CFO"]),
    ],

    # --- Other ---------------------------------------------------------------
    "default_currency": "INR",
    "payment_terms_default": "NET30",
    "payment_terms_by_vendor": {},       # optional per-vendor override
    "valid_currencies": ["INR", "USD", "EUR", "GBP", "AED"],
}

# Indian GSTIN: 2-digit state + PAN + entity + Z + checksum (15 chars).
GSTIN_REGEX = r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$"
