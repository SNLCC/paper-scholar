#!/usr/bin/env python3
"""
update_prescription.py — Writing guidance accumulation and confidence upgrade.

Manages the accumulated writing guidance (prescriptions) derived from
the model library. Each prescription is a piece of actionable advice
with its own confidence level.

Usage:
    python update_prescription.py list [--prescription-dir <dir>]
    python update_prescription.py add <prescription.json> [--prescription-dir <dir>]
    python update_prescription.py recommend <chapter_type> [--model-dir <dir>]
    python update_prescription.py upgrade <prescription_id> [--prescription-dir <dir>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from _paths import prescriptions_dir as _prescriptions_dir, models_dir as _models_dir

DEFAULT_PRESCRIPTION_DIR = _prescriptions_dir()
DEFAULT_MODEL_DIR = _models_dir()


def _pdir(prescription_dir: str | None) -> Path:
    d = Path(prescription_dir) if prescription_dir else DEFAULT_PRESCRIPTION_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_prescriptions(prescription_dir: str | None = None):
    """List all accumulated prescriptions."""
    d = _pdir(prescription_dir)
    files = sorted(d.glob("*.json"))
    if not files:
        print("No prescriptions yet.")
        return
    print(f"{'ID':<35} {'Chapter':<25} {'Conf':<8} {'Samples':<8} {'Advice'}")
    print("-" * 120)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            advice = data.get("advice", "")[:50]
            print(f"{f.stem:<35} {data.get('chapter_type',''):<25} "
                  f"{data.get('confidence',0):<8.3f} {data.get('sample_count',0):<8} {advice}")
        except Exception:
            print(f"{f.stem:<35} (invalid)")


def add_prescription(prescription_path: str, prescription_dir: str | None = None):
    """Add or update a writing prescription (with dedup)."""
    d = _pdir(prescription_dir)
    new = json.loads(Path(prescription_path).read_text(encoding="utf-8"))
    advice_text = new.get("advice", "").strip().lower()
    chapter_type = new.get("chapter_type", "")

    # Dedup: check if similar prescription exists
    for f in d.glob("*.json"):
        try:
            existing = json.loads(f.read_text(encoding="utf-8"))
            if (existing.get("advice", "").strip().lower() == advice_text
                    and existing.get("chapter_type", "") == chapter_type):
                # Merge: update confidence and sample count
                existing["sample_count"] = existing.get("sample_count", 1) + 1
                existing["confidence"] = min(1.0, existing.get("confidence", 0.5) + 0.05)
                existing["updated"] = datetime.now().isoformat()
                f.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"Updated existing prescription: {f.stem} (confidence+0.05)")
                return
        except Exception:
            continue

    # New prescription
    pid = f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    new["prescription_id"] = pid
    new.setdefault("sample_count", 1)
    new.setdefault("confidence", 0.3)
    new.setdefault("created", datetime.now().isoformat())
    new["updated"] = datetime.now().isoformat()

    dest = d / f"{pid}.json"
    dest.write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"New prescription → {dest}")


CHAPTER_ALIASES = {
    "introduction": "introduction",
    "引言": "introduction",
    "绪论": "introduction",
    "导论": "introduction",
    "前言": "introduction",
    "literature_review": "literature_review",
    "文献综述": "literature_review",
    "文献回顾": "literature_review",
    "methodology": "methodology",
    "方法": "methodology",
    "研究方法": "methodology",
    "analysis": "analysis",
    "findings": "analysis",
    "分析": "analysis",
    "研究发现": "analysis",
    "discussion": "discussion",
    "讨论": "discussion",
    "conclusion": "conclusion",
    "结论": "conclusion",
    "结语": "conclusion",
}

FALLBACK_STRATEGIES = {
    "introduction": {
        "purpose": "让读者认可该研究值得关注，并清晰理解论文要做什么",
        "common_moves": [
            {"step": "开场", "strategy": "用一个现象/问题/统计数据或引人深思的设问引入领域"},
            {"step": "背景", "strategy": "简要勾勒研究领域的关键脉络"},
            {"step": "聚焦", "strategy": "从广泛背景聚焦到具体研究问题"},
            {"step": "缺口", "strategy": "明确指出既有研究的不足或未解问题"},
            {"step": "回应", "strategy": "宣布本文的研究目的/假设/方法"},
            {"step": "预视", "strategy": "预告论文的组织结构"},
        ],
    },
    "literature_review": {
        "purpose": "展示作者对既有研究的全面把握，同时为本文的贡献建立舞台",
        "common_moves": [
            {"step": "主题式组织", "strategy": "按研究主题/流派组织，而非按时间顺序罗列"},
            {"step": "对话式叙述", "strategy": "让不同研究之间形成对话"},
            {"step": "批判性整合", "strategy": "对每个流派做出评价，指出其优势和局限"},
            {"step": "缺口凸显", "strategy": "在每个主要主题的结尾，指出还有哪些未尽之处"},
            {"step": "通向本文的桥梁", "strategy": "综述的结尾明确指向本文的研究空间"},
        ],
    },
    "methodology": {
        "purpose": "让读者相信本文的研究设计是严谨的、适合回答研究问题的",
        "common_moves": [
            {"step": "研究方法的选择", "strategy": "为什么选这个方法而非其他方法"},
            {"step": "数据来源", "strategy": "数据从哪里来，为何选择这个来源"},
            {"step": "分析策略", "strategy": "如何处理数据/文本，分析步骤是什么"},
            {"step": "研究局限", "strategy": "方法本身固有的局限（坦诚对待）"},
        ],
    },
    "analysis": {
        "purpose": "呈现作者的核心论证或研究发现",
        "common_moves": [
            {"step": "与理论框架呼应", "strategy": "框架中提出的概念如何在分析中被使用"},
            {"step": "证据分层呈现", "strategy": "核心发现优先，辅助发现其次"},
            {"step": "材料+分析并重", "strategy": "每个分析段落包含原始材料和解释"},
            {"step": "分析而非描述", "strategy": "重在论证材料说明了什么而非材料是什么"},
        ],
    },
    "discussion": {
        "purpose": "解释研究发现的意义，将其放回更广阔的学术语境",
        "common_moves": [
            {"step": "回扣引言", "strategy": "回到引言提出的问题，说明研究发现了什么"},
            {"step": "与既有研究对话", "strategy": "本文的发现与之前综述过的文献一致还是冲突"},
            {"step": "理论贡献", "strategy": "本文的研究如何推动了理论的发展"},
            {"step": "实践意义", "strategy": "研究发现对现实世界有何意义"},
            {"step": "局限与展望", "strategy": "坦诚面对不足，指出未来方向"},
        ],
    },
    "conclusion": {
        "purpose": "给读者留下清晰、持久的结构性印象",
        "common_moves": [
            {"step": "总结核心贡献", "strategy": "2-3点即可"},
            {"step": "强调研究的意义", "strategy": "理论+实践"},
            {"step": "前瞻性展望", "strategy": "3-5个未来方向"},
            {"step": "有力收尾", "strategy": "以一个有力的结束句收尾"},
        ],
    },
}


def recommend(chapter_type: str, model_dir: str | None = None):
    """Generate writing recommendations for a chapter type based on models.

    Supports all chapter types: introduction, literature_review, methodology,
    analysis, discussion, conclusion (and their Chinese aliases).
    Falls back to general writing strategies when model data is insufficient.
    """
    mdir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR

    # Resolve chapter type alias
    canonical = CHAPTER_ALIASES.get(chapter_type.lower(), chapter_type.lower())
    if canonical == chapter_type.lower() and canonical not in FALLBACK_STRATEGIES:
        print(f"Unknown chapter type: '{chapter_type}'")
        print(f"Supported types: {', '.join(sorted(CHAPTER_ALIASES.keys()))}")
        return

    print(f"Writing recommendations for '{chapter_type}' section:")
    print("=" * 60)

    found_model_data = False

    if mdir.exists():
        for f in sorted(mdir.glob("*.json")):
            if f.name in ("index.json",):
                continue
            try:
                model = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue

            wpm = model.get("writing_pattern_model", {})
            conf = wpm.get("confidence", 0)

            if canonical == "introduction":
                ifs = wpm.get("introduction_function_sequences", [])
                if ifs:
                    found_model_data = True
                    print(f"\nFrom model '{f.stem}' (conf={conf:.2f}):")
                    print(f"   Function sequences:")
                    for seq in ifs:
                        print(f"     - {seq}")

            elif canonical in ("methodology", "analysis", "discussion"):
                bop = wpm.get("body_organization_principles", [])
                if bop:
                    found_model_data = True
                    print(f"\nFrom model '{f.stem}' (conf={conf:.2f}):")
                    print(f"   Organization principles for {canonical}:")
                    for p in bop:
                        if canonical.lower() in p.lower() or canonical.lower() in p.lower():
                            print(f"     - {p}")

            elif canonical in ("literature_review", "conclusion"):
                am = model.get("argumentation_model", {})
                ast = am.get("argumentation_structures", [])
                if ast:
                    found_model_data = True
                    print(f"\nFrom model '{f.stem}' (conf={am.get('confidence', 0):.2f}):")
                    print(f"   Argumentation structures relevant to {canonical}:")
                    for s in ast:
                        print(f"     - {s}")

            for key, template in model.get("chapter_templates", {}).items():
                if canonical in key.lower() or chapter_type.lower() in key.lower():
                    found_model_data = True
                    purpose = template.get("purpose", "")
                    arc = template.get("internal_arc", "")
                    print(f"\nFrom model '{f.stem}':")
                    if purpose:
                        print(f"   Purpose: {purpose}")
                    if arc:
                        print(f"   Internal arc: {arc}")
                    for move in template.get("common_moves", []):
                        print(f"    - {move.get('step', '')}: {move.get('strategy', '')}")

    if not found_model_data:
        fallback = FALLBACK_STRATEGIES.get(canonical)
        if fallback:
            print(f"\nNo model data found for '{chapter_type}'.")
            print(f"   Using general writing strategies (from chapter-writing.md):")
            print()
            print(f"   Core task: {fallback.get('purpose', 'N/A')}")
            print(f"   Common moves:")
            for move in fallback.get("common_moves", []):
                print(f"     Step: {move.get('step', '')} -> {move.get('strategy', '')}")
            print()
            print(f"   Tip: Read 3-5 more papers of this type first for data-driven recommendations.")
        else:
            print(f"\nNo strategies available for '{chapter_type}'.")

def upgrade(prescription_id: str, prescription_dir: str | None = None):
    """Manually upgrade a prescription's confidence."""
    d = _pdir(prescription_dir)
    for f in d.glob(f"*{prescription_id}*"):
        data = json.loads(f.read_text(encoding="utf-8"))
        old_conf = data.get("confidence", 0.3)
        data["confidence"] = min(1.0, old_conf + 0.1)
        data["updated"] = datetime.now().isoformat()
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Upgraded '{f.stem}': confidence {old_conf:.2f} → {data['confidence']:.2f}")
        return
    print(f"Prescription not found: {prescription_id}")


def extract_from_analysis(analysis_json: str, prescription_dir: str | None = None):
    """Extract writing guidance elements from a stored analysis JSON.

    Parses the structured analysis to extract:
    - Introduction function sequences (from sections)
    - Writing pattern elements (from writing_pattern_model)
    - Concept usage tips (from concept_usage_model)
    - Chapter templates (from chapter_templates)

    Updates the corresponding prescription file for the paper type.
    """
    from _paths import data_dir as _get_data_dir

    d = _pdir(prescription_dir)
    analysis = json.loads(Path(analysis_json).read_text(encoding="utf-8"))

    paper_type = analysis.get("paper_type", "") or "综合"
    paper_id = analysis.get("paper_id", analysis_json)
    title = analysis.get("title", paper_id)

    # Extract elements from analysis structure
    elements = {
        "intro_sequence": [],
        "body_principles": [],
        "paragraph_patterns": [],
        "concept_tips": [],
        "chapter_templates": [],
    }

    # 1. Introduction function sequences from sections
    for sec in analysis.get("sections", []):
        func = sec.get("rhetorical_function", "").strip()
        if func:
            elements["intro_sequence"].append(func)

    # 2. Writing pattern model elements
    wpm = analysis.get("writing_pattern_model", {})
    if wpm:
        for seq in wpm.get("introduction_function_sequences", []):
            if seq not in elements["intro_sequence"]:
                elements["intro_sequence"].append(seq)
        for p in wpm.get("body_organization_principles", []):
            elements["body_principles"].append(p)
        for p in wpm.get("paragraph_cohesion_patterns", []):
            elements["paragraph_patterns"].append(p)

    # 3. Concept usage tips
    cum = analysis.get("concept_usage_model", {})
    if cum:
        for c in cum.get("topic_selection_criteria", []):
            elements["concept_tips"].append(c)
        for t in cum.get("title_expression_patterns", []):
            elements["concept_tips"].append(t)

    # 4. Chapter templates
    for ct_key, ct_val in analysis.get("chapter_templates", {}).items():
        if isinstance(ct_val, dict):
            elements["chapter_templates"].append(ct_val)

    # Build prescription entry
    pid = f"prescription_{paper_type}_{datetime.now().strftime('%Y%m%d')}"
    prescription = {
        "prescription_id": pid,
        "paper_type": paper_type,
        "source_title": title,
        "source_paper_id": paper_id,
        "sample_count": 1,
        "confidence": 0.3,
        "intro_function_sequences": elements["intro_sequence"][:10],
        "body_organization_principles": elements["body_principles"][:5],
        "paragraph_cohesion_patterns": elements["paragraph_patterns"][:5],
        "concept_usage_tips": elements["concept_tips"][:5],
        "chapter_templates": elements["chapter_templates"][:3],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }

    # Dedup: merge with existing prescription for same paper_type
    for f in d.glob(f"*{paper_type}*.json"):
        try:
            existing = json.loads(f.read_text(encoding="utf-8"))
            existing["sample_count"] = existing.get("sample_count", 1) + 1
            existing["confidence"] = min(1.0, existing.get("confidence", 0.3) + 0.05)
            # Merge new items
            for key in ["intro_function_sequences", "body_organization_principles",
                         "paragraph_cohesion_patterns", "concept_usage_tips"]:
                existing_items = existing.get(key, [])
                new_items = prescription.get(key, [])
                for item in new_items:
                    if item not in existing_items:
                        existing_items.append(item)
                existing[key] = existing_items[:10]
            existing["updated"] = datetime.now().isoformat()
            f.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Updated prescription: {f.stem} (samples={existing['sample_count']}, conf={existing['confidence']:.2f})")
            return
        except Exception:
            continue

    # New prescription
    dest = d / f"{pid}.json"
    dest.write_text(json.dumps(prescription, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"New prescription → {dest}")

    # Trigger model rebuild
    _trigger_model_rebuild(paper_type)


def _trigger_model_rebuild(paper_type: str):
    """Call model rebuild after prescription extraction."""
    import subprocess, sys
    script = Path(__file__).resolve().parent / "update_model.py"
    try:
        r = subprocess.run(
            [sys.executable, str(script), "rebuild",
             "--model-type", "writing_pattern",
             "--type", paper_type],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout.strip():
            print(f"[model rebuild] {r.stdout.strip()}")
    except Exception as e:
        print(f"[model rebuild warn] {e}")


def main():
    parser = argparse.ArgumentParser(description="Writing guidance management")
    parser.add_argument("--prescription-dir", help=f"Prescription directory (default: {DEFAULT_PRESCRIPTION_DIR})")
    parser.add_argument("--model-dir", help=f"Model directory (default: {DEFAULT_MODEL_DIR})")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list")
    p_add = sub.add_parser("add")
    p_add.add_argument("prescription_json")
    p_rec = sub.add_parser("recommend")
    p_rec.add_argument("chapter_type", help="e.g. introduction, methodology, conclusion")
    p_upg = sub.add_parser("upgrade")
    p_upg.add_argument("prescription_id")
    p_extract = sub.add_parser("extract", help="Extract guidance from analysis JSON")
    p_extract.add_argument("analysis_json", help="Path to stored analysis JSON")

    args = parser.parse_args()

    if args.command == "list":
        list_prescriptions(args.prescription_dir)
    elif args.command == "add":
        add_prescription(args.prescription_json, args.prescription_dir)
    elif args.command == "recommend":
        recommend(args.chapter_type, args.model_dir)
    elif args.command == "upgrade":
        upgrade(args.prescription_id, args.prescription_dir)
    elif args.command == "extract":
        extract_from_analysis(args.analysis_json, args.prescription_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
