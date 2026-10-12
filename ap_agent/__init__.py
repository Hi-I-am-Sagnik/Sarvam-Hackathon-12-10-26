"""Accounts Payable Agent — prototype package.

Modules:
    extraction  - pull structured data out of invoice documents
    validation  - check data quality, formats and the vendor master
    matching    - match invoices to POs and flag discrepancies
    approval    - decide the approval path from the configured matrix
    erp         - mock ERP: post invoices and prepare payment batches
    pipeline    - orchestrate the end-to-end flow
"""
__version__ = "0.1.0"
