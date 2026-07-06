#!/usr/bin/env python3
"""
progress_reporter.py — 进度报告（机制 A）

每完成一步后自动输出进度报告，追踪论文精读全流程。

用法：
    python progress_reporter.py init --paper "<标题>" --key "<Zotero Key>" --type "<类型>" --level "<精读/泛读/浏览>"
    python progress_reporter.py report --step 4 --status completed --detail "覆盖率 100%"
    python progress_reporter.py show
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from _paths import data_root

STEPS = [
    "第1步：质量评分",
    "第2步：动态评级调整",
    "第3步：判断论文类型",
    "第4步：语义理解精细分析",
    "第4.5步：读取Zotero批注",
    "第4.6步：对比与校准",
    "第4.7步：学习记录与规则优化",
    "第5步：理解验证",
    "第6步：模型更新",
    "第7步：选题分析与论文评分",
    "第8步：复现触发",
]


def _progress_dir() -> Path:
    d = data_root() / ".progress"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_file() -> Path:
    return _progress_dir() / "current.json"


def init_state(paper, key, paper_type, level, mode="对话流"):
    """初始化进度状态"""
    state = {
        "paper": paper,
        "key": key,
        "type": paper_type,
        "level": level,
        "mode": mode,
        "started_at": datetime.now().isoformat(),
        "steps": [
            {"name": step, "status": "pending", "detail": "", "completed_at": None}
            for step in STEPS
        ],
    }
    _state_file().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 状态已初始化：{paper}（{key}）")
    print_state(state)


def update_step(step, status, detail=""):
    """更新单个步骤的状态"""
    sf = _state_file()
    if not sf.exists():
        print("⚠️  状态文件不存在，请先运行 init", file=sys.stderr)
        sys.exit(1)

    state = json.loads(sf.read_text(encoding="utf-8"))

    target_step = STEPS[step - 1] if 1 <= step <= len(STEPS) else None
    if not target_step:
        print(f"❌ 步骤号 {step} 超出范围 (1-{len(STEPS)})", file=sys.stderr)
        sys.exit(1)

    for s in state["steps"]:
        if s["name"] == target_step:
            s["status"] = status
            s["detail"] = detail
            if status == "completed":
                s["completed_at"] = datetime.now().isoformat()
            break

    sf.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {target_step} — {status}: {detail}")


def show_state():
    """显示当前完整进度"""
    sf = _state_file()
    if not sf.exists():
        print("⚠️  状态文件不存在，请先运行 init", file=sys.stderr)
        sys.exit(1)
    state = json.loads(sf.read_text(encoding="utf-8"))
    print_state(state)


def print_state(state):
    """打印进度报告（核心输出）"""
    print()
    print("📋 paper-scholar 进度报告")
    print("─" * 60)
    print(f"论文：{state['paper']}（Zotero Key: {state['key']}）")
    print(f"类型：{state['type']}")
    print(f"阅读级别：{state['level']}")
    print(f"阅读模式：{state['mode']}")
    print()
    print("步骤进度：")

    status_icon = {
        "pending": "[ ]",
        "in_progress": "[🔄]",
        "completed": "[✓]",
        "skipped": "[⏭]",
        "blocked": "[⚠]",
    }
    for s in state["steps"]:
        icon = status_icon.get(s["status"], "[?]")
        detail = f" — {s['detail']}" if s["detail"] else ""
        print(f"  {icon} {s['name']}{detail}")
    print("─" * 60)


def main():
    parser = argparse.ArgumentParser(description="paper-scholar 进度报告（机制 A）")
    subparsers = parser.add_subparsers(dest="action", required=True)

    init_parser = subparsers.add_parser("init", help="初始化状态")
    init_parser.add_argument("--paper", required=True, help="论文标题")
    init_parser.add_argument("--key", required=True, help="Zotero Key")
    init_parser.add_argument("--type", required=True, help="论文类型")
    init_parser.add_argument("--level", required=True, choices=["精读", "泛读", "浏览"])
    init_parser.add_argument("--mode", default="对话流", help="阅读模式（对话流/命令行）")

    report_parser = subparsers.add_parser("report", help="更新单个步骤")
    report_parser.add_argument("--step", type=int, required=True, help="步骤号 (1-11)")
    report_parser.add_argument("--status", required=True,
                               choices=["pending", "in_progress", "completed", "skipped", "blocked"])
    report_parser.add_argument("--detail", default="", help="步骤详情")

    subparsers.add_parser("show", help="显示完整进度")

    args = parser.parse_args()

    if args.action == "init":
        init_state(args.paper, args.key, args.type, args.level, args.mode)
    elif args.action == "report":
        update_step(args.step, args.status, args.detail)
    elif args.action == "show":
        show_state()


if __name__ == "__main__":
    main()
