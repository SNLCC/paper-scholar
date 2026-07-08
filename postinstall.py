#!/usr/bin/env python3
"""postinstall.py — paper-scholar 依赖安装与首次使用标记

npx skills add 将 skill 文件复制到 .agents/skills/paper-scholar/ 后，
不会自动安装 Python 依赖。运行此脚本：

1. pip install -r requirements.txt
2. 写入 .paper-scholar/.setup_done 标记（表示首次配置已完成）

可通过 run.py 入口调用：python run.py postinstall
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass

import json
import subprocess
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent


def _data_root() -> Path:
    """Resolve data root (same logic as scripts/_paths.py)."""
    env = os.environ.get("PAPER_SCHOLAR_DATA_DIR")
    if env:
        root = Path(env)
    else:
        root = Path.cwd() / ".paper-scholar"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _write_setup_done(data_root: Path):
    """Write setup completion marker."""
    marker = data_root / ".setup_done"
    info = {
        "version": (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip() 
                   if (SKILL_DIR / "VERSION").exists() else "unknown",
        "pip_installed": True,
        "notes": "Run 'python run.py configure' to set API tokens"
    }
    marker.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ 首次配置标记已写入: {marker}")


def main():
    req = SKILL_DIR / "requirements.txt"
    if not req.exists():
        print("  requirements.txt not found — nothing to install.")
        return

    print(f"  Installing Python dependencies from {req.name} ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  ✅ Dependencies installed.")
    else:
        print("  ⚠ pip install had issues (dependencies may already be installed):")
        print(f"     {result.stderr.strip()[:200]}")

    # Write setup marker
    data_root = _data_root()
    _write_setup_done(data_root)

    print()
    print("  💡 下一步：运行配置向导设置 API Token")
    print("     python run.py configure")


if __name__ == "__main__":
    import os
    main()
