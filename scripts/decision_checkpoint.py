#!/usr/bin/env python3
"""
decision_checkpoint.py — 决策点检查（机制 B）

在关键决策点前检查是否需要停顿询问主人，减少遗漏。
在每个决策点前调用，确认是否有模糊/需要决定的点。

用法：
    python decision_checkpoint.py check --step 3 --context "对话体论文，标题含'对话'"
    python decision_checkpoint.py ask --question "是否补做覆盖率？" --option-a "A: 补做" --option-b "B: 保持当前"
"""

import sys
import argparse


CHECKPOINTS = {
    3: {
        "name": "判断论文类型",
        "checks": [
            ("论文类型是否在标准类别内？", "不在则需要询问主人"),
            ("是否含混合型？(评析+建构)", "是则记录主-X-Y辅格式"),
            ("是否发现新类型？", "是则报告主人确认"),
        ],
    },
    4: {
        "name": "精细分析覆盖率",
        "checks": [
            ("覆盖率是否达到 100%？", "低于 100% 必须报告并询问"),
            ("对话轮次/段落数是否完整覆盖？", "未覆盖必须补做"),
            ("是否需要跳过多余步骤？", "需明确说明原因"),
        ],
    },
    5: {
        "name": "理解验证",
        "checks": [
            ("转述检验是否通过？", "不通过需重读"),
            ("反例检验是否找到反例？", "需报告并判断论文是否处理"),
            ("衰减预判是否预期新理解？", "无冲击需重读"),
        ],
    },
    6: {
        "name": "模型更新前检查",
        "checks": [
            ("流程透明性检查是否完成？", "未完成不得进入"),
            ("本次论文与现有模型是否冲突？", "冲突标记[待验证] + 报告"),
            ("是否合并/新建？", "新类型需报告"),
            ("跨作者样本池是否过于集中？", "需标注警告"),
        ],
    },
}


def run_checkpoint(step, context=""):
    """运行检查清单"""
    if step not in CHECKPOINTS:
        print(f"⚠️  第 {step} 步没有预定义检查清单，请自行评估")
        return

    cp = CHECKPOINTS[step]
    print()
    print(f"🔍 第 {step} 步检查点：{cp['name']}")
    print(f"   上下文：{context}" if context else "")
    print("─" * 60)

    for question, hint in cp["checks"]:
        print(f"❓ {question}")
        print(f"   提示：{hint}")
        print()


def ask_question(question, options):
    """输出决策询问（标准格式）"""
    print()
    print("⚠️  决策点需要主人决定")
    print("─" * 60)
    print(f"问题：{question}")
    print()
    for opt in options:
        print(f"  {opt}")
    print()
    print("主人决定哪一个？（输入选项字母或提出其他选项）")
    print("─" * 60)


def main():
    parser = argparse.ArgumentParser(description="paper-scholar 决策点检查（机制 B）")
    subparsers = parser.add_subparsers(dest="action", required=True)

    check_parser = subparsers.add_parser("check", help="运行决策点检查")
    check_parser.add_argument("--step", type=int, required=True, help="步骤号")
    check_parser.add_argument("--context", default="", help="当前上下文")

    ask_parser = subparsers.add_parser("ask", help="触发决策询问")
    ask_parser.add_argument("--question", required=True, help="问题")
    ask_parser.add_argument("--option-a", required=True)
    ask_parser.add_argument("--option-b", required=True)
    ask_parser.add_argument("--option-c", default="")

    args = parser.parse_args()

    if args.action == "check":
        run_checkpoint(args.step, args.context)
    elif args.action == "ask":
        options = [f"A: {args.option_a}", f"B: {args.option_b}"]
        if args.option_c:
            options.append(f"C: {args.option_c}")
        ask_question(args.question, options)


if __name__ == "__main__":
    main()
