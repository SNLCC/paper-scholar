#!/usr/bin/env python3
"""configure.py — Configuration wizard and status checker for paper-scholar.

Usage:
    python configure.py                          # Interactive wizard
    python configure.py --show                   # Show current status
    python configure.py --mineru-token <token>   # Set specific values
    python configure.py --zotero-api-key <key>
    python configure.py --zotero-user-id <id>
    python configure.py --webdav-user <email> --webdav-password <pwd>
    python configure.py --zotero-data-dir <path>
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
from pathlib import Path

from _paths import data_root


# ---------------------------------------------------------------------------
# Config path & helpers  (same location as extract_pdf_text.py)
# ---------------------------------------------------------------------------

def _config_path() -> Path:
    return data_root() / "config.json"


def load_config() -> dict:
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(config: dict):
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ 配置已保存: {p}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_icon(value: str | None) -> str:
    return "✅" if value else "❌"


def _mask_token(token: str | None) -> str:
    if not token:
        return "未配置"
    if len(token) <= 8:
        return token
    return token[:4] + "…" + token[-4:]


# ---------------------------------------------------------------------------
# Interactive wizard
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """
{sep}
 {title}
{sep}
{description}
当前: {current}

按 Enter 跳过此项，或输入新值:
> """


def _prompt(key: str, title: str, description: str, config: dict,
            secret: bool = False) -> str | None:
    current = config.get(key) or ""
    current_display = _mask_token(current) if secret else (current or "未配置")
    sep = "=" * 50
    prompt = _PROMPT_TEMPLATE.format(
        sep=sep, title=title, description=description, current=current_display
    )
    try:
        val = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[中断]")
        sys.exit(1)
    if val:
        return val
    # Keep existing value if user pressed Enter and it's already set
    return current if current else None


def cmd_configure_interactive():
    """Run the interactive configuration wizard."""
    config = load_config()

    print()
    print("=" * 60)
    print("  paper-scholar 配置向导")
    print("=" * 60)
    print()
    print("  按 Enter 跳过不需要配置的项，会保留已有值。")
    print()

    # 1. MinerU Token
    val = _prompt(
        "mineru_token",
        "1/6 · MinerU API Token",
        "  MinerU 是首选 PDF 解析引擎（支持扫描件/双栏/表格/公式）。\n"
        "  免 Token 可用轻量 API（≤10MB/≤20页，IP 限频）。\n"
        "  申请地址: https://mineru.net/",
        config, secret=True
    )
    config["mineru_token"] = val

    # 2. Zotero API Key
    val = _prompt(
        "zotero_api_key",
        "2/6 · Zotero Web API Key",
        "  用于在线访问 Zotero 文库（无需 Zotero 桌面端运行）。\n"
        "  申请地址: https://www.zotero.org/settings/keys",
        config, secret=True
    )
    config["zotero_api_key"] = val

    # 3. Zotero User ID
    val = _prompt(
        "zotero_user_id",
        "3/6 · Zotero 用户 ID",
        "  不填则首次使用时会自动解析（需要 API Key 有效）。\n"
        "  可在 https://www.zotero.org/settings/keys 查看。",
        config, secret=False
    )
    config["zotero_user_id"] = val

    # 4. WebDAV 账号
    print("=" * 50)
    print(" 4/6 · 坚果云 WebDAV 账号")
    print("=" * 50)
    print("  用于从坚果云下载 PDF 文件。")
    print("  建议使用应用密码（在坚果云「安全选项」中生成），而非登录密码。")
    print()
    current_user = config.get("webdav_user") or "未配置"
    print(f"  当前用户名: {current_user}")
    try:
        user_val = input("  输入 WebDAV 用户名/邮箱 (留空跳过): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[中断]")
        sys.exit(1)
    if user_val:
        config["webdav_user"] = user_val
    elif config.get("webdav_user"):
        pass  # keep existing

    try:
        pwd_val = input("  输入 WebDAV 密码/应用密码 (留空跳过): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[中断]")
        sys.exit(1)
    if pwd_val:
        config["webdav_password"] = pwd_val
    elif config.get("webdav_password"):
        pass  # keep existing

    # 5. Zotero 数据目录
    val = _prompt(
        "zotero_data_dir",
        "5/6 · Zotero 数据目录",
        "  本地 Zotero 数据目录路径，用于读取批注。\n"
        "  不填则自动检测（Windows: %APPDATA%\\Zotero\\...）。",
        config, secret=False
    )
    config["zotero_data_dir"] = val

    # 6. 自定义数据根目录提示
    print("=" * 50)
    print(" 6/6 · 数据根目录")
    print("=" * 50)
    print(f"  当前: {data_root()}")
    print("  如需自定义数据目录，请设置环境变量:")
    print("    export PAPER_SCHOLAR_DATA_DIR=/path/to/data")
    print("  或在每次命令后加 --data-dir /path/to/data")
    print()

    save_config(config)
    _print_summary(config)
    print()
    print("  💡 配置完成后，重新执行之前的命令即可生效。")
    print()


def _print_summary(config: dict):
    """Print a summary of what was configured."""
    print()
    print("  📋 配置摘要:")
    print(f"  MinerU Token:       {_status_icon(config.get('mineru_token'))} {_mask_token(config.get('mineru_token'))}")
    print(f"  Zotero API Key:     {_status_icon(config.get('zotero_api_key'))} {_mask_token(config.get('zotero_api_key'))}")
    print(f"  Zotero 用户 ID:     {_status_icon(config.get('zotero_user_id'))} {config.get('zotero_user_id') or '未配置'}")
    print(f"  WebDAV 用户名:      {_status_icon(config.get('webdav_user'))} {config.get('webdav_user') or '未配置'}")
    print(f"  WebDAV 密码:        {_status_icon(config.get('webdav_password'))} {'已配置' if config.get('webdav_password') else '未配置'}")
    print(f"  Zotero 数据目录:    {_status_icon(config.get('zotero_data_dir'))} {config.get('zotero_data_dir') or '未配置（自动检测）'}")


# ---------------------------------------------------------------------------
# Non-interactive set
# ---------------------------------------------------------------------------

def cmd_set(args):
    """Set config values from command-line arguments."""
    config = load_config()
    changed = []

    if args.mineru_token is not None:
        config["mineru_token"] = args.mineru_token if args.mineru_token else None
        changed.append("mineru_token")
    if args.zotero_api_key is not None:
        config["zotero_api_key"] = args.zotero_api_key if args.zotero_api_key else None
        changed.append("zotero_api_key")
    if args.zotero_user_id is not None:
        config["zotero_user_id"] = args.zotero_user_id if args.zotero_user_id else None
        changed.append("zotero_user_id")
    if args.webdav_user is not None:
        config["webdav_user"] = args.webdav_user if args.webdav_user else None
        changed.append("webdav_user")
    if args.webdav_password is not None:
        config["webdav_password"] = args.webdav_password if args.webdav_password else None
        changed.append("webdav_password")
    if args.zotero_data_dir is not None:
        config["zotero_data_dir"] = args.zotero_data_dir if args.zotero_data_dir else None
        changed.append("zotero_data_dir")
    if args.data_root is not None:
        # data_root is an env var, just print reminder
        print("  ⚠ 数据根目录通过环境变量 PAPER_SCHOLAR_DATA_DIR 设置，不保存在 config.json 中。", file=sys.stderr)
        print(f"  export PAPER_SCHOLAR_DATA_DIR={args.data_root}", file=sys.stderr)

    if changed:
        save_config(config)
        print(f"  已更新: {', '.join(changed)}", file=sys.stderr)
    else:
        print("  未指定任何配置项。使用 --help 查看可用选项。", file=sys.stderr)


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

def cmd_status():
    """Show current configuration status."""
    config = load_config()
    root = data_root()

    print()
    print("=" * 60)
    print("  paper-scholar 配置状态")
    print("=" * 60)
    print()

    # Data root
    root_ok = root.is_dir()
    print(f"  数据根目录:  {root}")
    print(f"  目录存在:     {'✅ 是' if root_ok else '⚠ 否（将自动创建）'}")
    print()

    # Check subdirectories
    for sub in ["data", "models", ".learnings", "prescriptions"]:
        d = root / sub
        exists = d.is_dir()
        print(f"  {sub + '/':<15} {'✅' if exists else '○'}")
    print()

    print(f"  {'配置项':<25} {'状态':<10} {'值'}")
    print(f"  {'-'*25} {'-'*10} {'-'*30}")

    items = [
        ("MinerU Token",       config.get("mineru_token"),       _mask_token),
        ("Zotero API Key",     config.get("zotero_api_key"),     _mask_token),
        ("Zotero 用户 ID",     config.get("zotero_user_id"),     str),
        ("WebDAV 用户名",      config.get("webdav_user"),        str),
        ("WebDAV 密码",        config.get("webdav_password"),    lambda x: "已配置" if x else "未配置"),
        ("Zotero 数据目录",    config.get("zotero_data_dir"),    str),
    ]

    for label, value, fmt in items:
        icon = _status_icon(value)
        display = fmt(value) if value else ""
        print(f"  {label:<25} {icon:<10} {display}")

    print()

    # Environment variable hints
    env_token = os.environ.get("MINERU_TOKEN")
    env_data = os.environ.get("PAPER_SCHOLAR_DATA_DIR")
    env_zotero = os.environ.get("ZOTERO_DATA_DIR")

    has_env_overrides = any([env_token, env_data, env_zotero])
    if has_env_overrides:
        print("  ⚠ 环境变量覆盖（优先级高于 config.json）:")
        if env_token:
            print(f"     MINERU_TOKEN = {_mask_token(env_token)}")
        if env_data:
            print(f"     PAPER_SCHOLAR_DATA_DIR = {env_data}")
        if env_zotero:
            print(f"     ZOTERO_DATA_DIR = {env_zotero}")
        print()

    # Suggestions
    missing = [label for label, value, _ in items if not value]
    if missing:
        print("  💡 建议下一步:")
        for label in missing:
            key_map = {
                "MinerU Token":    "--mineru-token",
                "Zotero API Key":  "--zotero-api-key",
                "Zotero 用户 ID":  "--zotero-user-id",
                "WebDAV 用户名":    "--webdav-user",
                "WebDAV 密码":     "--webdav-password",
                "Zotero 数据目录": "--zotero-data-dir",
            }
            flag = key_map.get(label, "")
            print(f"    配置 {label}: python run.py configure {flag} <值>")
        print()
        print(f"    或使用交互式向导: python run.py configure")
    else:
        print("  ✅ 所有配置项已就绪。")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="paper-scholar configuration management"
    )
    parser.add_argument("--show", action="store_true",
                        help="Show current configuration status")

    # Setter arguments
    parser.add_argument("--mineru-token", nargs="?", const="", default=None,
                        help="Set MinerU API token (no value = clear)")
    parser.add_argument("--zotero-api-key", nargs="?", const="", default=None,
                        help="Set Zotero Web API key")
    parser.add_argument("--zotero-user-id", nargs="?", const="", default=None,
                        help="Set Zotero user ID")
    parser.add_argument("--webdav-user", nargs="?", const="", default=None,
                        help="Set WebDAV username")
    parser.add_argument("--webdav-password", nargs="?", const="", default=None,
                        help="Set WebDAV password")
    parser.add_argument("--zotero-data-dir", nargs="?", const="", default=None,
                        help="Set Zotero data directory path")
    parser.add_argument("--data-root", nargs="?", const="", default=None,
                        help="Reminder to set PAPER_SCHOLAR_DATA_DIR env var")

    args = parser.parse_args()

    if args.show:
        cmd_status()
        return

    # If any setter argument is provided, run in non-interactive mode
    setter_args = [
        args.mineru_token, args.zotero_api_key, args.zotero_user_id,
        args.webdav_user, args.webdav_password, args.zotero_data_dir,
        args.data_root,
    ]
    if any(v is not None for v in setter_args):
        cmd_set(args)
        return

    # Default: interactive wizard
    cmd_configure_interactive()


if __name__ == "__main__":
    main()
