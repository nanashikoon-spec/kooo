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

# Cache: pdf_path -> set of renderable unicode codepoints in F1 (regular) font.
_RENDERABLE_CACHE: dict[Path, set[int] | None] = {}
# Cache: pdf_path -> set of renderable unicode codepoints in F2 (medium/bold) font.
_RENDERABLE_F2_CACHE: dict[Path, set[int] | None] = {}
# Cache: pdf_path -> receipt type string ("sbp", "sbp_short", "sbp_long", ...)
_TYPE_CACHE: dict[Path, str] = {}

# '0'-'9' — digits that must be present in F2 for amount_bold to render correctly
_DIGIT_CODEPOINTS = frozenset(range(0x30, 0x3A))

# Donor types that contain bank/account/ident rows (full SBP layout)
_FULL_SBP_TYPES = frozenset({"sbp", "sbp_long"})


def _renderable_chars_for(donor_path: Path) -> set[int] | None:
    """Get renderable F1 codepoints for a donor (cached)."""
    cached = _RENDERABLE_CACHE.get(donor_path)
    if cached is not None or donor_path in _RENDERABLE_CACHE:
        return cached
    try:
        from tbank_check_service import get_renderable_chars
        chars = get_renderable_chars(donor_path.read_bytes(), "regular")
    except Exception:
        chars = None
    _RENDERABLE_CACHE[donor_path] = chars
    return chars


def _renderable_f2_chars_for(donor_path: Path) -> set[int] | None:
    """Get renderable F2 (medium/bold) codepoints for a donor (cached)."""
    if donor_path in _RENDERABLE_F2_CACHE:
        return _RENDERABLE_F2_CACHE[donor_path]
    try:
        from tbank_check_service import get_renderable_chars
        chars = get_renderable_chars(donor_path.read_bytes(), "medium")
    except Exception:
        chars = None
    _RENDERABLE_F2_CACHE[donor_path] = chars
    return chars


def _all_donors() -> list[Path]:
    """All available T-Bank donor PDFs (fresh ones first, enriched last)."""
    fresh = sorted(TBANK_DIR.glob("tbank_sbp_*.pdf"))
    enriched = sorted(TBANK_DIR.glob("*_enriched.pdf"))
    legacy = [p for p in sorted(TBANK_DIR.glob("*.pdf"))
              if not p.name.startswith("tbank_sbp_") and "_enriched" not in p.stem]
    return fresh + enriched + legacy


def _find_donor(
    prefer_enriched: bool = False,
    text_fields: Optional[dict[str, str]] = None,
    require_full_sbp: bool = True,
) -> Path:
    """Pick an SBP donor from TBANK/.

    If text_fields is provided, only donors whose F1 font can render ALL
    characters are eligible. Among eligible donors, fresh (tbank_sbp_*) are
    preferred over enriched legacy ones — fresh donors have current metadata
    and pass strict external verification more reliably.

    If require_full_sbp=True (default), only donors with full SBP layout
    (bank/account/ident rows) are considered — i.e. type "sbp" or "sbp_long".
    Donors with SBP_SHORT layout (type "sbp_short") are excluded because they
    lack bank/account rows that the user's form provides.
    """
    from tbank_check_service import detect_receipt_type as _detect_type

    def _donor_type(p: Path) -> str:
        if p not in _TYPE_CACHE:
            try:
                _TYPE_CACHE[p] = _detect_type(p)
            except Exception:
                _TYPE_CACHE[p] = "sbp"
        return _TYPE_CACHE[p]

    all_donors = _all_donors()
    if not all_donors:
        raise FileNotFoundError(
            "Не найдены донорские PDF для Т-Банка. "
            "Положите файлы в папку TBANK/ проекта."
        )

    # Filter out SBP_SHORT donors when full layout is required
    if require_full_sbp:
        full_donors = [d for d in all_donors if _donor_type(d) in _FULL_SBP_TYPES]
        if full_donors:
            all_donors = full_donors

    needed: set[int] = set()
    if text_fields:
        for val in text_fields.values():
            for ch in str(val):
                if ch != " ":
                    needed.add(ord(ch))

    if not needed:
        fresh = [p for p in all_donors if p.name.startswith("tbank_sbp_")]
        if fresh and not prefer_enriched:
            return random.choice(fresh)
        if prefer_enriched:
            enr = [p for p in all_donors if "_enriched" in p.stem]
            if enr:
                return random.choice(enr)
        return random.choice(all_donors)

    eligible_fresh: list[Path] = []
    eligible_enriched: list[Path] = []
    eligible_legacy: list[Path] = []
    best_partial: tuple[int, Path] | None = None

    # Build set of all donor paths for quick lookup
    all_donors_set = set(all_donors)

    for d in all_donors:
        chars = _renderable_chars_for(d)
        if chars is None:
            covered = needed
        else:
            covered = needed & chars
            if covered != needed:
                missing_count = len(needed - chars)
                if best_partial is None or missing_count < best_partial[0]:
                    best_partial = (missing_count, d)
                continue

        # F1 coverage OK — now also check F2 has all digit glyphs (needed for amount_bold)
        f2_chars = _renderable_f2_chars_for(d)
        if f2_chars is not None and not _DIGIT_CODEPOINTS.issubset(f2_chars):
            # F2 missing digits — try to upgrade to enriched version
            if "_enriched" not in d.stem:
                enriched_candidate = d.with_stem(d.stem + "_enriched")
                if enriched_candidate in all_donors_set:
                    d = enriched_candidate
                else:
                    # No enriched version available — skip (would produce invisible digits)
                    continue

        if "_enriched" in d.stem:
            eligible_enriched.append(d)
        elif d.name.startswith("tbank_sbp_"):
            eligible_fresh.append(d)
        else:
            eligible_legacy.append(d)

    if eligible_fresh:
        return random.choice(eligible_fresh)
    if eligible_enriched:
        return random.choice(eligible_enriched)
    if eligible_legacy:
        return random.choice(eligible_legacy)
    if best_partial is not None:
        return best_partial[1]
    return random.choice(all_donors)


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
    else:
        # Normalize single-digit hours: "1:13:23" → "01:13:23"
        _tp = operation_time.split(":")
        if len(_tp) >= 2:
            operation_time = f"{int(_tp[0]):02d}:{_tp[1]}" + (f":{_tp[2]}" if len(_tp) >= 3 else ":00")
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
        _update_keywords,
    )

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

    if donor_path is None:
        donor_path = _find_donor(text_fields=changes)

    receipt_type = detect_receipt_type(donor_path)

    pdf_bytes = patch_all_fields(donor_path, changes, receipt_type)

    # Update metadata.
    # NOTE: _update_keywords is intentionally NOT called here.
    # The donor's /Keywords field contains a server-side md5 that cannot be
    # reproduced. Changing it (even with an updated timestamp) produces a
    # wrong hash that causes "Целостность PDF: Нет" in the verifier.
    # Keeping the original Keywords from the donor passes the integrity check.
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
