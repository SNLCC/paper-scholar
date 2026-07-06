#!/usr/bin/env python3
"""
extract_pdf_text.py — Extract text from academic PDFs.

Primary engine: MinerU online API (best accuracy for academic PDFs).
Fallback chain when MinerU is unavailable/over limit:
  1. Warn user to install PyMuPDF → use it if available
  2. Warn user to install pdfplumber → use it if available
  3. Built-in zero-dep fallback (last resort)

Only warns, never installs anything automatically.
Only hard dependency: requests (for MinerU API).

Usage:
    python extract_pdf_text.py <pdf_path> [--output <txt_path>]
    python extract_pdf_text.py <pdf_path> --stdout
    python extract_pdf_text.py <pdf_path> --engine mineru
    python extract_pdf_text.py <pdf_path> --engine local     # try local engines
    python extract_pdf_text.py <pdf_path> --engine pymupdf   # force PyMuPDF
    python extract_pdf_text.py <pdf_path> --force-mineru
    python extract_pdf_text.py <pdf_path> --show-info
"""

import argparse
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests  # hard dependency — only this one is required


# ===================================================================
#  Engine detection (lazy — printed as prompts, not auto-imported)
# ===================================================================

def _check_pymupdf() -> bool:
    try:
        import fitz  # noqa: F401
        return True
    except ImportError:
        return False


def _check_pdfplumber() -> bool:
    try:
        import pdfplumber  # noqa: F401
        return True
    except ImportError:
        return False


def _warn_not_installed(name: str, cmd: str):
    print(f"\n⚠️  {name} 未安装。需要离线提取时请手动安装：", file=sys.stderr)
    print(f"   {cmd}", file=sys.stderr)


# ===================================================================
#  Engine 1 — MinerU API (primary)
# ===================================================================

_MINERU_AGENT_BASE = "https://mineru.net/api/v1/agent"
_MINERU_PRECISE_BASE = "https://mineru.net/api/v4/extract"


def _config_path() -> Path:
    """Path to persistent config file (.paper-scholar/config.json)."""
    from _paths import data_root
    return data_root() / "config.json"


def _load_config() -> dict:
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_mineru_token() -> str | None:
    """Return token from env var, config file, or None."""
    token = os.environ.get("MINERU_TOKEN")
    if token:
        return token
    config = _load_config()
    return config.get("mineru_token") or None


def _mineru_agent_submit_file(pdf_path: str) -> str | None:
    file_name = Path(pdf_path).name
    data = {"file_name": file_name, "language": "ch", "enable_table": True, "is_ocr": True}
    try:
        resp = requests.post(f"{_MINERU_AGENT_BASE}/parse/file", json=data, timeout=30)
        result = resp.json()
        if result.get("code") != 0:
            print(f"MinerU Agent submit failed: {result.get('msg')}", file=sys.stderr)
            return None
        task_id = result["data"]["task_id"]
        file_url = result["data"]["file_url"]
        with open(pdf_path, "rb") as f:
            put_resp = requests.put(file_url, data=f, timeout=120)
        if put_resp.status_code not in (200, 201):
            print(f"MinerU file upload failed, HTTP {put_resp.status_code}", file=sys.stderr)
            return None
        return task_id
    except Exception as e:
        print(f"MinerU Agent submit error: {e}", file=sys.stderr)
        return None


def _mineru_precise_upload_file(pdf_path: str, token: str) -> str | None:
    file_name = Path(pdf_path).name
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    data = {"files": [{"name": file_name}], "model_version": "vlm"}
    try:
        resp = requests.post(f"{_MINERU_PRECISE_BASE.rsplit('/', 1)[0]}/file-urls/batch",
                             json=data, headers=headers, timeout=30)
        result = resp.json()
        if result.get("code") != 0:
            print(f"Precise upload URL申请失败: {result.get('msg')}", file=sys.stderr)
            return None
        urls = result["data"]["file_urls"]
        if not urls:
            return None
        with open(pdf_path, "rb") as f:
            put_resp = requests.put(urls[0], data=f, timeout=120)
        if put_resp.status_code not in (200, 201):
            print(f"Precise file upload failed, HTTP {put_resp.status_code}", file=sys.stderr)
            return None
        return f"precise:{result['data']['batch_id']}"
    except Exception as e:
        print(f"Precise upload error: {e}", file=sys.stderr)
        return None


_MINERU_STATE_LABELS = {
    "pending": "排队中", "uploading": "文件下载中",
    "running": "解析中", "waiting-file": "等待文件上传",
}


def _mineru_poll_result(task_id: str, use_precise: bool = False, timeout: int = 300) -> str | None:
    if use_precise:
        token = _get_mineru_token()
        if not token:
            return None
        poll_url = f"{_MINERU_PRECISE_BASE}/task/{task_id}"
        headers = {"Authorization": f"Bearer {token}"}
    else:
        poll_url = f"{_MINERU_AGENT_BASE}/parse/{task_id}"
        headers = {}

    start = time.time()
    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        try:
            resp = requests.get(poll_url, headers=headers, timeout=30)
            result = resp.json()
        except Exception as e:
            print(f"[{elapsed}s] Poll error: {e}", file=sys.stderr)
            time.sleep(5)
            continue
        if result.get("code") != 0:
            print(f"[{elapsed}s] Poll API error: {result.get('msg')}", file=sys.stderr)
            time.sleep(5)
            continue
        state = result["data"]["state"]
        if state == "done":
            if use_precise:
                zip_url = result["data"].get("full_zip_url")
                if not zip_url:
                    return None
                try:
                    zip_resp = requests.get(zip_url, timeout=60)
                    import io, zipfile
                    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                        md = [n for n in zf.namelist() if n.endswith("full.md")]
                        if md:
                            return zf.read(md[0]).decode("utf-8", errors="replace")
                        mds = [n for n in zf.namelist() if n.endswith(".md")]
                        if mds:
                            return zf.read(mds[0]).decode("utf-8", errors="replace")
                    return None
                except Exception as e:
                    print(f"Zip extract error: {e}", file=sys.stderr)
                    return None
            else:
                md_url = result["data"].get("markdown_url")
                if not md_url:
                    return None
                try:
                    return requests.get(md_url, timeout=60).text
                except Exception as e:
                    print(f"Download error: {e}", file=sys.stderr)
                    return None
        elif state == "failed":
            err_msg = result["data"].get("err_msg", "unknown")
            print(f"[{elapsed}s] MinerU failed: {err_msg}", file=sys.stderr)
            return None
        print(f"[{elapsed}s] {_MINERU_STATE_LABELS.get(state, state)}...", file=sys.stderr)
        time.sleep(3)
    print(f"Poll timeout ({timeout}s), task_id: {task_id}", file=sys.stderr)
    return None


def extract_with_mineru(pdf_path: str, force_precise: bool = False) -> str:
    """Extract text using MinerU API (online OCR)."""
    pdf_obj = Path(pdf_path)
    size_mb = pdf_obj.stat().st_size / (1024 * 1024) if pdf_obj.exists() else 0
    token = _get_mineru_token()

    if not force_precise and size_mb <= 10:
        print(f"MinerU Agent API 提交中... ({size_mb:.1f}MB)", file=sys.stderr)
        tid = _mineru_agent_submit_file(pdf_path)
        if tid:
            r = _mineru_poll_result(tid)
            if r:
                return r
        print("Agent API 不可用或文件超限，尝试 Precise API...", file=sys.stderr)

    if token:
        label = "Precise" if force_precise else "Precise (fallback)"
        print(f"MinerU {label} API 提交中... ({size_mb:.1f}MB)", file=sys.stderr)
        tid = _mineru_precise_upload_file(pdf_path, token)
        if tid:
            r = _mineru_poll_result(tid, use_precise=True)
            if r:
                return r
    elif force_precise:
        print("错误: --force-mineru 需要设置 MINERU_TOKEN 环境变量", file=sys.stderr)
    else:
        print("MinerU 不可用 (文件 >10MB 或 Agent API 失败)，且未设置 MINERU_TOKEN", file=sys.stderr)
    return ""


# ===================================================================
#  Local engines (prompted install fallbacks)
# ===================================================================

def extract_with_pymupdf(pdf_path: str, skip_header_footer: bool = True) -> str:
    """Extract using PyMuPDF (fitz). Requires manual install.

    When skip_header_footer is True (default), uses block-level position
    information to filter out:
      - Page headers (top 8% of each page)
      - Page footers (bottom 8% of each page)
      - Standalone page numbers (pure digits on their own block)
    This reduces common PDF noise without needing layout analysis.
    """
    import fitz
    doc = fitz.open(pdf_path)
    pages_text = []

    for page in doc:
        if skip_header_footer:
            blocks = page.get_text("blocks")
            page_h = page.rect.height
            lines = []
            for b in blocks:
                x0, y0, x1, y1, text, block_no, block_type = b
                # Skip header/footer regions
                if y0 < page_h * 0.08 or y1 > page_h * 0.92:
                    continue
                # Skip standalone page numbers
                text_stripped = text.strip()
                if text_stripped.isdigit() and len(text_stripped) <= 4:
                    continue
                lines.append(text_stripped)
            pages_text.append("\n".join(lines))
        else:
            text = page.get_text()
            pages_text.append(text.strip() if text else "")

    doc.close()
    return "\n\n".join(pages_text)


def _detect_double_column_pymupdf(pdf_path: str, min_block_count: int = 3) -> dict:
    import fitz
    doc = fitz.open(pdf_path)
    if not doc:
        return {"is_double_column": False, "pages_analyzed": 0, "double_pages": 0,
                "left_counts": [], "right_counts": []}
    page_w = doc[0].rect.width
    mid_x = page_w / 2
    left_counts, right_counts = [], []
    for page in doc:
        blocks = page.get_text("blocks")
        left = sum(1 for b in blocks if b[0] < mid_x - 20)
        right = sum(1 for b in blocks if b[0] > mid_x + 20)
        left_counts.append(left)
        right_counts.append(right)
    doc.close()
    double_pages = sum(1 for l, r in zip(left_counts, right_counts)
                       if l >= min_block_count and r >= min_block_count)
    is_double = double_pages >= len(left_counts) * 0.5 if left_counts else False
    return {"is_double_column": is_double, "pages_analyzed": len(left_counts),
            "double_pages": double_pages, "left_counts": left_counts, "right_counts": right_counts}


def _extract_with_explicit_columns_pymupdf(pdf_path: str) -> str:
    import fitz
    doc = fitz.open(pdf_path)
    detection = _detect_double_column_pymupdf(pdf_path)
    all_text = []
    for page in doc:
        page_dict = page.get_text("dict")
        blocks = [b for b in page_dict.get("blocks", []) if "lines" in b]
        if not blocks:
            continue
        if detection["is_double_column"]:
            page_w = page.rect.width
            mid = page_w / 2
            left_blocks = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 < mid]
            right_blocks = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 >= mid]
            for col in [left_blocks, right_blocks]:
                col.sort(key=lambda b: b["bbox"][1])
                for block in col:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            all_text.append(span["text"])
                        all_text.append(" ")
                    all_text.append("\n")
                all_text.append("\n")
        else:
            blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
            for block in blocks:
                for line in block["lines"]:
                    for span in line["spans"]:
                        all_text.append(span["text"])
                    all_text.append(" ")
                all_text.append("\n")
        all_text.append("\n")
    doc.close()
    return "".join(all_text)


def extract_with_pymupdf_v62(pdf_path: str) -> tuple:
    """PyMuPDF double-column self-check + character-bag cross-validation."""
    import fitz
    default_text = extract_with_pymupdf(pdf_path)
    detection = _detect_double_column_pymupdf(pdf_path)
    is_double = detection["is_double_column"]
    info = {"method": "default", "is_double_column": is_double, "detection_detail": detection,
            "chars_count": len(default_text), "normalized_match": True, "similarity": 1.0, "warning": None}
    if not is_double:
        return default_text, info

    explicit_text = _extract_with_explicit_columns_pymupdf(pdf_path)

    def _norm(s):
        return "".join(c for c in s if not c.isspace() and ord(c) >= 0x20)
    d, e = _norm(default_text), _norm(explicit_text)
    db, eb = Counter(d), Counter(e)
    common = sum((db & eb).values())
    total = max(sum(db.values()), sum(eb.values()))
    similarity = common / total if total > 0 else 1.0
    match = similarity >= 0.99

    if match:
        final_text = default_text
        info["method"] = "default"
        info["warning"] = None if similarity >= 1.0 else f"Similarity={similarity:.4f}, using default"
    else:
        final_text = explicit_text
        info["method"] = "explicit"
        info["warning"] = f"Similarity={similarity:.4f}, switched to explicit columns"
    info["chars_count"] = len(final_text)
    info["normalized_match"] = match
    info["similarity"] = similarity
    return final_text, info


def extract_with_pdfplumber(pdf_path: str) -> str:
    """Extract using pdfplumber. Requires manual install."""
    import pdfplumber
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3,
                                     keep_blank_chars=False, use_text_flow=False)
            if text and text.strip():
                pages_text.append(text.strip())
    return "\n\n".join(pages_text)


def extract_with_pdfplumber_v62(pdf_path: str) -> tuple:
    """pdfplumber double-column self-check (fallback)."""
    import pdfplumber
    default_text = extract_with_pdfplumber(pdf_path)
    from collections import Counter as Ctr
    # Simple column detection via words
    with pdfplumber.open(pdf_path) as pdf:
        double_pages = 0
        total_pages = len(pdf.pages)
        for page in pdf.pages:
            mid_x = page.width / 2
            words = page.extract_words(keep_blank_chars=False)
            left = sum(1 for w in words if w["x0"] < mid_x - 10)
            right = sum(1 for w in words if w["x0"] > mid_x + 10)
            if left >= 3 and right >= 3:
                double_pages += 1
    is_double = double_pages >= total_pages * 0.5 if total_pages else False

    info = {"method": "default", "is_double_column": is_double,
            "chars_count": len(default_text), "normalized_match": True, "similarity": 1.0, "warning": None}
    if not is_double:
        return default_text, info

    all_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(keep_blank_chars=False)
            if not words:
                continue
            mid_x = page.width / 2
            left = sorted([w for w in words if w["x0"] < mid_x], key=lambda w: w["top"])
            right = sorted([w for w in words if w["x0"] >= mid_x], key=lambda w: w["top"])
            for col in [left, right]:
                parts, last_top = [], None
                for w in col:
                    if last_top is not None and abs(w["top"] - last_top) > 5:
                        parts.append("\n")
                    parts.append(w["text"])
                    last_top = w["top"]
                all_text.append(" ".join(parts))
                all_text.append("\n\n")
    explicit_text = "".join(all_text).strip()

    def _norm(s):
        return "".join(c for c in s if not c.isspace() and ord(c) >= 0x20)
    d, e = _norm(default_text), _norm(explicit_text)
    db, eb = Ctr(d), Ctr(e)
    common = sum((db & eb).values())
    total = max(sum(db.values()), sum(eb.values()))
    similarity = common / total if total > 0 else 1.0
    match = similarity >= 0.99
    if match:
        final_text = default_text
        info["method"] = "default"
        info["warning"] = None if similarity >= 1.0 else f"Similarity={similarity:.4f}, using default"
    else:
        final_text = explicit_text
        info["method"] = "explicit"
        info["warning"] = f"Similarity={similarity:.4f}, switched to explicit columns"
    info["chars_count"] = len(final_text)
    info["normalized_match"] = match
    info["similarity"] = similarity
    return final_text, info


# ===================================================================
#  Built-in (zero-dependency last resort)
# ===================================================================

from _extract_builtin import extract_with_builtin


# ===================================================================
#  Public API
# ===================================================================

def _print_info(info: dict, label: str = "PyMuPDF"):
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"双栏自检报告 ({label})", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"双栏判定: {info['is_double_column']}", file=sys.stderr)
    print(f"提取方法: {info['method']}", file=sys.stderr)
    if info.get("detection_detail"):
        d = info["detection_detail"]
        print(f"双栏页面: {d['double_pages']}/{d['pages_analyzed']}", file=sys.stderr)
    if info.get("similarity") is not None and info["similarity"] < 1.0:
        print(f"字符袋相似度: {info['similarity']:.4f}", file=sys.stderr)
    if info.get("warning"):
        print(f"警告: {info['warning']}", file=sys.stderr)
    print(f"提取字符: {info.get('chars_count', 0)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


def extract_text(pdf_path: str, engine: str = "auto",
                 show_info: bool = False,
                 mineru_token: str | None = None) -> str:
    """Extract text from an academic PDF.

    Engine chains:
      auto      → MinerU → (fail) → prompt PyMuPDF → prompt pdfplumber → builtin
      mineru    → MinerU only
      local     → PyMuPDF → pdfplumber → builtin (no network)
      pymupdf   → PyMuPDF only
      pymupdf-v62 → PyMuPDF with double-column self-check
      pdfplumber → pdfplumber only
      builtin   → built-in zero-dep only
    """
    if mineru_token:
        os.environ["MINERU_TOKEN"] = mineru_token

    # ---- MinerU primary path ----
    if engine in ("auto", "mineru"):
        text = extract_with_mineru(pdf_path)
        if text:
            return text

        if engine == "mineru":
            print("MinerU 提取失败，请检查网络或 MINERU_TOKEN 设置。", file=sys.stderr)
            return text  # empty

        # auto: fall through to local engines
        print("\n--- MinerU 不可用，尝试本地引擎 ---", file=sys.stderr)

    if engine == "local":
        pass  # skip MinerU, go straight to local engines

    # ---- Local engines (warn on missing, gracefully skip) ----
    if engine in ("auto", "local", "pymupdf", "pymupdf-v62"):
        if not _check_pymupdf():
            _warn_not_installed("PyMuPDF", "pip install PyMuPDF")
            if engine in ("pymupdf", "pymupdf-v62"):
                sys.exit(1)
            print("尝试下一个引擎...", file=sys.stderr)
            engine = "pdfplumber" if engine in ("auto", "local") else engine

        if _check_pymupdf():
            if engine == "pymupdf-v62":
                text, info = extract_with_pymupdf_v62(pdf_path)
                if show_info:
                    _print_info(info, "PyMuPDF")
                return text
            else:
                text = extract_with_pymupdf(pdf_path)
                if show_info:
                    import fitz
                    det = _detect_double_column_pymupdf(pdf_path)
                    _print_info({"method": "default", "is_double_column": det["is_double_column"],
                                 "detection_detail": det, "chars_count": len(text),
                                 "normalized_match": True, "similarity": 1.0, "warning": None}, "PyMuPDF")
                return text

    if engine in ("auto", "local", "pdfplumber", "pdfplumber-v62"):
        if not _check_pdfplumber():
            _warn_not_installed("pdfplumber", "pip install pdfplumber")
            if engine in ("pdfplumber", "pdfplumber-v62"):
                sys.exit(1)
            print("跳过 pdfplumber。", file=sys.stderr)

        if _check_pdfplumber():
            if engine == "pdfplumber-v62":
                text, info = extract_with_pdfplumber_v62(pdf_path)
                if show_info:
                    _print_info(info, "pdfplumber")
                return text
            else:
                return extract_with_pdfplumber(pdf_path)

    # ---- Last resort ----
    return extract_with_builtin(pdf_path)


# ===================================================================
#  CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract text from academic PDFs (MinerU online → local fallbacks)")
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--output", "-o", help="Output text file path")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout")
    parser.add_argument("--engine", choices=["auto", "mineru", "local", "pymupdf", "pymupdf-v62",
                                              "pdfplumber", "pdfplumber-v62", "builtin"],
                        default="auto",
                        help="Engine (default: auto = MinerU → prompt local → builtin)")
    parser.add_argument("--show-info", action="store_true",
                        help="Show extraction details (detection report)")
    parser.add_argument("--force-mineru", action="store_true",
                        help="Force MinerU OCR (requires MINERU_TOKEN for large files)")
    parser.add_argument("--mineru-token",
                        help="MinerU API token (overrides MINERU_TOKEN env var)")
    parser.add_argument("--save-mineru-token", action="store_true",
                        help="Save --mineru-token to config.json for future use")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Save token to config if requested
    if args.save_mineru_token and args.mineru_token:
        config = _load_config()
        config["mineru_token"] = args.mineru_token
        _save_config(config)
        print(f"Token saved to {_config_path()}", file=sys.stderr)

    if args.force_mineru:
        text = extract_with_mineru(str(pdf_path), force_precise=True)
    else:
        text = extract_text(str(pdf_path), engine=args.engine,
                            show_info=args.show_info, mineru_token=args.mineru_token)

    if not text:
        print("所有引擎均无法提取文本。", file=sys.stderr)
        sys.exit(1)

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
