#!/usr/bin/env python3
"""
extract_pdf_text.py — Extract text from academic PDFs.

Three engines:

  1. pdfplumber (MIT) — primary engine. Best for most PDFs.
  2. PyMuPDF (AGPL, optional) — handles CNKI custom fonts (HGFX_CNKI) better.
     Install separately: pip install pymupdf
  3. Built-in fallback (Python stdlib) — zero dependencies, limited layout.

Engine auto-selection order: pdfplumber → pymupdf (if installed) → builtin

Usage:
    python extract_pdf_text.py <pdf_path> [--output <txt_path>]
    python extract_pdf_text.py <pdf_path> --stdout
    python extract_pdf_text.py <pdf_path> --engine pdfplumber
    python extract_pdf_text.py <pdf_path> --engine pymupdf    # AGPL, opt-in
    python extract_pdf_text.py <pdf_path> --engine builtin
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Engine detection
# ---------------------------------------------------------------------------

_HAS_PDFPLUMBER = False
try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    pass

_HAS_PYMUPDF = False
try:
    import fitz  # PyMuPDF
    _HAS_PYMUPDF = True
except ImportError:
    pass


# ===================================================================
#  Engine 1 — pdfplumber (MIT license)
# ===================================================================

def _extract_with_pdfplumber(pdf_path: str) -> str:
    """Extract text using pdfplumber.

    Advantages:
      - Reads pages in natural order
      - Handles multi-column layouts via word-level extraction
      - Preserves paragraph boundaries
      - Good CJK support (pdfminer.six handles ToUnicode CMaps)
    """
    import pdfplumber
    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract text with layout-aware settings
            text = page.extract_text(
                x_tolerance=3,       # Merge characters with small x-gaps (same word)
                y_tolerance=3,       # Merge lines close together (same paragraph)
                keep_blank_chars=False,
                use_text_flow=False, # Keep natural reading order
            )
            if text and text.strip():
                pages_text.append(text.strip())

    return "\n\n".join(pages_text)


# ===================================================================
#  Engine 2 — PyMuPDF (AGPL, optional)
#  For PDFs with CNKI custom fonts (HGFX_CNKI) where ToUnicode
#  mappings are incomplete. Install: pip install pymupdf
# ===================================================================

def _extract_with_pymupdf(pdf_path: str) -> str:
    """Extract text using PyMuPDF (fitz).

    Better at handling custom CJK fonts with incomplete CMap,
    such as CNKI's HGFX_CNKI.
    """
    import fitz
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text and text.strip():
            pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages)


# ===================================================================
#  Engine 3 — Built-in (zero external deps)
# ===================================================================

def _read_until(data: bytes, start: int, delimiter: bytes) -> tuple[bytes, int]:
    end = data.find(delimiter, start)
    if end == -1:
        return data[start:], len(data)
    return data[start:end], end + len(delimiter)


def _decode_pdf_string(raw: bytes) -> str:
    raw = raw.strip()
    if raw.startswith(b"("):
        result = []
        i = 1
        depth = 1
        while i < len(raw) and depth > 0:
            c = raw[i]
            if c == 0x5c:
                if i + 1 < len(raw):
                    n = raw[i + 1]
                    esc_map = {b"n": "\n", b"r": "\r", b"t": "\t",
                               b"(": "(", b")": ")", b"\\": "\\"}
                    if n in esc_map:
                        result.append(esc_map[n])
                    elif n in (b"0", b"1", b"2", b"3", b"4", b"5", b"6", b"7"):
                        oct_str = raw[i:i + 3].decode("latin-1")
                        try:
                            result.append(chr(int(oct_str, 8)))
                        except ValueError:
                            result.append("?")
                        i += 2
                    else:
                        result.append(chr(n))
                    i += 2
                else:
                    i += 1
            elif c == 0x28:
                depth += 1
                result.append("(")
                i += 1
            elif c == 0x29:
                depth -= 1
                if depth > 0:
                    result.append(")")
                i += 1
            else:
                result.append(chr(c))
                i += 1
        return "".join(result)
    elif raw.startswith(b"<") and raw.endswith(b">"):
        hex_data = raw[1:-1].strip()
        if not hex_data:
            return ""
        raw_bytes = bytes.fromhex(hex_data.decode("ascii", errors="replace"))
        for enc in ("utf-8", "gb18030", "latin-1"):
            try:
                return raw_bytes.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw_bytes.decode("latin-1", errors="replace")
    return raw.decode("latin-1", errors="replace")


def _tokenize_content(data: bytes) -> list:
    tokens = []
    i = 0
    while i < len(data):
        if data[i] in (0x20, 0x0a, 0x0d, 0x09, 0x00):
            i += 1
            continue
        if data[i] == 0x25:
            _, i = _read_until(data, i, b"\n")
            continue
        if data[i] == 0x28:
            depth = 1
            j = i + 1
            while j < len(data) and depth > 0:
                if data[j] == 0x5c:
                    j += 2
                    continue
                if data[j] == 0x28:
                    depth += 1
                elif data[j] == 0x29:
                    depth -= 1
                j += 1
            tokens.append(("string", data[i:j]))
            i = j
            continue
        if data[i] == 0x3c and i + 1 < len(data) and data[i + 1] == 0x3c:
            tokens.append(("dict_start", b"<<"))
            i += 2
            continue
        if data[i] == 0x3e and i + 1 < len(data) and data[i + 1] == 0x3e:
            tokens.append(("dict_end", b">>"))
            i += 2
            continue
        if data[i] == 0x3c:
            depth = 1
            j = i + 1
            while j < len(data) and depth > 0:
                if data[j] == 0x3e:
                    depth -= 1
                elif data[j] == 0x3c:
                    depth += 1
                j += 1
            tokens.append(("string", data[i:j]))
            i = j
            continue
        if data[i] == 0x5b:
            depth = 1
            j = i + 1
            while j < len(data) and depth > 0:
                if data[j] == 0x5d:
                    depth -= 1
                elif data[j] == 0x5b:
                    depth += 1
                j += 1
            tokens.append(("array", data[i:j]))
            i = j
            continue
        if data[i] == 0x5d:
            tokens.append(("array_end", b"]"))
            i += 1
            continue
        if data[i] == 0x2f:
            j = i + 1
            while j < len(data) and data[j] not in (0x20, 0x0a, 0x0d, 0x09, 0x28, 0x29, 0x3c, 0x3e, 0x5b, 0x5d, 0x2f):
                j += 1
            tokens.append(("name", data[i:j].decode("latin-1", errors="replace")))
            i = j
            continue
        if data[i] in b"0123456789+-." or (data[i] == 0x2e):
            j = i
            while j < len(data) and data[j] in b"0123456789+-.eE":
                j += 1
            try:
                num = float(data[i:j]) if b"." in data[i:j] or b"e" in data[i:j] or b"E" in data[i:j] else int(data[i:j])
                tokens.append(("number", num))
            except ValueError:
                pass
            i = j
            continue
        if chr(data[i]) if data[i] < 128 else False in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
            j = i
            while j < len(data) and chr(data[j]) if data[j] < 128 else False in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'\"*":
                if data[j] > 127:
                    break
                j += 1
            if j > i:
                tokens.append(("operator", data[i:j].decode("latin-1")))
                i = j
                continue
        i += 1
    return tokens


def _extract_dict_inner(data: bytes) -> bytes | None:
    start = data.find(b"<<")
    if start < 0:
        return None
    depth = 0
    pos = start + 2
    while pos < len(data):
        if data[pos] == 0x3c and pos + 1 < len(data) and data[pos + 1] == 0x3c:
            depth += 1
            pos += 2
        elif data[pos] == 0x3e and pos + 1 < len(data) and data[pos + 1] == 0x3e:
            if depth == 0:
                return data[start + 2:pos]
            depth -= 1
            pos += 2
        else:
            pos += 1
    return None


def _parse_dict(data: bytes) -> dict:
    result = {}
    inner = _extract_dict_inner(data)
    if inner is None:
        return result
    tokens = _tokenize_content(inner)
    i = 0
    while i < len(tokens):
        if tokens[i][0] != "name":
            i += 1
            continue
        key = tokens[i][1].lstrip("/")
        if i + 1 >= len(tokens):
            break
        if (i + 3 < len(tokens) and tokens[i + 1][0] == "number"
                and tokens[i + 2][0] == "number"
                and tokens[i + 3][0] == "operator"
                and tokens[i + 3][1] == "R"):
            result[key] = f"ref:{tokens[i + 1][1]}"
            i += 4
            continue
        val = tokens[i + 1]
        if val[0] == "dict_start":
            depth = 1
            j = i + 2
            while j < len(tokens) and depth > 0:
                if tokens[j][0] == "dict_start":
                    depth += 1
                elif tokens[j][0] == "dict_end":
                    depth -= 1
                j += 1
            i = j
        elif val[0] == "name":
            result[key] = val[1]
            i += 2
        elif val[0] == "number":
            result[key] = val[1]
            i += 2
        elif val[0] == "string":
            result[key] = _decode_pdf_string(val[1])
            i += 2
        elif val[0] == "array":
            result[key] = val[1]
            i += 2
        else:
            i += 1
    return result


def _get_obj_raw(objects: dict, obj_num: int) -> bytes | None:
    if obj_num in objects:
        raw = objects[obj_num][2]
        m = re.search(rb"\d+\s+\d+\s+obj\b", raw)
        if m:
            content = raw[m.end():]
            end = content.rfind(b"endobj")
            if end >= 0:
                return content[:end].strip()
        return raw
    return None


def _find_objects_builtin(data: bytes) -> dict:
    objects = {}
    xref_pos = -1
    xs = data.rfind(b"\nxref\n")
    if xs >= 0:
        xref_pos = xs + 1
    if xref_pos < 0:
        xs = data.rfind(b"\nxref ")
        if xs >= 0:
            xref_pos = xs + 1
    if xref_pos >= 0:
        pos = xref_pos + 4
        while pos < len(data):
            line, pos = _read_until(data, pos, b"\n")
            line = line.strip()
            if not line or line.startswith(b"%"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                start_num = int(parts[0])
                count = int(parts[1])
            except ValueError:
                break
            for _ in range(count):
                line, pos = _read_until(data, pos, b"\n")
                line = line.rstrip(b"\r\n ")
                if len(line) < 18:
                    start_num += 1
                    continue
                if chr(line[17]) != "n":
                    start_num += 1
                    continue
                try:
                    offset = int(line[:10])
                except (ValueError, IndexError):
                    start_num += 1
                    continue
                obj_marker = data.find(b"obj", offset)
                if obj_marker < 0 or obj_marker > offset + 30:
                    start_num += 1
                    continue
                obj_end = data.find(b"endobj", obj_marker)
                if obj_end < 0:
                    start_num += 1
                    continue
                objects[start_num] = (offset, 0, data[offset:obj_end + 6])
                start_num += 1
            if data[pos:pos + 7] == b"trailer":
                break
    return objects


def _collect_streams_builtin(objects: dict) -> list[bytes]:
    import zlib
    streams = []
    for _, _, raw in objects.items():
        if b"/Type" in raw and b"/Pages" in raw and b"/Kids" in raw:
            page_dict = _parse_dict(raw)
            kids_val = page_dict.get("Kids")
            if isinstance(kids_val, bytes):
                kid_refs = re.findall(rb"(\d+)\s+\d+\s+R", kids_val)
            else:
                continue
            for page_num in (int(r) for r in kid_refs):
                page_raw = _get_obj_raw(objects, page_num)
                if page_raw is None:
                    continue
                paged = _parse_dict(page_raw)
                content_val = paged.get("Contents")
                if content_val is None:
                    continue
                content_refs = []
                if isinstance(content_val, str) and content_val.startswith("ref:"):
                    content_refs = [int(content_val.split(":")[1])]
                elif isinstance(content_val, bytes):
                    content_refs = [int(r) for r in re.findall(rb"(\d+)\s+\d+\s+R", content_val)]
                for cn in content_refs:
                    obj_raw = _get_obj_raw(objects, cn)
                    if obj_raw:
                        m = re.search(rb"stream\s(.+?)\s*endstream", obj_raw, re.DOTALL)
                        if m:
                            raw_data = m.group(1)
                            for fn in (lambda d: zlib.decompress(d), lambda d: zlib.decompress(d, -zlib.MAX_WBITS)):
                                try:
                                    raw_data = fn(raw_data)
                                    break
                                except (zlib.error, ValueError):
                                    continue
                            streams.append(raw_data)
            break
    return streams


def _extract_text_builtin(stream_data: bytes) -> str:
    tokens = _tokenize_content(stream_data)
    parts = []
    i = 0
    while i < len(tokens):
        if tokens[i][0] != "operator":
            i += 1
            continue
        op = tokens[i][1]
        if op == "Tj" and i > 0 and tokens[i - 1][0] == "string":
            parts.append(_decode_pdf_string(tokens[i - 1][1]))
        elif op == "'" and i > 0 and tokens[i - 1][0] == "string":
            parts.append("\n" + _decode_pdf_string(tokens[i - 1][1]))
        elif op == '"' and i > 2:
            for k in (i - 1, i - 2):
                if tokens[k][0] == "string":
                    parts.append("\n" + _decode_pdf_string(tokens[k][1]))
                    break
        elif op == "TJ" and i > 0 and tokens[i - 1][0] == "array":
            arr = tokens[i - 1][1]
            inner = arr.strip()
            if inner.startswith(b"[") and inner.endswith(b"]"):
                inner = inner[1:-1].strip()
            for t in _tokenize_content(inner):
                if t[0] == "string":
                    parts.append(_decode_pdf_string(t[1]))
                elif t[0] == "number" and t[1] < -100:
                    parts.append(" ")
        elif op == "Td" or op == "TD":
            parts.append("\n")
        i += 1
    return "".join(parts).strip()


def _extract_with_builtin(pdf_path: str) -> str:
    """Fallback: extract text using only Python stdlib."""
    data = Path(pdf_path).read_bytes()
    if not data.startswith(b"%PDF-"):
        return ""
    objects = _find_objects_builtin(data)
    if not objects:
        return ""
    streams = _collect_streams_builtin(objects)
    if not streams:
        return ""
    all_text = []
    for s in streams:
        t = _extract_text_builtin(s)
        if t:
            all_text.append(t)
    text = "\n\n".join(all_text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ===================================================================
#  Public API
# ===================================================================

def extract_text(pdf_path: str, engine: str = "auto") -> str:
    """Extract text from an academic PDF.

    Args:
        pdf_path: Path to the PDF file.
        engine: 'auto' (try pdfplumber → pymupdf → builtin),
                'pdfplumber', 'pymupdf', or 'builtin'.

    Returns:
        Plain text of the document.
    """
    if engine == "auto":
        if _HAS_PDFPLUMBER:
            engine = "pdfplumber"
        elif _HAS_PYMUPDF:
            engine = "pymupdf"
        else:
            engine = "builtin"

    if engine == "pdfplumber":
        if not _HAS_PDFPLUMBER:
            print("Warning: pdfplumber not installed. Trying PyMuPDF...", file=sys.stderr)
            engine = "pymupdf" if _HAS_PYMUPDF else "builtin"
        else:
            return _extract_with_pdfplumber(pdf_path)

    if engine == "pymupdf":
        if not _HAS_PYMUPDF:
            print("Warning: PyMuPDF not installed. Try: pip install pymupdf", file=sys.stderr)
            print("Falling back to built-in engine.", file=sys.stderr)
            engine = "builtin"
        else:
            return _extract_with_pymupdf(pdf_path)

    return _extract_with_builtin(pdf_path)


# ===================================================================
#  CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract text from academic PDFs"
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--output", "-o", help="Output text file path")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout")
    parser.add_argument("--engine", choices=["auto", "pdfplumber", "pymupdf", "builtin"],
                        default="auto",
                        help="Extraction engine (default: auto; pymupdf is AGPL, opt-in)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    text = extract_text(str(pdf_path), engine=args.engine)

    if args.stdout:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    elif args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"Extracted text saved to: {out_path}", file=sys.stderr)
    else:
        out_path = pdf_path.with_suffix(".txt")
        out_path.write_text(text, encoding="utf-8")
        print(f"Extracted text saved to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
