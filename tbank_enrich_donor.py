#!/usr/bin/env python3
"""Enrich T-Bank donor PDFs by injecting missing digit glyphs into F2 (Medium/bold) font.

The F2 font subset in T-Bank receipts typically contains only 2-3 digit glyphs (e.g.
'0' and '2'), so amounts like '15 000' render as '000'. This script copies all missing
digit glyph outlines from F1 (Regular) into F2 (Medium) at the same GID positions
(both fonts use Identity CIDToGIDMap: CID = GID), then extends F2's /W width array.

Usage:
    python3 tbank_enrich_donor.py              # enrich all TBANK/*.pdf
    python3 tbank_enrich_donor.py TBANK/receipt_sbp_1.pdf  [output.pdf]
"""
from __future__ import annotations

import copy
import re
import sys
import zlib
from io import BytesIO
from pathlib import Path
from fontTools.ttLib import TTFont

BASE_DIR = Path(__file__).parent
TBANK_DIR = BASE_DIR / "TBANK"

# CIDs/GIDs for digits '0'-'9' (same for both F1 and F2 due to Identity mapping)
DIGIT_GIDS = list(range(305, 315))  # 305='0', 306='1', ..., 314='9'

# Desired F2 widths for digits 0-9 (from MEDIUM_WIDTHS table in tbank_cmap.py)
DIGIT_WIDTHS = {
    305: 570,  # '0'
    306: 509,  # '1'
    307: 540,  # '2'
    308: 540,  # '3'
    309: 540,  # '4'
    310: 540,  # '5'
    311: 540,  # '6'
    312: 540,  # '7'
    313: 540,  # '8'
    314: 540,  # '9'
}


def _find_font_stream(
    pdf_data: bytes, name_fragment: str
) -> tuple[int, int, int, bytes] | None:
    """Find a font's embedded stream by FontName fragment.

    Returns (stream_start, stream_len, len_num_start, decompressed_bytes).
    Matches FontDescriptor objects containing name_fragment in /FontName.
    """
    # First, find the FontDescriptor that has the name and get its FontFile2 obj ref
    for m in re.finditer(rb"(\d+)\s+0\s+obj", pdf_data):
        obj_start = m.start()
        chunk = pdf_data[obj_start : obj_start + 600]
        if b"/Type/FontDescriptor" not in chunk and b"FontDescriptor" not in chunk:
            continue
        if b"FontName" not in chunk:
            continue
        fn_m = re.search(rb"/FontName/([^\s/\]>]+)", chunk)
        if not fn_m:
            continue
        font_name = fn_m.group(1).decode("latin-1", errors="replace")
        if name_fragment not in font_name:
            continue
        ff2_m = re.search(rb"/FontFile2\s+(\d+)\s+0\s+R", chunk)
        if not ff2_m:
            continue
        stream_obj = int(ff2_m.group(1))

        # Now find that stream object
        pattern = rb"(" + str(stream_obj).encode() + rb")\s+0\s+obj\s*<<"
        for sm in re.finditer(pattern, pdf_data):
            if int(sm.group(1)) != stream_obj:
                continue
            schunk = pdf_data[sm.end() : sm.end() + 500]
            len_m = re.search(rb"/Length\s+(\d+)", schunk)
            end_m = re.search(rb">>\s*stream\r?\n", schunk)
            if not len_m or not end_m:
                continue
            stream_len = int(len_m.group(1))
            len_num_start = sm.end() + len_m.start(1)
            stream_start = sm.end() + end_m.end()
            raw = pdf_data[stream_start : stream_start + stream_len]
            try:
                dec = zlib.decompress(raw)
            except zlib.error:
                continue
            if len(dec) < 1000:
                continue
            return stream_start, stream_len, len_num_start, dec

    return None


def _glyph_is_empty(font: TTFont, gid: int) -> bool:
    """Return True if GID has no glyph outline (empty slot)."""
    order = font.getGlyphOrder()
    if gid >= len(order):
        return True
    glyf = font["glyf"]
    g = glyf[order[gid]]
    if g.numberOfContours == 0:
        return True
    if hasattr(g, "components") and g.components:
        return False
    return False


def _copy_glyph_at_gid(src_font: TTFont, dst_font: TTFont, gid: int) -> bool:
    """Copy glyph outline at GID from src into dst at the same GID slot."""
    src_order = src_font.getGlyphOrder()
    dst_order = dst_font.getGlyphOrder()
    if gid >= len(src_order) or gid >= len(dst_order):
        return False

    src_name = src_order[gid]
    dst_name = dst_order[gid]

    src_glyf = src_font["glyf"]
    dst_glyf = dst_font["glyf"]

    if src_name not in src_glyf:
        return False

    src_g = src_glyf[src_name]
    if src_g.numberOfContours == 0 and not (hasattr(src_g, "components") and src_g.components):
        return False

    dst_glyf[dst_name] = copy.deepcopy(src_g)

    # Copy hmtx metrics (advance width and lsb)
    src_hmtx = src_font["hmtx"]
    dst_hmtx = dst_font["hmtx"]
    if src_name in src_hmtx.metrics:
        dst_hmtx.metrics[dst_name] = src_hmtx.metrics[src_name]

    return True


def _delta_patch(
    pdf_data: bytes, stream_start: int, old_len: int, new_compressed: bytes
) -> bytes:
    """Replace a stream in pdf_data and delta-patch /Length, xref, startxref."""
    data = bytearray(pdf_data)
    delta = len(new_compressed) - old_len

    # 1. Replace stream bytes
    data[stream_start : stream_start + old_len] = new_compressed

    if delta == 0:
        return bytes(data)

    # 2. Patch /Length value for this stream (search backwards from stream_start)
    before = bytes(data[max(0, stream_start - 200) : stream_start])
    len_m = None
    for lm in re.finditer(rb"/Length\s+(\d+)", before):
        len_m = lm
    if len_m:
        abs_pos = (stream_start - len(before)) + len_m.start(1)
        old_len_str = len_m.group(1)
        new_len_str = str(stream_start - (stream_start - len(new_compressed) + len(new_compressed)) + len(new_compressed)).encode()
        # Simpler: just use len(new_compressed)
        new_len_str = str(len(new_compressed)).encode()
        data[abs_pos : abs_pos + len(old_len_str)] = new_len_str
        extra_delta = len(new_len_str) - len(old_len_str)
        if extra_delta != 0:
            # /Length digit count changed — update the delta
            # This is very rare (e.g. 999→1000), handle gracefully
            delta += extra_delta
            # stream_start also shifted
            stream_start += extra_delta

    # 3. Patch xref entries
    xref_m = re.search(
        rb"xref\r?\n(\d+)\s+(\d+)\r?\n((?:\d{10}\s+\d{5}\s+[nf]\s*\r?\n)+)",
        data,
    )
    if xref_m:
        entries = bytearray(xref_m.group(3))
        for em in re.finditer(rb"(\d{10})(\s+\d{5}\s+[nf]\s*\r?\n)", entries):
            offset = int(em.group(1))
            if offset > stream_start:
                entries[em.start(1) : em.start(1) + 10] = (
                    f"{offset + delta:010d}".encode()
                )
        data[xref_m.start(3) : xref_m.end(3)] = bytes(entries)

    # 4. Patch startxref
    sxref_m = re.search(rb"startxref\r?\n(\d+)\r?\n", data)
    if sxref_m and delta != 0:
        old_sxref = int(sxref_m.group(1))
        if stream_start < old_sxref:
            new_sxref = old_sxref + delta
            pos = sxref_m.start(1)
            old_s = sxref_m.group(1)
            data[pos : pos + len(old_s)] = str(new_sxref).encode()

    return bytes(data)


def _patch_font_stream(
    pdf_data: bytes,
    stream_start: int,
    old_stream_len: int,
    len_num_start: int,
    new_font_bytes: bytes,
) -> bytes:
    """Compress new_font_bytes, replace font stream in PDF, fix /Length + xref."""
    new_compressed = zlib.compress(new_font_bytes, 9)
    delta = len(new_compressed) - old_stream_len

    data = bytearray(pdf_data)

    # 1. Replace stream
    data[stream_start : stream_start + old_stream_len] = new_compressed

    # 2. Update /Length
    old_len_str = str(old_stream_len).encode()
    new_len_str = str(len(new_compressed)).encode()
    len_delta = len(new_len_str) - len(old_len_str)
    data[len_num_start : len_num_start + len(old_len_str)] = new_len_str

    if len_delta != 0:
        # The /Length digits changed size — all subsequent byte offsets shift by this too
        # (len_num_start is before stream_start, so it shifts stream_start)
        delta += len_delta
        stream_start += len_delta

    # 3. Patch xref
    xref_m = re.search(
        rb"xref\r?\n(\d+)\s+(\d+)\r?\n((?:\d{10}\s+\d{5}\s+[nf]\s*\r?\n)+)",
        data,
    )
    if xref_m:
        entries = bytearray(xref_m.group(3))
        for em in re.finditer(rb"(\d{10})(\s+\d{5}\s+[nf]\s*\r?\n)", entries):
            offset = int(em.group(1))
            if offset > stream_start:
                entries[em.start(1) : em.start(1) + 10] = (
                    f"{offset + delta:010d}".encode()
                )
        data[xref_m.start(3) : xref_m.end(3)] = bytes(entries)

    # 4. Patch startxref
    sxref_m = re.search(rb"startxref\r?\n(\d+)\r?\n", data)
    if sxref_m and delta != 0:
        old_sxref = int(sxref_m.group(1))
        if stream_start < old_sxref:
            new_sxref = old_sxref + delta
            pos = sxref_m.start(1)
            old_s = sxref_m.group(1)
            data[pos : pos + len(old_s)] = str(new_sxref).encode()

    return bytes(data)


def _update_medium_w_array(pdf_data: bytes) -> bytes:
    """Replace F2's /W array in the CIDFont dict to include all digit widths."""
    # Find the CIDFont object with TinkoffSans-Medium and a /W array
    for m in re.finditer(rb"(\d+)\s+0\s+obj", pdf_data):
        obj_start = m.start()
        # Read enough to cover the obj dict
        chunk = pdf_data[obj_start : obj_start + 600]
        if b"CIDFontType2" not in chunk:
            continue
        if b"Medium" not in chunk:
            continue
        w_m = re.search(rb"/W\s*\[(.*?)\]", chunk, re.DOTALL)
        if not w_m:
            continue

        # Build the new /W array content that covers all digits 305-314
        new_w_content = (
            "3[200]"
            "244[675]271[390]283[544]287[418]"
            f"305[{DIGIT_WIDTHS[305]} {DIGIT_WIDTHS[306]} {DIGIT_WIDTHS[307]} "
            f"{DIGIT_WIDTHS[308]} {DIGIT_WIDTHS[309]} {DIGIT_WIDTHS[310]} "
            f"{DIGIT_WIDTHS[311]} {DIGIT_WIDTHS[312]} {DIGIT_WIDTHS[313]} "
            f"{DIGIT_WIDTHS[314]}]"
        ).encode()

        old_w_content = w_m.group(1)
        if old_w_content == new_w_content:
            return pdf_data  # already done

        old_w_bytes = b"/W [" + old_w_content + b"]"
        new_w_bytes = b"/W [" + new_w_content + b"]"

        abs_w_start = obj_start + w_m.start()
        abs_w_end = obj_start + w_m.end()

        data = bytearray(pdf_data)
        data[abs_w_start:abs_w_end] = new_w_bytes

        delta = len(new_w_bytes) - (abs_w_end - abs_w_start)
        if delta == 0:
            return bytes(data)

        # Delta-patch xref
        xref_m = re.search(
            rb"xref\r?\n(\d+)\s+(\d+)\r?\n((?:\d{10}\s+\d{5}\s+[nf]\s*\r?\n)+)",
            data,
        )
        if xref_m:
            entries = bytearray(xref_m.group(3))
            for em in re.finditer(rb"(\d{10})(\s+\d{5}\s+[nf]\s*\r?\n)", entries):
                offset = int(em.group(1))
                if offset > abs_w_start:
                    entries[em.start(1) : em.start(1) + 10] = (
                        f"{offset + delta:010d}".encode()
                    )
            data[xref_m.start(3) : xref_m.end(3)] = bytes(entries)

        sxref_m = re.search(rb"startxref\r?\n(\d+)\r?\n", data)
        if sxref_m and delta != 0:
            old_sxref = int(sxref_m.group(1))
            if abs_w_start < old_sxref:
                pos = sxref_m.start(1)
                old_s = sxref_m.group(1)
                data[pos : pos + len(old_s)] = str(old_sxref + delta).encode()

        return bytes(data)

    return pdf_data


def enrich_pdf(input_path: Path, output_path: Path) -> bool:
    """Enrich a T-Bank donor PDF by injecting digit glyphs into F2 font.

    Returns True if the output was written (modified or already enriched).
    """
    pdf_data = input_path.read_bytes()

    # Find F1 (Regular) and F2 (Medium) font streams
    f1_info = _find_font_stream(pdf_data, "Regular")
    f2_info = _find_font_stream(pdf_data, "Medium")

    if not f1_info:
        print(f"[ERROR] F1 (Regular) font stream not found in {input_path.name}")
        return False
    if not f2_info:
        print(f"[ERROR] F2 (Medium) font stream not found in {input_path.name}")
        return False

    f1_start, f1_len, f1_len_pos, f1_bytes = f1_info
    f2_start, f2_len, f2_len_pos, f2_bytes = f2_info

    # Load fonts
    f1_font = TTFont(BytesIO(f1_bytes))
    f2_font = TTFont(BytesIO(f2_bytes))

    # Find which digit GIDs are empty in F2
    missing = [gid for gid in DIGIT_GIDS if _glyph_is_empty(f2_font, gid)]

    if not missing:
        print(f"[OK] {input_path.name}: F2 already has all digit glyphs")
        f1_font.close()
        f2_font.close()
        # Still write the output (update /W)
        pdf_data = _update_medium_w_array(pdf_data)
        output_path.write_bytes(pdf_data)
        return True

    print(f"[INFO] {input_path.name}: F2 missing digit GIDs {missing} — injecting from F1")

    # Copy glyphs from F1 to F2
    copied = []
    for gid in missing:
        if _copy_glyph_at_gid(f1_font, f2_font, gid):
            copied.append(gid)
        else:
            print(f"  [WARN] Could not copy GID {gid} (empty in F1?)")

    if not copied:
        print(f"[ERROR] No glyphs copied — F1 source may be empty")
        f1_font.close()
        f2_font.close()
        return False

    # Serialize enriched F2
    buf = BytesIO()
    f2_font.save(buf)
    new_f2_bytes = buf.getvalue()
    f1_font.close()
    f2_font.close()

    digits_str = "".join(chr(0x30 + (gid - 305)) for gid in copied)
    print(f"  Injected digits: {digits_str}  ({len(f2_bytes)} → {len(new_f2_bytes)} bytes)")

    # Patch F2 font stream in PDF
    pdf_data = _patch_font_stream(pdf_data, f2_start, f2_len, f2_len_pos, new_f2_bytes)

    # Update F2 /W array in CIDFont dict to include all digit widths
    pdf_data = _update_medium_w_array(pdf_data)

    output_path.write_bytes(pdf_data)
    print(f"  Saved enriched PDF: {output_path}")
    return True


def enrich_all(tbank_dir: Path = TBANK_DIR) -> list[Path]:
    """Enrich all PDFs in tbank_dir (skip already-enriched files).

    Returns list of output paths.
    """
    outputs = []
    for pdf_path in sorted(tbank_dir.glob("*.pdf")):
        if "_enriched" in pdf_path.stem:
            continue
        out = pdf_path.with_stem(pdf_path.stem + "_enriched")
        if enrich_pdf(pdf_path, out):
            outputs.append(out)
    return outputs


def main() -> int:
    if len(sys.argv) >= 2:
        inp = Path(sys.argv[1])
        out = Path(sys.argv[2]) if len(sys.argv) >= 3 else inp.with_stem(inp.stem + "_enriched")
        return 0 if enrich_pdf(inp, out) else 1
    else:
        outputs = enrich_all()
        if not outputs:
            print("[WARN] No PDFs enriched")
        return 0


if __name__ == "__main__":
    sys.exit(main())
