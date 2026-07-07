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
    python run.py configure                                 # Interactive configuration wizard
    python run.py configure --show                           # Show configuration status
    python run.py configure --mineru-token <token>           # Set specific config value
    python run.py status                                     # Alias for 'configure --show'
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

--- 配置 ---
  python run.py configure              # 交互式配置向导
  python run.py status                 # 查看配置状态

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
    p_extract.add_argument("--engine", choices=["auto", "local", "pymupdf", "pymupdf-v62", "pdfplumber", "pdfplumber-v62", "builtin", "mineru"], default="auto")

    p_extract.add_argument("--show-info", action="store_true",
                        help="Show double-column detection report")
    p_extract.add_argument("--force-mineru", action="store_true",
                        help="Force MinerU OCR (requires MINERU_TOKEN for large files)")
    p_extract.add_argument("--mineru-token",
                        help="MinerU API token (overrides MINERU_TOKEN env var)")
    p_extract.add_argument("--save-mineru-token", action="store_true",
                        help="Save --mineru-token to config.json for future use")

    # --- fetch ---
    p_fetch = sub.add_parser("fetch", help="Zotero/Nutstore access")
    p_fetch.add_argument("mode", choices=["local", "web", "webdav"], help="Access mode")
    p_fetch.add_argument("args", nargs=argparse.REMAINDER, help="Subcommand arguments")

    # --- score ---
    p_score = sub.add_parser("score", help="Paper quality scoring")
    p_score.add_argument("target", help="Metadata JSON or 'template'")
    p_score.add_argument("--output", "-o", help="Output path")

    # --- rate ---
    p_rate = sub.add_parser("rate", help="Rate paper by journal/author/citations")
    p_rate.add_argument("journal_name", help="Journal name")
    p_rate.add_argument("--author", default="", help="Author name")
    p_rate.add_argument("--cited", type=int, default=0, help="Citation count")
    p_rate.add_argument("--has-methodology", action="store_true", help="Has methodology section")

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
        "self-assess", "evolution-status", "rebuild"
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

    # --- scoverage (mechanism C) ---
    p_scover = sub.add_parser("scoverage", help="Sentence-level coverage report")
    p_scover.add_argument("--input", "-i", required=True, help="Input text file")
    p_scover.add_argument("--output", "-o", help="Output report path")
    p_scover.add_argument("--show-clean-log", action="store_true", help="Show cleaning log")

    # --- progress (mechanism A) ---
    p_prog = sub.add_parser("progress", help="Progress tracking (mechanism A)")
    p_prog_sub = p_prog.add_subparsers(dest="progress_command")
    p_prog_init = p_prog_sub.add_parser("init", help="Initialize progress")
    p_prog_init.add_argument("--paper", required=True)
    p_prog_init.add_argument("--key", required=True)
    p_prog_init.add_argument("--type", required=True)
    p_prog_init.add_argument("--level", required=True, choices=["精读", "泛读", "浏览"])
    p_prog_init.add_argument("--mode", default="对话流")
    p_prog_report = p_prog_sub.add_parser("report", help="Update a step")
    p_prog_report.add_argument("--step", type=int, required=True)
    p_prog_report.add_argument("--status", required=True,
                               choices=["pending", "in_progress", "completed", "skipped", "blocked"])
    p_prog_report.add_argument("--detail", default="")
    p_prog_sub.add_parser("show", help="Show full progress")

    # --- decision (mechanism B) ---
    p_dec = sub.add_parser("decision", help="Decision checkpoint (mechanism B)")
    p_dec_sub = p_dec.add_subparsers(dest="decision_command")
    p_dec_check = p_dec_sub.add_parser("check", help="Run checkpoint check")
    p_dec_check.add_argument("--step", type=int, required=True)
    p_dec_check.add_argument("--context", default="")
    p_dec_ask = p_dec_sub.add_parser("ask", help="Ask a decision question")
    p_dec_ask.add_argument("--question", required=True)
    p_dec_ask.add_argument("--option-a", required=True)
    p_dec_ask.add_argument("--option-b", required=True)
    p_dec_ask.add_argument("--option-c", default="")

    # --- configure ---
    p_conf = sub.add_parser("configure", help="Configuration wizard & status")
    p_conf.add_argument("--show", action="store_true",
                        help="Show current configuration status")
    p_conf.add_argument("--mineru-token", nargs="?", const="", default=None,
                        help="Set MinerU API token")
    p_conf.add_argument("--zotero-api-key", nargs="?", const="", default=None,
                        help="Set Zotero Web API key")
    p_conf.add_argument("--zotero-user-id", nargs="?", const="", default=None,
                        help="Set Zotero user ID")
    p_conf.add_argument("--webdav-user", nargs="?", const="", default=None,
                        help="Set WebDAV username")
    p_conf.add_argument("--webdav-password", nargs="?", const="", default=None,
                        help="Set WebDAV password")
    p_conf.add_argument("--zotero-data-dir", nargs="?", const="", default=None,
                        help="Set Zotero data directory path")

    # --- status ---
    p_status = sub.add_parser("status", help="Show configuration status")

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
        if args.show_info:
            script_args += ["--show-info"]
        if args.force_mineru:
            script_args += ["--force-mineru"]
        if args.mineru_token:
            script_args += ["--mineru-token", args.mineru_token]
        if getattr(args, 'save_mineru_token', False):
            script_args += ["--save-mineru-token"]
        _run("extract_pdf_text.py", script_args)

    elif cmd == "fetch":
        _run("fetch_zotero.py", [args.mode] + args.args)

    elif cmd == "score":
        if args.target == "template":
            script_args = ["template"]
        else:
            script_args = ["score", args.target]
        if args.output:
            script_args += ["--output", args.output]
        _run("analyze_paper.py", script_args)

    elif cmd == "rate":
        script_args = ["rate", args.journal_name]
        if args.author:
            script_args += ["--author", args.author]
        if args.cited:
            script_args += ["--cited", str(args.cited)]
        if args.has_methodology:
            script_args += ["--has-methodology"]
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

    elif cmd == "scoverage":
        s_args = ["--input", args.input]
        if args.output:
            s_args += ["--output", args.output]
        if args.show_clean_log:
            s_args += ["--show-clean-log"]
        _run("sentence_coverage.py", s_args)

    elif cmd == "progress":
        if args.progress_command == "init":
            _run("progress_reporter.py", ["init",
                 "--paper", args.paper, "--key", args.key,
                 "--type", args.type, "--level", args.level,
                 "--mode", args.mode])
        elif args.progress_command == "report":
            _run("progress_reporter.py", ["report",
                 "--step", str(args.step),
                 "--status", args.status,
                 "--detail", args.detail])
        elif args.progress_command == "show":
            _run("progress_reporter.py", ["show"])

    elif cmd == "decision":
        if args.decision_command == "check":
            d_args = ["check", "--step", str(args.step)]
            if args.context:
                d_args += ["--context", args.context]
            _run("decision_checkpoint.py", d_args)
        elif args.decision_command == "ask":
            d_args = ["ask", "--question", args.question,
                     "--option-a", args.option_a,
                     "--option-b", args.option_b]
            if args.option_c:
                d_args += ["--option-c", args.option_c]
            _run("decision_checkpoint.py", d_args)

    elif cmd == "configure":
        conf_args = []
        if args.show:
            conf_args.append("--show")
        else:
            for flag in ["--mineru-token", "--zotero-api-key", "--zotero-user-id",
                          "--webdav-user", "--webdav-password", "--zotero-data-dir"]:
                val = getattr(args, flag.lstrip("--").replace("-", "_"), None)
                if val is not None:
                    conf_args.append(flag)
                    if val:
                        conf_args.append(val)
        _run("configure.py", conf_args)

    elif cmd == "status":
        _run("configure.py", ["--show"])

    elif cmd == "welcome":
        cmd_welcome()

    elif cmd == "install":
        cmd_install()

    elif cmd == "update":
        import subprocess
        install_script = Path(__file__).resolve().parent / "install.py"
        extra = ["--force"] if getattr(args, 'force', False) else []
        env = os.environ.copy()
        if _GLOBAL_DATA_DIR:
            env["PAPER_SCHOLAR_DATA_DIR"] = _GLOBAL_DATA_DIR
        result = subprocess.run([sys.executable, str(install_script)] + extra, env=env)
        sys.exit(result.returncode)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
