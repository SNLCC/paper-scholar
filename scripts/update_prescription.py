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

DEFAULT_PRESCRIPTION_DIR = Path(__file__).resolve().parent.parent / "prescriptions"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


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


def recommend(chapter_type: str, model_dir: str | None = None):
    """Generate writing recommendations for a chapter type based on models."""
    mdir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    if not mdir.exists():
        print(f"No model directory at {mdir}")
        return

    print(f"Writing recommendations for '{chapter_type}' section:")
    print("=" * 60)

    # Search across all models for relevant chapter patterns
    for f in sorted(mdir.glob("*.json")):
        if f.name in ("index.json",):
            continue
        try:
            model = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Check writing_pattern_model for relevant patterns
        wpm = model.get("writing_pattern_model", {})
        ifs = wpm.get("introduction_function_sequences", [])
        if chapter_type.lower() in ("introduction", "引言", "绪论"):
            for seq in ifs:
                print(f"\n📖 From model '{f.stem}' (conf={wpm.get('confidence', 0):.2f}):")
                print(f"   Function sequence: {seq}")

        # Check chapter_templates
        for key, template in model.get("chapter_templates", {}).items():
            if chapter_type.lower() in key.lower():
                purpose = template.get("purpose", "")
                arc = template.get("internal_arc", "")
                print(f"\n📖 From model '{f.stem}':")
                if purpose:
                    print(f"   Purpose: {purpose}")
                if arc:
                    print(f"   Internal arc: {arc}")
                for move in template.get("common_moves", []):
                    print(f"   • {move.get('step', '')}: {move.get('strategy', '')}")


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


def main():
    parser = argparse.ArgumentParser(description="Writing guidance management")
    parser.add_argument("--prescription-dir", help="Prescriptions directory")
    parser.add_argument("--model-dir", help="Model directory")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list")
    p_add = sub.add_parser("add")
    p_add.add_argument("prescription_json")
    p_rec = sub.add_parser("recommend")
    p_rec.add_argument("chapter_type", help="e.g. introduction, methodology, conclusion")
    p_upg = sub.add_parser("upgrade")
    p_upg.add_argument("prescription_id")

    args = parser.parse_args()

    if args.command == "list":
        list_prescriptions(args.prescription_dir)
    elif args.command == "add":
        add_prescription(args.prescription_json, args.prescription_dir)
    elif args.command == "recommend":
        recommend(args.chapter_type, args.model_dir)
    elif args.command == "upgrade":
        upgrade(args.prescription_id, args.prescription_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
