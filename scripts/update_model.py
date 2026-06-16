#!/usr/bin/env python3
"""
update_model.py — Model update with confidence management and conflict detection.

Handles:
  - Adding analysis results to the model library (with dedup/merge)
  - Confidence computation
  - Conflict detection between new and existing patterns
  - Pruning, snapshot, rollback

Usage:
    python update_model.py add <analysis.json> [--model-dir <dir>]
    python update_model.py list [--model-dir <dir>]
    python update_model.py show <model_id> [--model-dir <dir>]
    python update_model.py match <analysis.json> [--model-dir <dir>]
    python update_model.py prune <model_id> [--min-frequency 0.3]
    python update_model.py snapshot <model_id>
    python update_model.py rollback <model_id> <snapshot_id>
    python update_model.py detect-conflict <analysis.json> <model_id>
    python update_model.py report <model_id> [--output <md>]   # Human-readable report
    python update_model.py export <model_id> <output_path>
    python update_model.py import <input_path>
"""

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


def _mdir(model_dir: str | None) -> Path:
    d = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(mdir: Path, mid: str) -> Path:
    return mdir / f"{mid}.json"


def _snap_dir(mdir: Path) -> Path:
    p = mdir / "snapshots"
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- Confidence ---

def compute_confidence(papers: list, consistency: float = 0.0) -> float:
    n = len(papers)
    if n == 0:
        return 0.0
    n_score = 1.0 - math.exp(-n / 5.0)
    c_score = max(0.0, min(1.0, consistency))
    return round(0.4 * n_score + 0.6 * c_score, 4)


# --- Dedup helpers ---

def _find_similar_section(sections: list, new_sec: dict) -> int | None:
    nf = new_sec.get("rhetorical_function", "").strip().lower()
    for i, s in enumerate(sections):
        ef = s.get("rhetorical_function", "").strip().lower()
        if nf and ef and (nf == ef or nf in ef or ef in nf):
            return i
    return None


def _find_similar_device(devices: list, new_dev: dict) -> int | None:
    nn = new_dev.get("device", "").strip().lower()
    for i, d in enumerate(devices):
        en = d.get("device", "").strip().lower()
        if nn and en and (nn == en or nn in en or en in nn):
            return i
    return None


def _merge_section(existing: dict, new_data: dict):
    moves_e = existing.get("rhetorical_moves", [])
    for nm in new_data.get("rhetorical_moves", []):
        found = False
        for em in moves_e:
            if em.get("move", "").strip().lower() == nm.get("move", "").strip().lower():
                em["frequency"] = round((em.get("frequency", 0.5) + nm.get("frequency", 0.5)) / 2, 2)
                found = True
                break
        if not found:
            moves_e.append(nm)
    for f in ["typical_length_ratio", "frequency"]:
        if f in new_data and f in existing:
            existing[f] = round((existing[f] + new_data[f]) / 2, 2)


def _structural_similarity(a: dict, b: dict) -> float:
    sa = [s.get("rhetorical_function", "") for s in a.get("sections", [])]
    sb = [s.get("rhetorical_function", "") for s in b.get("sections", [])]
    if not sa and not sb:
        return 0.5
    if not sa or not sb:
        return 0.2
    inter = set(sa) & set(sb)
    union = set(sa) | set(sb)
    return len(inter) / len(union) if union else 0.0


# --- Commands ---

def list_models(model_dir=None):
    mdir = _mdir(model_dir)
    for f in sorted(mdir.glob("*.json")):
        if f.name in ("index.json",):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            print(f"{f.stem:<30} {d.get('label',''):<40} papers={len(d.get('papers_analyzed',[]))} conf={d.get('confidence',0):.3f}")
        except Exception:
            pass


def add_analysis(analysis_path: str, model_dir=None):
    mdir = _mdir(model_dir)
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    paper_id = analysis.get("paper_id", "")

    sections = [s.get("rhetorical_function", "") for s in analysis.get("sections", [])]
    sig = " → ".join(sections) if sections else "unknown"

    # Match
    best_match = None
    best_score = 0.0
    for f in mdir.glob("*.json"):
        if f.name == "index.json":
            continue
        try:
            existing = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        score = _structural_similarity(existing, analysis)
        if score > best_score:
            best_score = score
            best_match = f

    if best_match and best_score >= 0.5:
        mid = best_match.stem
        model = json.loads(best_match.read_text(encoding="utf-8"))
        seen = {p.get("paper_id") for p in model.get("papers_analyzed", [])}
        if paper_id not in seen:
            model.setdefault("papers_analyzed", []).append({"paper_id": paper_id, "added": datetime.now().isoformat()})
        # Merge sections
        for ns in analysis.get("sections", []):
            idx = _find_similar_section(model.get("structural_patterns", {}).get("section_sequence", []), ns)
            if idx is not None:
                _merge_section(model["structural_patterns"]["section_sequence"][idx], ns)
            else:
                model.setdefault("structural_patterns", {}).setdefault("section_sequence", []).append(ns)
        # Merge devices
        for nd in analysis.get("rhetorical_devices", []):
            idx = _find_similar_device(model.get("rhetorical_devices", []), nd)
            if idx is not None:
                ef = model["rhetorical_devices"][idx].get("frequency", 0.5)
                model["rhetorical_devices"][idx]["frequency"] = round((ef + nd.get("frequency", 0.5)) / 2, 2)
            else:
                model.setdefault("rhetorical_devices", []).append(nd)
        model["updated"] = datetime.now().isoformat()
        model["papers_count"] = len(model["papers_analyzed"])
        model["confidence"] = compute_confidence(model["papers_analyzed"], best_score)
        best_match.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Merged into '{mid}' (sim={best_score:.2f}, n={model['papers_count']}, conf={model['confidence']:.3f})")
        return mid
    else:
        mid = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        model = {
            "model_id": mid, "label": sig[:80], "type_family": "auto", "type_signature": sig,
            "created": datetime.now().isoformat(), "updated": datetime.now().isoformat(),
            "papers_analyzed": [{"paper_id": paper_id, "added": datetime.now().isoformat()}],
            "papers_count": 1, "confidence": compute_confidence([paper_id], 1.0),
            "structural_patterns": analysis.get("structural_patterns", {}),
            "chapter_templates": analysis.get("chapter_templates", {}),
            "rhetorical_devices": analysis.get("rhetorical_devices", []),
            "argumentation_model": analysis.get("argumentation_model", {}),
            "writing_pattern_model": analysis.get("writing_pattern_model", {}),
            "concept_usage_model": analysis.get("concept_usage_model", {}),
        }
        p = _path(mdir, mid)
        p.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Created '{mid}' (sig: {sig})")
        return mid


def show_model(mid, model_dir=None):
    mdir = _mdir(model_dir)
    p = _path(mdir, mid)
    if not p.exists():
        print(f"Not found: {mid}", file=sys.stderr)
        return
    print(p.read_text(encoding="utf-8"))


def match_analysis(analysis_path, model_dir=None):
    mdir = _mdir(model_dir)
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    matches = []
    for f in mdir.glob("*.json"):
        if f.name == "index.json":
            continue
        try:
            existing = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        matches.append((_structural_similarity(existing, analysis), f.stem, existing))
    matches.sort(key=lambda x: -x[0])
    print(f"{'Score':<8} {'Model':<30} {'Papers':<8} {'Conf':<8}")
    print("-" * 60)
    for s, mid, d in matches[:10]:
        print(f"{s:<8.3f} {mid:<30} {d.get('papers_count',0):<8} {d.get('confidence',0):<8.3f}")


def prune_model(mid, min_freq=0.3, model_dir=None):
    mdir = _mdir(model_dir)
    p = _path(mdir, mid)
    if not p.exists():
        print(f"Not found: {mid}", file=sys.stderr)
        return
    model = json.loads(p.read_text(encoding="utf-8"))
    seq = model.get("structural_patterns", {}).get("section_sequence", [])
    orig = len(seq)
    seq[:] = [s for s in seq if s.get("frequency", 1.0) >= min_freq]
    pruned_s = orig - len(seq)
    for sec in seq:
        moves = sec.get("rhetorical_moves", [])
        sec["rhetorical_moves"] = [m for m in moves if m.get("frequency", 1.0) >= min_freq]
    devs = model.get("rhetorical_devices", [])
    orig_d = len(devs)
    model["rhetorical_devices"] = [d for d in devs if d.get("frequency", 1.0) >= min_freq]
    pruned_d = orig_d - len(model["rhetorical_devices"])
    model["updated"] = datetime.now().isoformat()
    snapshot_model(mid, model_dir, auto=True)
    p.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Pruned '{mid}': -{pruned_s} sections, -{pruned_d} devices (min_freq={min_freq})")


def snapshot_model(mid, model_dir=None, auto=False):
    mdir = _mdir(model_dir)
    src = _path(mdir, mid)
    if not src.exists():
        print(f"Not found: {mid}", file=sys.stderr)
        return
    sdir = _snap_dir(mdir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = sdir / f"{mid}_{ts}.snapshot.json"
    shutil.copy2(src, dst)
    if not auto:
        print(f"Snapshot: {dst}")


def rollback_model(mid, snap_id, model_dir=None):
    mdir = _mdir(model_dir)
    dst = _path(mdir, mid)
    sdir = _snap_dir(mdir)
    cands = list(sdir.glob(f"{mid}_{snap_id}*.snapshot.json"))
    if not cands:
        cands = list(sdir.glob(f"*{snap_id}*.snapshot.json"))
    if not cands:
        print(f"Snapshot not found: {snap_id}", file=sys.stderr)
        return
    shutil.copy2(cands[0], dst)
    print(f"Rolled back to {cands[0].name}")


def detect_conflict(analysis_path, mid, model_dir=None):
    """Detect conflicts between new analysis and existing model."""
    mdir = _mdir(model_dir)
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    p = _path(mdir, mid)
    if not p.exists():
        print(f"Model not found: {mid}", file=sys.stderr)
        return
    model = json.loads(p.read_text(encoding="utf-8"))
    conflicts = []
    # Compare section functions
    existing_funcs = {s.get("rhetorical_function", "") for s in model.get("structural_patterns", {}).get("section_sequence", [])}
    new_funcs = {s.get("rhetorical_function", "") for s in analysis.get("sections", [])}
    if new_funcs and existing_funcs:
        mismatch = new_funcs - existing_funcs
        if mismatch:
            conflicts.append({"type": "new_section_function", "items": list(mismatch)})
    if conflicts:
        print("Conflicts detected:")
        print(json.dumps(conflicts, indent=2, ensure_ascii=False))
    else:
        print("No conflicts detected.")


def export_model(mid, output, model_dir=None):
    mdir = _mdir(model_dir)
    src = _path(mdir, mid)
    if not src.exists():
        print(f"Not found: {mid}", file=sys.stderr)
        return
    dst = Path(output)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    print(f"Exported → {dst}")


def report_model(mid, output=None, model_dir=None):
    """Generate a human-readable markdown report for a model."""
    mdir = _mdir(model_dir)
    p = _path(mdir, mid)
    if not p.exists():
        print(f"Not found: {mid}", file=sys.stderr)
        return
    model = json.loads(p.read_text(encoding="utf-8"))

    lines = []
    lines.append(f"# 模型报告：{model.get('label', mid)}")
    lines.append(f"")
    lines.append(f"- **模型 ID**: {mid}")
    lines.append(f"- **类型签名**: {model.get('type_signature', 'N/A')}")
    lines.append(f"- **论文数量**: {model.get('papers_count', 0)}")
    lines.append(f"- **整体置信度**: {model.get('confidence', 0):.3f}")
    lines.append(f"- **创建时间**: {model.get('created', 'N/A')}")
    lines.append(f"- **更新时间**: {model.get('updated', 'N/A')}")
    lines.append(f"")

    # Argumentation model
    am = model.get("argumentation_model", {})
    if am:
        lines.append(f"## ① 论证模型（置信度 {am.get('confidence', 0):.3f}）")
        cf = am.get("classification_frameworks", [])
        if cf:
            lines.append(f"### 分类框架")
            for f in cf:
                lines.append(f"- {f}")
        ast = am.get("argumentation_structures", [])
        if ast:
            lines.append(f"### 论证结构")
            for s in ast:
                lines.append(f"- {s}")
        pd = am.get("position_differentiations", [])
        if pd:
            lines.append(f"### 立场分化")
            for d in pd:
                lines.append(f"- {d}")
        lines.append(f"")

    # Writing pattern model
    wpm = model.get("writing_pattern_model", {})
    if wpm:
        lines.append(f"## ② 写作模式模型（置信度 {wpm.get('confidence', 0):.3f}）")
        ifs = wpm.get("introduction_function_sequences", [])
        if ifs:
            lines.append(f"### 引言功能序列")
            for s in ifs:
                lines.append(f"- {s}")
        bop = wpm.get("body_organization_principles", [])
        if bop:
            lines.append(f"### 正文组织原则")
            for p in bop:
                lines.append(f"- {p}")
        pcp = wpm.get("paragraph_cohesion_patterns", [])
        if pcp:
            lines.append(f"### 段落衔接模式")
            for p in pcp:
                lines.append(f"- {p}")
        lines.append(f"")

    # Concept usage model
    cum = model.get("concept_usage_model", {})
    if cum:
        lines.append(f"## ③ 概念/选题模型（置信度 {cum.get('confidence', 0):.3f}）")
        tep = cum.get("title_expression_patterns", [])
        if tep:
            lines.append(f"### 标题表达模式")
            for p in tep:
                lines.append(f"- {p}")
        tsc = cum.get("topic_selection_criteria", [])
        if tsc:
            lines.append(f"### 选题判断依据")
            for c in tsc:
                lines.append(f"- {c}")
        lines.append(f"")

    # Paper list
    papers = model.get("papers_analyzed", [])
    if papers:
        lines.append(f"## 分析过的论文 ({len(papers)})")
        for pr in papers:
            lines.append(f"- `{pr.get('paper_id', '?')}` （{pr.get('added', '')[:10]}）")

    report = "\n".join(lines)

    if output:
        Path(output).write_text(report, encoding="utf-8")
        print(f"Report saved → {output}")
    else:
        print(report)


def import_model(input_path, model_dir=None):
    mdir = _mdir(model_dir)
    src = Path(input_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    mid = data.get("model_id", src.stem)
    dst = _path(mdir, mid)
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Imported as '{mid}' → {dst}")


def main():
    parser = argparse.ArgumentParser(description="Model update and management")
    parser.add_argument("--model-dir", help="Custom model directory")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list")
    p_add = sub.add_parser("add")
    p_add.add_argument("analysis_json")
    p_show = sub.add_parser("show")
    p_show.add_argument("model_id")
    p_match = sub.add_parser("match")
    p_match.add_argument("analysis_json")
    p_prune = sub.add_parser("prune")
    p_prune.add_argument("model_id")
    p_prune.add_argument("--min-frequency", type=float, default=0.3)
    p_snap = sub.add_parser("snapshot")
    p_snap.add_argument("model_id")
    p_roll = sub.add_parser("rollback")
    p_roll.add_argument("model_id")
    p_roll.add_argument("snapshot_id")
    p_conflict = sub.add_parser("detect-conflict")
    p_conflict.add_argument("analysis_json")
    p_conflict.add_argument("model_id")
    p_export = sub.add_parser("export")
    p_export.add_argument("model_id")
    p_export.add_argument("output_path")
    p_import = sub.add_parser("import")
    p_import.add_argument("input_path")
    p_report = sub.add_parser("report")
    p_report.add_argument("model_id")
    p_report.add_argument("--output", "-o", help="Output markdown file")

    args = parser.parse_args()

    cmds = {
        "list": lambda: list_models(args.model_dir),
        "add": lambda: add_analysis(args.analysis_json, args.model_dir),
        "show": lambda: show_model(args.model_id, args.model_dir),
        "match": lambda: match_analysis(args.analysis_json, args.model_dir),
        "prune": lambda: prune_model(args.model_id, args.min_frequency, args.model_dir),
        "snapshot": lambda: snapshot_model(args.model_id, args.model_dir),
        "rollback": lambda: rollback_model(args.model_id, args.snapshot_id, args.model_dir),
        "detect-conflict": lambda: detect_conflict(args.analysis_json, args.model_id, args.model_dir),
        "export": lambda: export_model(args.model_id, args.output_path, args.model_dir),
        "import": lambda: import_model(args.input_path, args.model_dir),
        "report": lambda: report_model(args.model_id, args.output, args.model_dir),
    }
    fn = cmds.get(args.command)
    if fn:
        fn()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
