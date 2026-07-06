#!/usr/bin/env python3
"""
sentence_coverage.py — 逐句覆盖率机器可数脚本

从 PDF 提取的纯文本中，自动按章节切分并数每章节的句子总数，
辅助在第 4 步"逐句分析闸门"中报告句级覆盖率。

用法：
  python sentence_coverage.py --input paper.txt
  python sentence_coverage.py --input paper.txt --output report.md
"""

import argparse
import re
from pathlib import Path


def count_sentences(text: str) -> int:
    """数完整句子数：句号、问号、感叹号结尾。"""
    text = text.strip()
    n = text.count('。') + text.count('？') + text.count('！')
    return n


def clean_noise(text: str):
    """
    移除 PDF 提取中的非正文噪音（范围定位策略）。

    策略：
    1. 定位正文范围：[关键词之后] ~ [参考文献/注释之前]
    2. 范围内的页眉/页脚/脚注行被清洗

    返回：(清洗后的文本字符串, 被移除行的描述列表)
    """
    lines = text.split('\n')

    # === 第一步：定位正文范围 ===
    body_start_idx = None
    body_end_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 摘要结束的标志
        if body_start_idx is None and re.match(r'^(关键词|中图分类号|文献标识码|文章编号)\b', stripped):
            body_start_idx = i + 1

        # 正文结束的标志
        if re.match(r'^(参考文献|注释|作者简介|责任编辑)\b', stripped):
            body_end_idx = i
            break

    # === 第二步：清洗 ===
    cleaned_lines = []
    removed_lines = []

    inline_noise_patterns = [
        r'^[\d]+$',
        r'^[\d]+\.\d+$',
        r'^[一二三四五六七八九十百千]+$',
        r'^·[\d\s]+$',
        r'^\d+\s*\|$',
        r'^\|\s*\d+$',
    ]

    in_body = False
    for i, line in enumerate(lines):
        stripped = line.strip()

        if body_start_idx is not None and i == body_start_idx:
            in_body = True
            continue

        if body_end_idx is not None and i >= body_end_idx:
            if in_body:
                removed_lines.append(f'[正文结束] {stripped[:30]}')
            break

        if not in_body:
            if stripped:
                removed_lines.append(f'[元信息] {stripped[:30]}')
            continue

        is_noise = False
        for pattern in inline_noise_patterns:
            if re.match(pattern, stripped):
                is_noise = True
                break

        if is_noise:
            removed_lines.append(f'[噪音] {stripped[:50]}')
        elif stripped in ('结', '语'):
            removed_lines.append(f'[结语标题] {stripped}')
        else:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines), removed_lines


def split_sections(text: str):
    """
    按章节标题切分文本。

    处理逻辑：
    1. clean_noise 范围定位清洗
    2. 识别主章节（一、二、...）
    3. 识别结语起点

    返回：(章节字典, 清洗日志列表)
    """
    cleaned_text, removed_lines = clean_noise(text)

    sections = {}

    main_positions = []
    for m in re.finditer(r'^([一二三四五六七八九十\d]+)、', cleaned_text, re.MULTILINE):
        main_positions.append((m.start(), m.group()))

    if not main_positions:
        return {'全文': cleaned_text}, removed_lines

    # 引言
    first_pos = main_positions[0][0]
    if first_pos > 0:
        intro_text = cleaned_text[:first_pos].strip()
        if intro_text:
            sections['引言'] = intro_text

    # 主章节
    for i, (pos, raw_title) in enumerate(main_positions):
        title = raw_title.strip()
        if i + 1 < len(main_positions):
            end = main_positions[i + 1][0]
        else:
            end = len(cleaned_text)
        seg = cleaned_text[pos:end]
        sections[title] = seg

    # 结语
    last_title = main_positions[-1][1].strip()
    last_seg = sections.get(last_title, '')
    all_conclusions = list(re.finditer(r'\n综上所述[，,]', last_seg))
    if all_conclusions:
        last_conclusion = all_conclusions[-1]
        body = last_seg[:last_conclusion.start()]
        conclusion = last_seg[last_conclusion.start():]
        sections[last_title] = body
        sections['结语'] = conclusion

    return sections, removed_lines


def main():
    parser = argparse.ArgumentParser(description='逐句覆盖率报告生成器')
    parser.add_argument('--input', '-i', required=True, help='输入文本文件路径')
    parser.add_argument('--output', '-o', help='输出报告路径（默认打印到 stdout）')
    parser.add_argument('--show-clean-log', action='store_true', help='显示清洗日志')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'❌ 文件不存在: {input_path}')
        return 1

    text = input_path.read_text(encoding='utf-8', errors='replace')

    sections, removed_lines = split_sections(text)

    section_stats = []
    total_sentences = 0
    for name, content in sections.items():
        n = count_sentences(content)
        total_sentences += n
        section_stats.append((name, n))

    original_count = count_sentences(text)
    noise_count = original_count - total_sentences

    lines = [
        '# 逐句覆盖率报告',
        '',
        f'**输入文件：** `{input_path}`',
        f'**章节数：** {len(sections)}',
        f'**总句子数（正文）：** {total_sentences}',
        f'**总句子数（原始）：** {original_count}',
        f'**清洗去除：** {noise_count} 句（含 {len(removed_lines)} 行非正文）',
        '',
        '## 各章节句子数',
        '',
        '| 章节 | 句子数 |',
        '|------|--------|',
    ]
    for name, n in section_stats:
        lines.append(f'| {name[:40]} | {n} |')

    if removed_lines:
        lines.extend([
            '',
            '## 清洗日志',
            '',
            f'共移除 {len(removed_lines)} 行非正文内容：',
            '',
        ])
        for entry in removed_lines[:30]:
            lines.append(f'- {entry}')
        if len(removed_lines) > 30:
            lines.append(f'- 等（共 {len(removed_lines)} 行）')

    lines.extend([
        '',
        '## 闸门填写模板',
        '',
        '需逐节核对并填写"已分析"列：',
        '',
        '| 节 | 句子数（机器可数） | 已分析（人工） | 覆盖率 |',
        '|----|------------------|--------------|--------|',
    ])
    for name, n in section_stats:
        lines.append(f'| {name} | {n} | <N> | <✓/✗> |')
    lines.append(f'| **总计** | **{total_sentences}** | **<A>** | **<P>%** |')
    lines.extend([
        '',
        '**闸门判定：** ✓ 通过（覆盖率=100%）/ ✗ 未通过',
        '',
    ])

    report = '\n'.join(lines)

    if args.output:
        Path(args.output).write_text(report, encoding='utf-8')
        print(f'✅ 报告已写入: {args.output}')
    else:
        print(report)

    return 0


if __name__ == '__main__':
    exit(main())
