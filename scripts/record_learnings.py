#!/usr/bin/env python3
"""
record_learnings.py — Learning record aggregation with 21-tag annotation library.

Uses the annotation tag system from references/annotation-tags.md instead of
keyword matching, consistent with the skill's "semantic understanding first" principle.

Usage:
    python record_learnings.py aggregate [--learnings-dir <dir>]
    python record_learnings.py profile [--learnings-dir <dir>]
    python record_learnings.py add --paper <id> --page <n> --sentence <text>
                                  --my-analysis <text> --annotation <text>
                                  --decision <keep-mine|adopt-annotation|record-diff>
                                  --reason <text>
    python record_learnings.py list
    python record_learnings.py generate-rules
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from _paths import learnings_dir as _learnings_dir

DEFAULT_LEARNINGS_DIR = _learnings_dir()

ANNOTATION_TAGS = [
    "历史背景", "过渡", "转折点", "转折影响概括", "总体概括",
    "学科定位", "本文任务", "本段论点", "理论基础", "主要观点",
    "影响与评议", "概述", "评述", "综合判断", "合理性解释",
    "具体展开", "方法论视角提炼", "承上启下", "总结评述",
    "概括与评述", "进一步分析"
]


def _ldir(learnings_dir: str | None) -> Path:
    d = Path(learnings_dir) if learnings_dir else DEFAULT_LEARNINGS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _deviations_file(ldir: Path) -> Path:
    return ldir / "deviations.json"


def _infer_tag(text: str) -> str | None:
    t = text.strip().lower()
    if not t:
        return None
    patterns = [
        ("历史背景",   ["梳理", "发展", "历史", "脉络", "演变", "由来"]),
        ("过渡",       ["接下来", "转向", "过渡", "与此", "同时"]),
        ("转折点",     ["转折", "转向", "变化", "改变", "拐点"]),
        ("学科定位",   ["学科", "领域", "属于", "定位", "归属"]),
        ("本文任务",   ["本文", "任务", "目的", "旨在", "要做"]),
        ("本段论点",   ["本段", "论点", "主张", "认为", "核心"]),
        ("理论基础",   ["理论", "框架", "范式", "基础", "前提"]),
        ("主要观点",   ["观点", "主张", "立场", "核心", "关键"]),
        ("评述",       ["评价", "不足", "优势", "局限", "问题"]),
        ("合理性解释", ["合理", "解释", "原因", "因为", "由于"]),
        ("方法论视角提炼", ["方法", "方法论", "视角", "路径"]),
        ("承上启下",   ["承上", "启下", "连接", "呼应", "衔接"]),
        ("综合判断",   ["综合", "总体", "整体", "判断", "结论"]),
        ("进一步分析", ["进一步", "深入", "未来", "尚需", "待"]),
    ]
    scores = [(sum(1 for kw in keywords if kw in t), tag) for tag, keywords in patterns]
    scores = [(s, tag) for s, tag in scores if s > 0]
    if scores:
        scores.sort(reverse=True)
        return scores[0][1]
    return None


# ===================================================================
#  Deviation case tracking
# ===================================================================

def add_deviation(paper: str, page: str, sentence: str,
                  my_analysis: str, annotation: str,
                  decision: str, reason: str,
                  learnings_dir: str | None = None):
    """Record a deviation case between AI analysis and user annotation."""
    ldir = _ldir(learnings_dir)
    df = _deviations_file(ldir)

    deviations = []
    if df.exists():
        try:
            deviations = json.loads(df.read_text(encoding="utf-8"))
        except Exception:
            pass

    entry = {
        "paper": paper,
        "page": page,
        "sentence": sentence[:200] if len(sentence) > 200 else sentence,
        "my_analysis": my_analysis,
        "annotation": annotation if annotation else "(纯划线，无注释)",
        "decision": decision,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
    deviations.append(entry)

    df.write_text(json.dumps(deviations, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 偏差案例已记录：{paper} 第{page}页")
    print(f"   决策：{decision}")
    print(f"   原因：{reason}")


def list_deviations(learnings_dir: str | None = None):
    """List all deviation cases with summary statistics."""
    ldir = _ldir(learnings_dir)
    df = _deviations_file(ldir)

    if not df.exists():
        print("暂无偏差案例记录")
        return

    deviations = json.loads(df.read_text(encoding="utf-8"))
    total = len(deviations)
    if total == 0:
        print("暂无偏差案例记录")
        return

    keep_mine = sum(1 for d in deviations if d["decision"] == "keep-mine")
    adopt = sum(1 for d in deviations if d["decision"] == "adopt-annotation")
    record_diff = sum(1 for d in deviations if d["decision"] == "record-diff")

    print(f"\n{'='*50}")
    print(f"  偏差案例统计")
    print(f"{'='*50}")
    print(f"  总案例数：{total}")
    print(f"  保持小研：{keep_mine} ({keep_mine*100//total}%)")
    print(f"  采用批注：{adopt} ({adopt*100//total}%)")
    print(f"  记录差异：{record_diff} ({record_diff*100//total}%)")
    print(f"{'='*50}\n")

    print("最近的偏差案例：")
    for i, d in enumerate(deviations[-5:], 1):
        sent = d.get("sentence", "")[:60]
        print(f"  {i}. [{d['decision']}] {d['paper']} p{d['page']}: {sent}...")


def generate_rules(learnings_dir: str | None = None):
    """Analyze deviation patterns and generate rule improvement suggestions."""
    ldir = _ldir(learnings_dir)
    df = _deviations_file(ldir)

    if not df.exists():
        print("暂无偏差案例，无法生成规则")
        return

    deviations = json.loads(df.read_text(encoding="utf-8"))
    total = len(deviations)
    if total == 0:
        print("暂无偏差案例，无法生成规则")
        return

    keep_mine = sum(1 for d in deviations if d["decision"] == "keep-mine")
    adopt = sum(1 for d in deviations if d["decision"] == "adopt-annotation")
    record_diff = sum(1 for d in deviations if d["decision"] == "record-diff")

    print(f"\n{'='*50}")
    print(f"  规则优化建议")
    print(f"{'='*50}\n")
    print(f"偏差案例分析（共{total}条）：")
    print(f"  - 保持小研分析：{keep_mine}条 ({keep_mine*100//total}%)")
    print(f"  - 采用主人批注：{adopt}条 ({adopt*100//total}%)")
    print(f"  - 记录差异：{record_diff}条 ({record_diff*100//total}%)")

    if keep_mine / total > 0.7:
        print("""
  📊 小研分析质量较高：
     - 70%以上的情况小研分析更优
     - 继续保持语义理解优先原则
     - 批注仅作校准参考
""")
    if adopt / total > 0.3:
        print("""
  ⚠️ 主人批注价值较高：
     - 超过30%的情况主人批注更优
     - 注意学习主人独特的分析视角
     - 这些案例值得深入研究
""")
    print("""
  💡 持续优化建议：
     1. 继续积累更多偏差案例
     2. 分析 adopt-annotation 的具体原因
     3. 将有价值的规则更新到 SKILL.md
""")


# ===================================================================
#  Profile & aggregate
# ===================================================================

def profile(learnings_dir: str | None = None):
    """Build user annotation profile using 21-tag library (L1 -> L2)."""
    ldir = _ldir(learnings_dir)
    files = list(ldir.glob("*.json"))
    if not files:
        print("No learning data yet. Run 'compare' first.")
        return

    tag_counts = {}
    total = 0
    color_counts = {}
    section_counts = {}
    comment_count = 0

    for f in files:
        if f.name == "deviations.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for m in d.get("semantic_alignment", {}).get("matched_annotations", []):
            total += 1
            tag = _infer_tag(m.get("user_comment", "") or m.get("user_text", ""))
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            color = m.get("user_color", "")
            if color:
                color_counts[color] = color_counts.get(color, 0) + 1
            sec = m.get("matched_section", "")
            if sec:
                section_counts[sec] = section_counts.get(sec, 0) + 1
            if m.get("user_comment"):
                comment_count += 1

    if total == 0:
        print("No annotations found in learning data.")
        return

    print(f"User Annotation Profile (L2: type induction)")
    print(f"  Papers: {len(files)}, Annotations: {total}")
    print()

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    if sorted_tags:
        print("  Top tags:")
        for tag, count in sorted_tags[:8]:
            print(f"    {tag}: {count} ({count/total:.0%})")

    if color_counts:
        print("\n  Color patterns:")
        for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {color}: {count}")

    if section_counts:
        print("\n  Section focus:")
        for sec, count in sorted(section_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {sec}: {count} ({count/total:.0%})")

    cr = comment_count / total
    print(f"\n  Comment ratio: {cr:.0%}")
    density = "high" if cr > 0.5 else "medium" if cr > 0.2 else "low"
    print(f"  Density: {density}")

    profile_path = ldir / "profile.json"
    profile_data = {
        "updated": datetime.now().isoformat(),
        "papers_count": len(files),
        "total_annotations": total,
        "top_tags": dict(sorted_tags[:5]),
        "color_patterns": color_counts,
        "section_focus": section_counts,
        "comment_ratio": cr,
        "density": density,
    }
    profile_path.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Profile saved: {profile_path}")


def aggregate(learnings_dir: str | None = None):
    """Aggregate learning records (alias for profile)."""
    profile(learnings_dir)


def main():
    parser = argparse.ArgumentParser(description="Learning record aggregation with tag library")
    parser.add_argument("--learnings-dir", help=".learnings directory")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("aggregate")
    sub.add_parser("profile")

    p_add = sub.add_parser("add", help="Add a deviation case")
    p_add.add_argument("--paper", required=True, help="Paper ID")
    p_add.add_argument("--page", required=True, help="Page number")
    p_add.add_argument("--sentence", required=True, help="Sentence text")
    p_add.add_argument("--my-analysis", required=True, help="AI's analysis")
    p_add.add_argument("--annotation", default="", help="User annotation")
    p_add.add_argument("--decision", required=True,
                       choices=["keep-mine", "adopt-annotation", "record-diff"],
                       help="Calibration decision")
    p_add.add_argument("--reason", required=True, help="Reason for decision")

    sub.add_parser("list", help="List deviation cases")

    sub.add_parser("generate-rules", help="Generate rule improvement suggestions")

    args = parser.parse_args()

    if args.command == "aggregate":
        aggregate(args.learnings_dir)
    elif args.command == "profile":
        profile(args.learnings_dir)
    elif args.command == "add":
        add_deviation(args.paper, args.page, args.sentence,
                      args.my_analysis, args.annotation,
                      args.decision, args.reason, args.learnings_dir)
    elif args.command == "list":
        list_deviations(args.learnings_dir)
    elif args.command == "generate-rules":
        generate_rules(args.learnings_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
