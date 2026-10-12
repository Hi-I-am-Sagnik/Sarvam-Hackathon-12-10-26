# Accounts Payable Agent — Prototype

A small, dependency-light Python prototype of an Accounts Payable agent that
covers the three requested capabilities:

1. **Extract and validate invoice data** from documents (PDF or text).
2. **Match invoices with purchase orders** and flag discrepancies.
3. **Automate approvals and payments** through ERP workflows.

It is built as a pipeline of independent modules so each stage can be tested,
replaced, or extended on its own.

## Layout

```
ap_agent_proto/
├── ap_agent/
│   ├── config.py       # all business rules: tolerances, approval matrix
│   ├── models.py       # dataclasses for invoices, POs, results
│   ├── extraction.py   # capability 1a — document → structured fields
│   ├── validation.py   # capability 1b — quality, format, vendor-master checks
│   ├── matching.py     # capability 2  — PO match + discrepancy flags
│   ├── approval.py     # capability 3a — approval routing from the matrix
│   ├── erp.py          # capability 3b — mock ERP posting + payment batch
│   └── pipeline.py     # orchestration + reporting
├── data/
│   ├── vendors.json          # vendor master
│   ├── purchase_orders.json  # open POs
│   └── invoices/             # generated sample invoice PDFs
├── generate_samples.py # creates the sample invoice PDFs
└── run_pipeline.py     # CLI entry point
```

## Run it

```bash
pip install -r requirements.txt
python generate_samples.py          # creates the sample invoices (once)
python run_pipeline.py              # runs the full pipeline
python run_pipeline.py --json out.json   # also emit machine-readable results
```

## What the demo shows

The bundled sample set deliberately exercises every path:

| Invoice | Scenario | Expected outcome |
|---|---|---|
| INV-1001 | Clean three-way match | Auto-approved, posted, paid |
| INV-1002 | Price variance within tolerance (2%) | Auto-approved (touchless) |
| INV-1003 | Price variance over tolerance (10%) | Routed to exception queue |
| INV-1004 | Quantity mismatch (120 vs 100) | Routed to exception queue |
| INV-1005 | No PO reference | Unmatched — exception |
| INV-1006 | Duplicate of INV-1001 | Blocked as duplicate |
| INV-1007 | Vendor not in master | Blocked — vendor review |
| INV-1008 | High value (₹14.16L), clean | Multi-level approval required |

## Tuning the rules

Everything a finance team would want to change lives in `ap_agent/config.py`:
price/quantity tolerances, the approval matrix (amount bands → approver
roles), the touchless limit, and payment terms. No code changes are needed to
adjust policy.

## Going to production

This prototype uses a regex extractor and a mock ERP so it runs anywhere. To
productionise:

- Swap `extraction.py` for a document-AI service (returns the same `Invoice`).
- Swap `erp.py` for a real connector (Tally, Zoho Books, SAP, NetSuite, …).
- Move `seen_keys` duplicate detection into a persistent store.
- Add authentication, an approval UI/email channel, and an audit log sink.

## Notes

- The pipeline is deterministic and needs no network access.
- All currency is INR in the sample data; the model supports multi-currency.
