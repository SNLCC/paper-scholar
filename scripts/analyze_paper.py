#!/usr/bin/env python3
"""
analyze_paper.py — Journal scoring, topic analysis, multi-dimension scoring.

This script provides the scoring framework for paper quality assessment.
It generates structured scoring output per references/quality-scoring.md.

Features:
  - CSSCI journal database with fuzzy matching
  - Journal rating (rate) — 100-point scale: journal (40) + author (30) + features (30)
  - Topic analysis (topic) — problem source classification + innovation type
  - Scoring template generation (template)

Usage:
    python analyze_paper.py score <paper_metadata.json> [--output <path>]
    python analyze_paper.py template                    # Print scoring template
    python analyze_paper.py rate <journal_name> [--author <name>] [--cited <n>]
    python analyze_paper.py topic --title "<title>" --abstract "<abstract>"
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from _paths import models_dir as _get_models_dir


SCORING_TEMPLATE = {
    "paper_title": "",
    "overall_score": 0,
    "decision": "浏览",
    "dimensions": {
        "journal_level": {"score": 0, "max": 40, "detail": "", "confidence": "unknown"},
        "author_authority": {"score": 0, "max": 25, "detail": "", "confidence": "unknown"},
        "paper_characteristics": {"score": 0, "max": 35, "detail": "", "confidence": "unknown"},
    },
    "reading_depth": {"recommended": "浏览", "reason": ""},
    "adjustment_log": [],
}


# ===================================================================
#  CSSCI journal database (loaded from references/journals.json)
# ===================================================================

_SCRIPT_DIR = Path(__file__).resolve().parent
_BUILTIN_JOURNALS = _SCRIPT_DIR.parent / "references" / "journals.json"


def _user_journals_path() -> Path:
    """Path to user's custom journal overrides."""
    from _paths import data_root
    return data_root() / "journals.json"


def _load_journal_db() -> dict[str, dict]:
    """Load journal database: built-in + user overrides (user wins)."""
    merged = {}

    # Load built-in
    if _BUILTIN_JOURNALS.exists():
        try:
            raw = json.loads(_BUILTIN_JOURNALS.read_text(encoding="utf-8"))
            for level, journals in raw.items():
                for name, info in journals.items():
                    merged[name] = {"level": level, "score": info["score"], "field": info.get("field", "unknown")}
        except Exception as e:
            print(f"Warning: failed to load {_BUILTIN_JOURNALS}: {e}", file=sys.stderr)

    # Load user overrides (same format, overwrites built-in)
    uj = _user_journals_path()
    if uj.exists():
        try:
            raw = json.loads(uj.read_text(encoding="utf-8"))
            for level, journals in raw.items():
                for name, info in journals.items():
                    merged[name] = {"level": level, "score": info["score"], "field": info.get("field", "unknown")}
        except Exception as e:
            print(f"Warning: failed to load {uj}: {e}", file=sys.stderr)

    return merged


def query_journal_level(journal_name: str) -> dict:
    """Query journal level with fuzzy matching. Returns level info dict."""
    merged = _load_journal_db()
    name = journal_name.strip()

    # Exact match
    if name in merged:
        return {**merged[name], "source": "database"}

    # Fuzzy match via rapidfuzz (if available), otherwise simple substring
    try:
        from rapidfuzz import fuzz
        best_match = None
        best_score = 0
        for jname, info in merged.items():
            score = fuzz.partial_ratio(name.lower(), jname.lower())
            if score > best_score and score >= 85:
                best_score = score
                best_match = (jname, info)
        if best_match:
            jname, info = best_match
            return {**info, "source": f"fuzzy_match({best_score})"}
    except ImportError:
        for jname, info in merged.items():
            if jname in name or name in jname:
                return {**info, "source": "substring_match"}

    # Not found → try interactive query
    return _query_journal_interactive(name)


# ===================================================================
#  Interactive journal query + cache
# ===================================================================

LEVEL_MAP = {
    "1": {"level": "CSSCI核心", "score": 38},
    "2": {"level": "CSSCI扩展", "score": 28},
    "3": {"level": "北大核心",  "score": 20},
    "4": {"level": "普刊",      "score": 10},
}


def _journal_cache_path() -> Path:
    from _paths import data_root
    return data_root() / "journal_cache.json"


def _load_journal_cache() -> dict:
    p = _journal_cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_journal_cache(cache: dict):
    p = _journal_cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _query_journal_interactive(name: str) -> dict:
    """Ask the user to classify an unknown journal, cache the result."""
    cache = _load_journal_cache()
    if name in cache:
        return {**cache[name], "source": "cache"}

    print(f"\n⚠️  期刊「{name}」不在数据库中，请告知其级别：", file=sys.stderr)
    print("   1) CSSCI 核心期刊", file=sys.stderr)
    print("   2) CSSCI 扩展版", file=sys.stderr)
    print("   3) 北大核心", file=sys.stderr)
    print("   4) 普刊 / 不确定", file=sys.stderr)
    try:
        choice = input("   请输入编号 (1-4): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "4"

    entry = LEVEL_MAP.get(choice, LEVEL_MAP["4"])
    result = {**entry, "field": "unknown", "source": "user_input"}

    cache[name] = result
    _save_journal_cache(cache)
    print(f"   已缓存「{name}」→ {result['level']}", file=sys.stderr)

    return result


# ===================================================================
#  Commands
# ===================================================================

def generate_scoring_template(output_path: str | None = None):
    """Print or save an empty scoring template."""
    text = json.dumps(SCORING_TEMPLATE, indent=2, ensure_ascii=False)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        print(f"Template saved to: {output_path}")
    else:
        print(text)


def rate_paper(journal_name: str, author_name: str = "",
               cited_count: int = 0, has_methodology: bool = False):
    """Rate a paper on 100-point scale: journal (40) + author (30) + features (30)."""
    j_info = query_journal_level(journal_name)
    journal_score = j_info["score"]

    # Author authority (simplified)
    author_score = 0
    if author_name:
        author_score = min(30, len(author_name) * 3)
    if cited_count > 100:
        author_score = min(30, author_score + 15)
    elif cited_count > 50:
        author_score = min(30, author_score + 10)

    # Paper features
    feature_score = 0
    if cited_count > 20:
        feature_score += 15
    if has_methodology:
        feature_score += 15

    total = journal_score + author_score + feature_score

    # Reading level
    if total >= 75:
        level = "精读"
    elif total >= 45:
        level = "泛读"
    else:
        level = "浏览"

    result = {
        "total_score": total,
        "journal_score": journal_score,
        "author_score": author_score,
        "feature_score": feature_score,
        "reading_level": level,
        "journal_info": j_info,
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def analyze_topic(title: str = "", abstract: str = "",
                   research_question: str = "", contribution: str = ""):
    """Analyze the topic of a paper: problem source + innovation type."""
    title_lower = title.lower()
    abstract_lower = abstract.lower()

    # Problem source
    if any(kw in abstract_lower for kw in ["争论", "分歧", "冲突", "对立"]):
        source = "学术争论"
    elif any(kw in abstract_lower for kw in ["不足", "空白", "缺乏", "尚未"]):
        source = "理论缺口"
    elif any(kw in abstract_lower for kw in ["现实", "实践", "问题", "困境"]):
        source = "现实问题"
    elif any(kw in abstract_lower for kw in ["重新", "再", "质疑", "反思"]):
        source = "范式反思"
    else:
        source = "待判定"

    # Innovation type
    if "新" in title or "首次" in abstract or "原创" in abstract:
        innovation = "原创性"
    elif "重释" in title or "再释" in title or "重读" in title:
        innovation = "重新诠释"
    elif "比较" in title or "比较研究" in abstract:
        innovation = "比较研究"
    elif "中国" in title or "本土" in abstract:
        innovation = "本土化"
    else:
        innovation = "待判定"

    result = {
        "title": title,
        "abstract": abstract[:200],
        "problem_source": source,
        "innovation_type": innovation,
        "problem_awareness": "明确" if research_question else "待确认",
        "contribution_claimed": contribution[:100] if contribution else "待提取",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ===================================================================
#  Writing pattern analysis (analyze)
# ===================================================================

def analyze_writing_pattern(title: str = "", abstract: str = "",
                            intro: str = "", sections_text: str = "",
                            conclusion: str = ""):
    """Analyze writing patterns: type classification, structure, intro/conclusion patterns.

    Args:
        title: Paper title
        abstract: Paper abstract
        intro: Introduction paragraph(s)
        sections_text: Section titles and content (title:content format, one per line)
        conclusion: Conclusion paragraph(s)
    """
    t = (title + " " + abstract).lower()

    # --- Paper type classification ---
    if any(kw in t for kw in ["实证", "数据", "实验", "调查", "统计", "定量"]):
        paper_type = "实证研究"
    elif any(kw in t for kw in ["理论", "框架", "模型", "范式", "建构"]):
        paper_type = "理论建构"
    elif any(kw in t for kw in ["述评", "综述", "回顾", "评论", "评价"]):
        paper_type = "学术述评"
    elif any(kw in t for kw in ["比较", "对比", "跨"]):
        paper_type = "比较研究"
    else:
        paper_type = "待判定"

    # --- Structure analysis ---
    section_list = [s.strip() for s in sections_text.split("\n") if s.strip()]
    has_literature = any("文献" in s or "综述" in s or "literature" in s.lower() for s in section_list)
    has_methodology = any("方法" in s or "method" in s.lower() for s in section_list)
    has_discussion = any("讨论" in s or "discussion" in s.lower() or "分析" in s for s in section_list)
    has_conclusion_sec = any("结论" in s or "结语" in s or "conclusion" in s.lower() for s in section_list)

    standard_structure = has_literature and has_methodology and has_discussion and has_conclusion_sec

    # --- Introduction pattern ---
    intro_lower = intro.lower()
    if any(kw in intro_lower for kw in ["问题", "困境", "为何", "为什么"]):
        intro_pattern = "问题导向"
    elif any(kw in intro_lower for kw in ["意义", "重要", "价值", "贡献"]):
        intro_pattern = "意义导向"
    elif any(kw in intro_lower for kw in ["背景", "历史", "发展", "演变"]):
        intro_pattern = "背景导向"
    else:
        intro_pattern = "待判定"

    # --- Conclusion pattern ---
    conc_lower = conclusion.lower()
    conc_patterns = []
    if any(kw in conc_lower for kw in ["总结", "综上", "总之", "总体"]):
        conc_patterns.append("总结要点")
    if any(kw in conc_lower for kw in ["未来", "展望", "方向", "进一步"]):
        conc_patterns.append("指向未来")
    if any(kw in conc_lower for kw in ["实践", "应用", "启示", "建议"]):
        conc_patterns.append("实践意义")
    if not conc_patterns:
        conc_patterns.append("待判定")

    # --- Argumentation type ---
    if any(kw in t for kw in ["演绎", "推理", "如果", "那么"]):
        arg_type = "演绎"
    elif any(kw in t for kw in ["归纳", "总结", "概括", "案例"]):
        arg_type = "归纳"
    elif any(kw in t for kw in ["类比", "比喻", "类似"]):
        arg_type = "类比"
    else:
        arg_type = "混合（待判定）"

    result = {
        "paper_type": paper_type,
        "structure": {
            "section_count": len(section_list),
            "has_literature_review": has_literature,
            "has_methodology": has_methodology,
            "has_discussion": has_discussion,
            "has_conclusion": has_conclusion_sec,
            "standard_structure": standard_structure,
        },
        "intro_pattern": intro_pattern,
        "conclusion_pattern": conc_patterns,
        "argumentation_type": arg_type,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ===================================================================
#  Model-based multi-dimension scoring
# ===================================================================

def score_paper_by_model(analysis_path: str, model_dir: str | None = None):
    """Score a paper based on accumulated models: topic (25) + argumentation (35) + writing (40).

    Reads the analysis JSON, compares its structure against stored models,
    and generates dimension scores plus improvement suggestions.
    """
    mdir = Path(model_dir) if model_dir else _get_models_dir()
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))

    title = analysis.get("title", "Unknown")
    paper_type = analysis.get("paper_type", "") or ""
    sections = analysis.get("sections", [])
    section_funcs = [s.get("rhetorical_function", "") for s in sections if s.get("rhetorical_function")]

    result = {
        "title": title,
        "paper_type": paper_type,
        "dimensions": {},
        "total_score": 0,
        "reading_level": "浏览",
        "suggestions": [],
        "model_refs": [],
    }

    # Scan models for matching paper type
    relevant_models = []
    if mdir.exists():
        for f in sorted(mdir.glob("*.json")):
            if f.name == "index.json":
                continue
            try:
                model = json.loads(f.read_text(encoding="utf-8"))
                mt = model.get("type_family", "")
                if paper_type and (paper_type in mt or mt in paper_type):
                    relevant_models.append(model)
            except Exception:
                continue

    # --- Topic score (max 25) ---
    topic_score = 15
    topic_detail = []
    if paper_type:
        topic_score += 5
        topic_detail.append("论文类型明确 (+5)")
    if relevant_models:
        topic_score = min(25, topic_score + 3)
        topic_detail.append(f"有 {len(relevant_models)} 个相关模型可参考 (+3)")
    else:
        topic_detail.append("无直接匹配模型，选题创新性待确认")
    result["dimensions"]["topic"] = {"score": topic_score, "max": 25, "detail": "; ".join(topic_detail)}

    # --- Argumentation score (max 35) ---
    arg_score = 20
    arg_detail = []
    if len(section_funcs) >= 3:
        arg_score += 5
        arg_detail.append(f"{len(section_funcs)} 个章节功能已识别 (+5)")
    if any("论证" in s or "分析" in s for s in section_funcs):
        arg_score += 5
        arg_detail.append("含核心论证分析 (+5)")
    if analysis.get("argumentation_model"):
        arg_score = min(35, arg_score + 5)
        arg_detail.append("已有论证模型数据 (+5)")
    if not arg_detail:
        arg_detail.append("论证结构待补充分析")
    result["dimensions"]["argumentation"] = {"score": arg_score, "max": 35, "detail": "; ".join(arg_detail)}

    # --- Writing score (max 40) ---
    write_score = 20
    write_detail = []
    if analysis.get("writing_pattern_model"):
        write_score += 8
        write_detail.append("已有写作模式模型 (+8)")
    if any("引言" in s or "introduction" in s.lower() for s in section_funcs):
        write_score += 6
        write_detail.append("引言功能已标注 (+6)")
    if any("结论" in s or "结语" in s or "conclusion" in s.lower() for s in section_funcs):
        write_score += 6
        write_detail.append("结论功能已标注 (+6)")
    if not write_detail:
        write_detail.append("写作模式待详细分析")
    result["dimensions"]["writing"] = {"score": min(40, write_score), "max": 40, "detail": "; ".join(write_detail)}

    total = topic_score + arg_score + write_score
    result["total_score"] = total
    if total >= 75:
        result["reading_level"] = "精读"
    elif total >= 50:
        result["reading_level"] = "泛读"
    else:
        result["reading_level"] = "浏览"

    if total < 50:
        result["suggestions"].append("选题方向不够明确，建议补充问题来源和创新性分析")
    if arg_score < 25:
        result["suggestions"].append("论证结构不够完整，建议补充论证模型分析")
    if write_score < 30:
        result["suggestions"].append("写作模式分析不足，建议补充引言/结论功能标注")

    for m in relevant_models[:3]:
        result["model_refs"].append({
            "label": m.get("label", ""),
            "papers": m.get("papers_count", 0),
            "confidence": m.get("confidence", ""),
        })

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ===================================================================
#  CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Paper quality analysis and scoring")
    sub = parser.add_subparsers(dest="command")

    # --- score ---
    p_score = sub.add_parser("score", help="Score a paper from metadata JSON")
    p_score.add_argument("metadata", help="Paper metadata JSON file path")
    p_score.add_argument("--output", "-o", help="Output scoring JSON path")

    # --- template ---
    p_temp = sub.add_parser("template", help="Generate an empty scoring template")
    p_temp.add_argument("--output", "-o", help="Output path")

    # --- rate ---
    p_rate = sub.add_parser("rate", help="Rate paper by journal/author/citations")
    p_rate.add_argument("journal_name", help="Journal name")
    p_rate.add_argument("--author", default="", help="Author name")
    p_rate.add_argument("--cited", type=int, default=0, help="Citation count")
    p_rate.add_argument("--has-methodology", action="store_true", help="Has methodology section")

    # --- topic ---
    p_topic = sub.add_parser("topic", help="Analyze paper topic")
    p_topic.add_argument("--title", required=True, help="Paper title")
    p_topic.add_argument("--abstract", default="", help="Paper abstract")
    p_topic.add_argument("--research-question", default="", help="Research question")
    p_topic.add_argument("--contribution", default="", help="Claimed contribution")

    # --- analyze (writing pattern depth analysis) ---
    p_analyze = sub.add_parser("analyze", help="Analyze writing patterns")
    p_analyze.add_argument("--title", required=True, help="Paper title")
    p_analyze.add_argument("--abstract", default="", help="Paper abstract")
    p_analyze.add_argument("--intro", default="", help="Introduction text")
    p_analyze.add_argument("--sections", default="", help="Section titles (one per line)")
    p_analyze.add_argument("--conclusion", default="", help="Conclusion text")

    # --- model-score (based on accumulated models) ---
    p_mscore = sub.add_parser("model-score", help="Score paper against accumulated models")
    p_mscore.add_argument("analysis_json", help="Analysis JSON path")
    p_mscore.add_argument("--model-dir", help="Custom model directory")

    args = parser.parse_args()

    if args.command == "template":
        generate_scoring_template(args.output)
    elif args.command == "score":
        path = Path(args.metadata)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(path.read_text(encoding="utf-8"))
        if args.output:
            Path(args.output).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Scoring data saved to: {args.output}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.command == "rate":
        rate_paper(args.journal_name, args.author, args.cited, args.has_methodology)
    elif args.command == "topic":
        analyze_topic(args.title, args.abstract, args.research_question, args.contribution)
    elif args.command == "analyze":
        analyze_writing_pattern(args.title, args.abstract, args.intro,
                                args.sections, args.conclusion)
    elif args.command == "model-score":
        score_paper_by_model(args.analysis_json, args.model_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
