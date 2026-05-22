#!/usr/bin/env python3
"""T-Bank SBP receipt generator.

Takes user-supplied field values and patches a donor T-Bank PDF from the
TBANK/ folder, replacing amount, datetime, sender, recipient, phone, bank,
account, and SBP operation ID.

All coordinates are derived from the actual donor PDFs in TBANK/.
"""
from __future__ import annotations

import random
import re
import string
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent
TBANK_DIR = BASE_DIR / "TBANK"


def _find_donor(prefer_enriched: bool = True) -> Path:
    """Pick an SBP donor from TBANK/ folder, preferring enriched variants."""
    if prefer_enriched:
        enriched = sorted(TBANK_DIR.glob("*_enriched.pdf"))
        if enriched:
            return random.choice(enriched)
    candidates = [p for p in sorted(TBANK_DIR.glob("*.pdf")) if "_enriched" not in p.stem]
    if not candidates:
        raise FileNotFoundError(
            "Не найдены донорские PDF для Т-Банка. "
            "Положите файлы в папку TBANK/ проекта."
        )
    return random.choice(candidates)


def _format_amount(amount: int) -> str:
    """Format integer amount: 15000 → '15 000 ', 20 → '20 '."""
    s = f"{amount:,}".replace(",", " ")
    return s + " "


def _auto_datetime(
    operation_date: str, operation_time: str
) -> tuple[str, str]:
    """Return (date_str, time_str), substituting 'auto' with current values."""
    now = datetime.now()
    if operation_date in ("", "auto", "авто"):
        operation_date = now.strftime("%d.%m.%Y")
    if operation_time in ("", "auto", "авто"):
        operation_time = now.strftime("%H:%M:%S")
    return operation_date, operation_time


def _gen_receipt_number() -> str:
    """Generate a receipt number like '1-119-177-831-062'."""
    parts = [str(random.randint(1, 9))] + [
        f"{random.randint(0, 999):03d}" for _ in range(4)
    ]
    return "-".join(parts)


def _gen_sbp_operation_id() -> str:
    """Generate a T-Bank style SBP operation ID like 'A61061126522550G0B100600117'."""
    chars = string.ascii_uppercase + string.digits
    return "A" + "".join(random.choices(chars, k=26))


def get_missing_chars(donor_path: Path, text_fields: dict[str, str]) -> list[str]:
    """Return list of characters in text_fields that lack glyph outlines in the donor's F1 font.

    Used to warn the user which characters will render as invisible.
    """
    from tbank_check_service import get_renderable_chars
    pdf_bytes = donor_path.read_bytes()
    f1_renderable = get_renderable_chars(pdf_bytes, "regular")
    if f1_renderable is None:
        return []
    missing: set[str] = set()
    for val in text_fields.values():
        for ch in val:
            if ch != " " and ord(ch) not in f1_renderable:
                missing.add(ch)
    return sorted(missing)


def generate_tbank_receipt(
    amount: int,
    sender_name: str,
    sender_account: str,
    recipient_name: str,
    recipient_phone: str,
    recipient_bank: str,
    operation_date: str = "auto",
    operation_time: str = "auto",
    spb_number: str = "auto",
    receipt_number: str = "auto",
    donor_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> tuple[bytes, str]:
    """Generate a T-Bank SBP receipt PDF by patching a donor.

    Returns (pdf_bytes, filename).
    """
    from tbank_check_service import (
        patch_all_fields,
        detect_receipt_type,
        _update_doc_id,
        _update_dates,
    )

    if donor_path is None:
        donor_path = _find_donor(prefer_enriched=True)

    operation_date, operation_time = _auto_datetime(operation_date, operation_time)

    if spb_number in ("", "auto", "авто"):
        spb_number = _gen_sbp_operation_id()

    if receipt_number in ("", "auto", "авто"):
        receipt_number = _gen_receipt_number()

    # Format datetime string as shown in T-Bank receipts (double-space between date and time)
    datetime_str = f"{operation_date}  {operation_time}"

    # Amount string (bold uses same formatted value)
    amount_str = _format_amount(amount)

    # Build changes dict mapping field keys to new values
    changes: dict[str, str] = {
        "datetime": datetime_str,
        "amount_bold": amount_str,
        "amount_small": amount_str,
        "sender": sender_name,
        "phone": recipient_phone,
        "receiver": recipient_name,
        "bank": recipient_bank,
        "account": sender_account,
    }

    receipt_type = detect_receipt_type(donor_path)

    pdf_bytes = patch_all_fields(donor_path, changes, receipt_type)

    # Update metadata
    try:
        dt = datetime.strptime(f"{operation_date} {operation_time}", "%d.%m.%Y %H:%M:%S")
    except ValueError:
        dt = datetime.now()
    pdf_bytes = _update_dates(pdf_bytes, dt)
    pdf_bytes = _update_doc_id(pdf_bytes)

    # Build filename
    date_tag = operation_date.replace(".", "")
    filename = f"Tbank_SBP_{date_tag}_{amount}.pdf"

    if output_path:
        output_path = Path(output_path)
        output_path.write_bytes(pdf_bytes)

    return pdf_bytes, filename
