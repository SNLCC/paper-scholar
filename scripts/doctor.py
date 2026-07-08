#!/usr/bin/env python3
"""doctor.py — Comprehensive health check for paper-scholar setup.

Usage:
    python scripts/doctor.py          # Full check
    python scripts/doctor.py --quick  # Quick check (first-run gate)
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass

import argparse
import json
import os
import platform
from pathlib import Path

from _paths import data_root, data_dir, models_dir, learnings_dir, prescriptions_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GREEN = "✅"
YELLOW = "⚠"
RED = "✗"
GRAY = "○"

SKILL_DIR = Path(__file__).resolve().parent.parent


def _has_config(key: str) -> str | None:
    """Read a value from config.json."""
    cfg_path = data_root() / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            return cfg.get(key)
        except Exception:
            pass
    return None


def _mask(val: str | None) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return val
    return val[:4] + "…" + val[-4:]


def _check_import(mod: str, name: str = "") -> tuple[str, str]:
    try:
        __import__(mod)
        return GREEN, f"{name or mod} 可用"
    except ImportError:
        return YELLOW, f"{name or mod} 未安装（按需安装，非必需）"


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_python() -> tuple[str, str]:
    v = sys.version_info
    ok = v.major >= 3 and v.minor >= 10
    return (GREEN if ok else YELLOW), f"Python {v.major}.{v.minor}.{v.micro} ({'✓' if ok else '建议 ≥3.10'})"


def _check_skill_path() -> tuple[str, str]:
    skill_md = SKILL_DIR / "SKILL.md"
    if skill_md.exists():
        return GREEN, str(SKILL_DIR.resolve())
    return RED, f"未找到 SKILL.md（检查 {SKILL_DIR}）"


def _check_setup_done() -> tuple[str, str]:
    marker = data_root() / ".setup_done"
    if marker.exists():
        try:
            info = json.loads(marker.read_text(encoding="utf-8"))
            ver = info.get("version", "?")
            return GREEN, f"已完成首次配置（v{ver}）"
        except Exception:
            return YELLOW, "标记文件存在但无法解析"
    return YELLOW, "尚未完成首次配置 — 运行 python run.py postinstall"


def _check_data_root() -> tuple[str, str]:
    root = data_root()
    return GREEN, str(root)


def _check_data_subdirs() -> list[tuple[str, str, str]]:
    results = []
    for name, path_fn in [("data/", data_dir), ("models/", models_dir),
                          (".learnings/", learnings_dir), ("prescriptions/", prescriptions_dir)]:
        p = path_fn()
        if p.is_dir():
            count = len(list(p.iterdir())) if name != ".learnings/" else len([f for f in p.iterdir() if f.suffix == ".json"])
            results.append((GREEN, name, f"{count} 文件" if count else "空目录"))
        else:
            results.append((GRAY, name, "不存在"))
    return results


def _check_requests() -> tuple[str, str]:
    return _check_import("requests", "requests")


def _check_pymupdf() -> tuple[str, str]:
    return _check_import("fitz", "PyMuPDF (fitz)")


def _check_pdfplumber() -> tuple[str, str]:
    return _check_import("pdfplumber", "pdfplumber")


def _check_mineru_token() -> tuple[str, str]:
    token = os.environ.get("MINERU_TOKEN") or _has_config("mineru_token")
    if token:
        return GREEN, f"Token 已配置 ({_mask(token)})"
    return YELLOW, "未配置（免 Token 可用 ≤10MB/≤20页）"


def _check_zotero_api() -> tuple[str, str]:
    key = _has_config("zotero_api_key")
    if key:
        return GREEN, f"API Key 已配置 ({_mask(key)})"
    return YELLOW, "未配置（仅在需要 Web API 时必需）"


def _check_zotero_data_dir() -> tuple[str, str]:
    # Check env var first
    env_dir = os.environ.get("ZOTERO_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            return GREEN, str(p)
        return YELLOW, f"ZOTERO_DATA_DIR 已设但目录不存在: {env_dir}"

    # Check config
    cfg_dir = _has_config("zotero_data_dir")
    if cfg_dir:
        p = Path(cfg_dir)
        if p.is_dir():
            return GREEN, str(p)
        return YELLOW, f"config.json 已配但目录不存在: {cfg_dir}"

    # Try auto-detect
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA", "")
        candidates = [
            Path(appdata) / "Zotero" / "Zotero" / "Profiles",
            Path(appdata) / "Zotero" / "Profiles",
        ]
    elif platform.system() == "Darwin":
        candidates = [Path.home() / "Zotero"]
    else:
        candidates = [Path.home() / ".zotero" / "zotero"]

    for base in candidates:
        if base.is_dir():
            return YELLOW, f"未配置（自动检测到 {base}）"
    return YELLOW, "未配置（本地 API 无需配置，Zotero 运行即可）"


def _check_webdav() -> tuple[str, str]:
    user = _has_config("webdav_user")
    pwd = _has_config("webdav_password")
    if user and pwd:
        return GREEN, f"已配置 ({user})"
    return YELLOW, "未配置（仅在需要坚果云时必需）"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def cmd_doctor():
    """Full health check — print report."""
    print()
    print("=" * 60)
    print("  paper-scholar 健康检查")
    print("=" * 60)
    print()

    # --- Environment ---
    print("  📦 运行环境")
    icon, msg = _check_python()
    print(f"    {icon} {msg}")
    icon, msg = _check_skill_path()
    print(f"    {icon} Skill 位置: {msg}")

    print()
    print("  📂 数据目录")
    icon, msg = _check_data_root()
    print(f"    {icon} 根目录: {msg}")
    for icon, name, msg in _check_data_subdirs():
        print(f"    {icon} {name:<14} {msg}")

    print()
    print("  🔧 首次配置状态")
    icon, msg = _check_setup_done()
    print(f"    {icon} {msg}")

    print()
    print("  📦 Python 依赖")
    for check_fn in [_check_requests, _check_pymupdf, _check_pdfplumber]:
        icon, msg = check_fn()
        print(f"    {icon} {msg}")

    print()
    print("  🔑 外部服务凭证")
    for check_fn in [_check_mineru_token, _check_zotero_api, _check_zotero_data_dir, _check_webdav]:
        icon, msg = check_fn()
        print(f"    {icon} {msg}")

    print()

    # --- Recommendations ---
    issues = []
    if not (_has_config("mineru_token") or os.environ.get("MINERU_TOKEN")):
        issues.append("  配置 MinerU Token（大文件解析需要）: python run.py configure --mineru-token <token>")
    if not _has_config("zotero_api_key"):
        issues.append("  配置 Zotero API Key（Web API 需要）: python run.py configure --zotero-api-key <key>")
    if not (data_root() / ".setup_done").exists():
        issues.insert(0, "  首次配置未完成: python run.py postinstall")

    if issues:
        print("  💡 建议:")
        for issue in issues:
            print(f"    {issue}")
        print()
    else:
        print("  ✅ 基础环境就绪。")
        print()

    print("  📋 完整配置向导: python run.py configure")
    print()


def cmd_quick() -> bool:
    """Quick first-run gate — return True if setup is complete."""
    # Check marker
    if (data_root() / ".setup_done").exists():
        return True

    # No marker — guide user
    print()
    print("=" * 60)
    print("  ⚠ paper-scholar 首次使用检测")
    print("=" * 60)
    print()
    print("  检测到首次使用，需要完成以下步骤：")
    print()
    print("  1️⃣  安装 Python 依赖")
    print("     python run.py postinstall")
    print()
    print("  2️⃣  配置服务凭证（API Token 等）")
    print("     python run.py configure")
    print()
    print("  3️⃣  查看全部状态")
    print("     python run.py doctor")
    print()
    print("=" * 60)
    print()
    return False


def main():
    parser = argparse.ArgumentParser(description="paper-scholar health check")
    parser.add_argument("--quick", action="store_true",
                        help="Quick check (exit code: 0=ready, 1=needs setup)")
    args = parser.parse_args()

    if args.quick:
        ok = cmd_quick()
        sys.exit(0 if ok else 1)
    else:
        cmd_doctor()


if __name__ == "__main__":
    main()
