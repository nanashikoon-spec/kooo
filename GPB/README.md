# GPB Donor Templates

Place genuine Gazprombank SBP receipt PDFs here.

Naming: any `.pdf` file works.

## Required source files
Copy these files from your device:
- `receipt_08.04.2026 (2).pdf`
- `receipt_08.04.2026 (3).pdf`
- `receipt_08.04.2026 (4).pdf`

## What gen_gpb_receipt.py uses from donors
- Font (CMap) coverage for all Cyrillic / digit characters
- SBP ID suffix (last 16 chars) — bank-specific, era-specific
- PDF structure (streams, xref)

## GPB SBP ID suffix (April 2026)
The last 10 chars of all April 2026 GPB SBP IDs are `0011680301`.
Full suffix example: `0000050011680301`
