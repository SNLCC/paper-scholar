#!/usr/bin/env python3
"""run.py — ..."""

# Handle terminal encoding gracefully
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass

"""
run.py — Unified entry point for all paper-scholar commands.

Usage:
    python run.py extract <pdf_path> [--output <path>]      # Extract text from PDF
    python run.py fetch <mode> <subcommand> [args...]       # Zotero/Nutstore access
    python run.py score template [--output <path>]          # Scoring template
    python run.py score <metadata.json> [--output <path>]   # Score a paper
    python run.py coverage report <analysis.json>           # Coverage report
    python run.py coverage verify <analysis.json> <txt>     # Verify coverage
    python run.py compare <analysis.json> <annotations.json> # Compare with annotations
    python run.py learn aggregate                          # Aggregate learning records
    python run.py learn profile                            # Build user profile
    python run.py data store <analysis.json>               # Store analysis data
    python run.py data list                                # List stored papers
    python run.py data show <paper_id>                     # Show stored paper
    python run.py model add <analysis.json>                # Add to model library
    python run.py model list                               # List models
    python run.py model show <model_id>                    # Show model details
    python run.py model match <analysis.json>              # Match models
    python run.py model prune <model_id> [--min-frequency] # Prune model
    python run.py model snapshot <model_id>                # Snapshot model
    python run.py model rollback <model_id> <snap>         # Rollback model
    python run.py model detect-conflict <json> <mid>       # Conflict detection
    python run.py model report <model_id> [--output <md>]  # Human-readable report
    python run.py model export <mid> <path>                # Export model
    python run.py model import <path>                      # Import model
    python run.py model self-assess                        # Self-assessment
    python run.py model evolution-status                   # Evolution state
    python run.py prescribe list                           # List prescriptions
    python run.py prescribe add <prescription.json>        # Add prescription
    python run.py prescribe recommend <chapter_type>       # Get recommendations
    python run.py prescribe upgrade <prescription_id>      # Upgrade confidence
    python run.py welcome                                    # Show getting-started guide
    python run.py reproduce recall <paper_id>               # Recall paper skeleton
    python run.py reproduce list                            # List stored papers
    python run.py reproduce search <keyword>                # Search papers
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

from scripts._paths import data_root

_GLOBAL_DATA_DIR: str | None = None


WELCOME_TEXT = """
+==========================================================+
|              paper-scholar -- 论文精读与写作              |
+==========================================================+

paper-scholar 是一个学术论文精读与写作辅助工具。它可以：

[1] 精读论文
  对人文社科论文进行章->段->句三层逐级精读，识别结构模式
  与论证规律，构建具有置信度支撑的写作模型。

[2] 指导写作
  基于模型库中的同类论文规律，提供章节规划、论证策略、
  句式模板和选题建议。

[3] 接入你的研究生态
  . Zotero -- 读取论文库和批注
  . 坚果云 WebDAV -- 获取 PDF 原文
  . 学习你的批注风格 -- 越用越懂你

------ 快速上手 ------

第一步：安装
  python install.py   # 自动下载 + 装依赖 + 注册到 Codex

第二步：精读一篇论文
  python run.py extract paper.pdf --output paper.txt
  # 将 paper.txt 交给 Codex，它会按 8 条研读规范逐层分析

第三步：存储分析结果
  python run.py data store analysis.json
  python run.py model add analysis.json

第四步：需要写作指导时
  python run.py prescribe recommend introduction

--- 数据目录 ---
积累数据存储在项目目录的 .paper-scholar/ 下
  自定义：export PAPER_SCHOLAR_DATA_DIR=/path/to/data

--- 更新 ---
  python install.py   # 自动检测新版本，保留用户数据

查看所有命令：
  python run.py --help

------ 三条路径 ------

路径1：「帮我精读这篇论文」
  -> 提供 PDF -> 评分 -> 8规范精读 -> 建模 -> 入库

路径2：「我想写一篇关于X的论文」
  -> 查询模型库 -> 推荐结构 -> 生成写作指导

路径3：「看看我的Zotero里有什么」
  -> python run.py fetch local collections
  -> python run.py fetch local items
  -> 选择论文 -> 进入路径1
"""


def cmd_welcome():
    print(textwrap.dedent(WELCOME_TEXT).strip())


SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"


def _run(script: str, args: list[str]):
    """Run a script with the given arguments."""
    import subprocess
    script_path = SCRIPTS_DIR / script
    cmd = [sys.executable, str(script_path)] + args
    env = os.environ.copy()
    if _GLOBAL_DATA_DIR:
        env["PAPER_SCHOLAR_DATA_DIR"] = _GLOBAL_DATA_DIR
    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)


def cmd_install():
    """Install to Codex skills directory (auto-detects install vs update)."""
    import subprocess
    install_script = Path(__file__).resolve().parent / "install.py"
    env = os.environ.copy()
    if _GLOBAL_DATA_DIR:
        env["PAPER_SCHOLAR_DATA_DIR"] = _GLOBAL_DATA_DIR
    result = subprocess.run([sys.executable, str(install_script)], env=env)
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="paper-scholar — paper reading and writing assistant"
    )
    parser.add_argument("--data-dir", help=f"Data root (default: {data_root()})")
    sub = parser.add_subparsers(dest="command")

    # --- extract ---
    p_extract = sub.add_parser("extract", help="Extract text from PDF")
    p_extract.add_argument("pdf", help="PDF file path")
    p_extract.add_argument("--output", "-o", help="Output text file")
    p_extract.add_argument("--stdout", action="store_true", help="Print to stdout")
    p_extract.add_argument("--engine", choices=["auto", "pdfplumber", "builtin"], default="auto")

    # --- fetch ---
    p_fetch = sub.add_parser("fetch", help="Zotero/Nutstore access")
    p_fetch.add_argument("mode", choices=["local", "web", "webdav"], help="Access mode")
    p_fetch.add_argument("args", nargs=argparse.REMAINDER, help="Subcommand arguments")

    # --- score ---
    p_score = sub.add_parser("score", help="Paper quality scoring")
    p_score.add_argument("target", help="Metadata JSON or 'template'")
    p_score.add_argument("--output", "-o", help="Output path")

    # --- coverage ---
    p_cov = sub.add_parser("coverage", help="Coverage checking")
    p_cov_sub = p_cov.add_subparsers(dest="coverage_command")
    p_cov_report = p_cov_sub.add_parser("report", help="Coverage report")
    p_cov_report.add_argument("analysis_json")
    p_cov_verify = p_cov_sub.add_parser("verify", help="Verify against original")
    p_cov_verify.add_argument("analysis_json")
    p_cov_verify.add_argument("original_text")

    # --- compare ---
    p_comp = sub.add_parser("compare", help="Compare with user annotations")
    p_comp.add_argument("analysis_json")
    p_comp.add_argument("annotations_json")

    # --- learn ---
    p_learn = sub.add_parser("learn", help="Learning records")
    p_learn_sub = p_learn.add_subparsers(dest="learn_command")
    p_learn_sub.add_parser("aggregate", help="Aggregate learning records")
    p_learn_sub.add_parser("profile", help="Build user profile")

    # --- data ---
    p_data = sub.add_parser("data", help="Data storage")
    p_data_sub = p_data.add_subparsers(dest="data_command")
    p_ds = p_data_sub.add_parser("store", help="Store analysis")
    p_ds.add_argument("analysis_json")
    p_data_sub.add_parser("list", help="List stored papers")
    p_sh = p_data_sub.add_parser("show", help="Show stored paper")
    p_sh.add_argument("paper_id")

    # --- model ---
    p_model = sub.add_parser("model", help="Model management")
    p_model.add_argument("action", choices=[
        "add", "list", "show", "match", "prune", "snapshot",
        "rollback", "detect-conflict", "report", "export", "import",
        "self-assess", "evolution-status"
    ], help="Model action")
    p_model.add_argument("args", nargs=argparse.REMAINDER, help="Action arguments")

    # --- prescribe ---
    p_pres = sub.add_parser("prescribe", help="Writing prescriptions")
    p_pres_sub = p_pres.add_subparsers(dest="prescribe_command")
    p_pres_sub.add_parser("list", help="List prescriptions")
    p_pa = p_pres_sub.add_parser("add", help="Add prescription")
    p_pa.add_argument("prescription_json")
    p_pr = p_pres_sub.add_parser("recommend", help="Get recommendations")
    p_pr.add_argument("chapter_type")
    p_pu = p_pres_sub.add_parser("upgrade", help="Upgrade confidence")
    p_pu.add_argument("prescription_id")

    # --- reproduce ---
    p_repro = sub.add_parser("reproduce", help="Recall paper skeleton from memory")
    p_repro_sub = p_repro.add_subparsers(dest="reproduce_command")
    p_rr = p_repro_sub.add_parser("recall", help="Recall a paper")
    p_rr.add_argument("paper_id")
    p_repro_sub.add_parser("list", help="List stored papers")
    p_rs = p_repro_sub.add_parser("search", help="Search papers")
    p_rs.add_argument("keyword")

    # --- welcome ---
    sub.add_parser("welcome", help="Show getting-started guide")

    # --- install ---
    sub.add_parser("install", help="Install skill to Codex skills directory")

    # --- update ---
    p_update = sub.add_parser("update", help="Update skill (preserves user data)")
    p_update.add_argument("--force", action="store_true", help="Force update even if same version")

    args = parser.parse_args()
    global _GLOBAL_DATA_DIR
    _GLOBAL_DATA_DIR = args.data_dir

    cmd = args.command

    if cmd == "extract":
        script_args = [args.pdf]
        if args.output:
            script_args += ["--output", args.output]
        if args.stdout:
            script_args += ["--stdout"]
        if args.engine != "auto":
            script_args += ["--engine", args.engine]
        _run("extract_pdf_text.py", script_args)

    elif cmd == "fetch":
        _run("fetch_zotero.py", [args.mode] + args.args)

    elif cmd == "score":
        script_args = ["score" if args.target != "template" else "template", args.target]
        if args.output:
            script_args += ["--output", args.output]
        _run("analyze_paper.py", script_args)

    elif cmd == "coverage":
        if args.coverage_command == "report":
            _run("check_coverage.py", ["report", args.analysis_json])
        elif args.coverage_command == "verify":
            _run("check_coverage.py", ["verify", args.analysis_json, args.original_text])

    elif cmd == "compare":
        _run("compare_annotations.py", ["compare", args.analysis_json, args.annotations_json])

    elif cmd == "learn":
        if args.learn_command == "aggregate":
            _run("record_learnings.py", ["aggregate"])
        elif args.learn_command == "profile":
            _run("record_learnings.py", ["profile"])

    elif cmd == "data":
        if args.data_command == "store":
            _run("accumulate_data.py", ["store", args.analysis_json])
        elif args.data_command == "list":
            _run("accumulate_data.py", ["list"])
        elif args.data_command == "show":
            _run("accumulate_data.py", ["show", args.paper_id])

    elif cmd == "model":
        _run("update_model.py", [args.action] + args.args)

    elif cmd == "prescribe":
        if args.prescribe_command == "list":
            _run("update_prescription.py", ["list"])
        elif args.prescribe_command == "add":
            _run("update_prescription.py", ["add", args.prescription_json])
        elif args.prescribe_command == "recommend":
            _run("update_prescription.py", ["recommend", args.chapter_type])
        elif args.prescribe_command == "upgrade":
            _run("update_prescription.py", ["upgrade", args.prescription_id])

    elif cmd == "reproduce":
        if args.reproduce_command == "recall":
            _run("reproduce_paper.py", ["recall", args.paper_id])
        elif args.reproduce_command == "list":
            _run("reproduce_paper.py", ["list"])
        elif args.reproduce_command == "search":
            _run("reproduce_paper.py", ["search", args.keyword])

    elif cmd == "welcome":
        cmd_welcome()

    elif cmd == "install":
        cmd_install()

    elif cmd == "update":
        import subprocess
        install_script = Path(__file__).resolve().parent / "install.py"
        extra = ["--force"] if getattr(args, 'force', False) else []
        result = subprocess.run([sys.executable, str(install_script)] + extra)
        sys.exit(result.returncode)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
