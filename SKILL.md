---
name: paper-scholar
description: >
  论文精读与写作辅助技能。通过对人文社科论文的章→段→句三层逐级精读（100%覆盖率），
  从内容中动态识别论文的结构模式和论证规律，构建具有置信度支撑的写作模型，
  从而指导用户完成从论文构思到逐章写作的全流程。
  
  适用场景：（1）用户提供论文PDF/Zotero条目，要求精读分析；
  （2）用户要求理解某类论文的谋篇布局规律；
  （3）用户需要写作指导——生成大纲、章节规划、论证策略建议；
  （4）用户希望在Zotero批注基础上优化分析精度；
  （5）用户积累了多篇论文后希望提取可迁移的写作模式。
  
  不使用关键词/信号词进行逻辑关系判定——所有维度分析均基于语义理解。
---

# paper-scholar — 论文精读与写作

## 核心理念

**模型建构，而非数据堆积。**
- 数据堆积：记住论文的事实、引用、观点
- 模型建构：从多篇同类论文中发现共同规律，抽象为可指导实践的分析框架

读一篇不能只读一篇——从单篇中提取可泛化的写作模式与论证规律。

**三维模型积累**：每篇论文精读后，从三个维度提取规律，存入统一模型：

| 维度 | 关注 | 对写作的贡献 |
|------|------|-------------|
| **论证模型** | 论文怎么"想"——分类框架、论证结构、立场分化 | 帮用户搭建论证骨架 |
| **写作模式模型** | 论文怎么"写"——引言功能序列、正文组织、段落衔接 | 帮用户组织章节内容 |
| **概念/选题模型** | 论文选什么题、怎么界定概念——概念使用、选题判断、标题表达 | 帮用户判断选题和标题 |

所有逻辑关系的判定基于语义理解，而非关键词匹配。

## 首次激活引导

当首次激活本 skill 时（即用户表现出论文精读或写作需求时），向用户呈现以下介绍：

"""
[paper-scholar] 论文精读与写作助手

我可以帮你做三件事：

路径1：精读一篇论文
  给我一篇论文（PDF/Zotero/直接粘贴文本），我会：
  -> 先对论文质量评分，决定精读/泛读/浏览
  -> 按 8 条研读规范逐层分析（篇章->段落->句子，100% 覆盖）
  -> 从论证、写作模式和概念使用三个维度提取规律
  -> 与你的 Zotero 批注对比，学习你的分析风格

路径2：指导你写论文
  告诉我你的研究主题，我会：
  -> 从积累的模型库中找到同类论文的结构规律
  -> 推荐章节布局、论证策略和句式模板
  -> 附带置信度说明

路径3：探索你的研究库
  -> 连接 Zotero 查看你的论文收藏
  -> 从坚果云下载论文

开始前：
  python install.py   # 装依赖 + 注册到 Codex，已装则自动检查更新

然后告诉我你想做什么。
"""

## 完整工作流（8 阶段）

### 阶段 0：获取论文（任选其一）

**方式A — 从 Zotero 获取**
1. 确认 Zotero 正在运行（本地 API：`http://localhost:23119/api/`）
2. 列出论文供用户选择：
   ```bash
   python scripts/fetch_zotero.py local collections
   python scripts/fetch_zotero.py local items --collection <key>
   ```
3. 获取论文详情、PDF 路径和批注：
   ```bash
   python scripts/fetch_zotero.py local item <item_key> --annotations --pdf-path
   ```
4. 用 `extract_pdf_text.py` 提取全文
5. 如果论文有批注，先读取批注（参见 `references/annotation-learning.md`）

**方式B — 从坚果云 WebDAV 获取**
```bash
python scripts/fetch_zotero.py webdav --user <email> --password <app_pwd> get <remote> <local>
python scripts/extract_pdf_text.py <local> --output paper.txt
```

**方式C — 本地文件或用户直接提供文本**
```bash
python scripts/extract_pdf_text.py <pdf_path> --output paper.txt
```

---

### 阶段 1：质量评分 → 确定阅读深度

严格按照 `references/quality-scoring.md` 进行评分。

**三个维度加权**：
- 期刊层次（40%）→ CSSCI/核心/省级 等
- 作者权威（25%）→ 学术头衔 / H-index / 发文历史
- 论文特征（35%）→ 引用 / 方法严谨性 / 论证完整性 / 创新性 / 写作质量

**评分决策**：

| 总分 | 阅读深度 | 行为 |
|------|---------|------|
| ≥ 70 | **精读** | 完整 100% 覆盖率三层分析，建模入库 |
| 40–69 | **泛读** | 篇章+段落级分析，不做逐句标注，不入库 |
| < 40 | **浏览** | 仅提取摘要、标题、核心论点 |

输出评分 JSON 供后续使用。

---

### 阶段 1.5：动态调整

评分是起点，不是终点。阅读过程中持续评估：
- 浏览中发现内容超出预期 → 升级为泛读/精读（用户确认）
- 精读中发现名不副实 → 降级（用户确认）
- 用户随时可手动覆盖

调整记录写入分析报告的"评分日志"。

---

### 阶段 2：论文类型判断

基于全文内容（而非标题）判断论文类型。不预设分类标签，而是从内容中推断其结构族系。

常见类型参考：学术述评 / 理论建构 / 理论分析 / 混合型 / 其他

类型判断将影响后续分析的侧重点，但不影响覆盖率。

---

### 阶段 3：100% 覆盖率精读

严格遵守 `references/analysis-framework.md` 的三层框架：
1. **篇章级**：实际修辞功能（读内容判定，不看标题）、章节内部逻辑展开、章节间衔接
2. **段落级**：实际段落功能、段落内部逻辑展开、修辞策略
3. **句级**：逐句标注（类型、功能、位置、与前句关系、作者意图、可迁移模板）

**三项覆盖率检查**：章节数、段落数、句数逐一核对，任何跳过得记录原因。

```bash
python scripts/check_coverage.py report analysis.json
python scripts/check_coverage.py verify analysis.json original.txt
```

精读产出：
- 精读报告（.md，可读格式）
- 结构化分析数据（.json，按 `references/analysis-framework.md` 格式）

---

### 阶段 4：批注对比与校准

如果论文有 Zotero 批注，执行以下步骤：

1. **读取批注**：位置、颜色、评注内容
2. **对比分析**：skill 的精读标注 vs 用户的批注
3. **运行对比脚本**：
   ```bash
   python scripts/compare_annotations.py compare analysis.json annotations.json
   ```
4. **识别差异**：skill 漏标了什么？用户关注了什么？
5. **写入 .learnings/**：偏差案例记录（原则："小研分析可能更优"——不强行对齐）
6. **定期聚合用户画像**：
   ```bash
   python scripts/record_learnings.py aggregate
   python scripts/record_learnings.py profile
   ```

参见 `references/annotation-learning.md`。

---

### 阶段 5：理解验证（三检）

精读完成后，对论文的核心论证做三重检验：

1. **转述检验**：用自己的话复述核心论证过程 → 是否准确？
2. **反例检验**：是否存在反例、边界条件或替代解释？
3. **衰减预判**：该论文的结论在 3-5 年后是否仍然有效？

三检结果记录在精读报告的末尾。

---

### 阶段 6：模型更新（智能进化）

将精读结果纳入模型库：

```bash
# 数据存储
python scripts/accumulate_data.py store analysis_output.json

# 模型更新（含去重合并）
python scripts/update_model.py add analysis_output.json

# 冲突检测（新数据与已有模型的差异）
python scripts/update_model.py detect-conflict analysis_output.json <model_id>
```

**智能合并**（不是简单追加）：
- 查重：避免同一篇论文重复入库
- 去重合并：新结构模式与已有模式对比——相似则合并（更新频率），全新则追加
- 置信度更新：基于样本量和一致性重新计算
- 冲突检测：新模式与既有模式的方向不一致时发出警告

**定期维护**：
```bash
# 修剪：移除低频节点（建议每 5 篇论文执行一次）
python scripts/update_model.py prune <model_id> --min-frequency 0.3

# 快照：重大变更前创建（建议每 15 篇论文一次）
python scripts/update_model.py snapshot <model_id>

# 回滚：如修剪后有误删，可回滚
python scripts/update_model.py rollback <model_id> <snapshot_id>
```

模型 Schema 和进化策略详见 `references/model-schema.md`。

---

### 阶段 7：选题分析与论文评分

对于入库的论文，提供额外的分析维度：

1. **时代局限评估**：论文的时效性（数据是否过时？理论框架是否仍有效？）
2. **与研究关联**：该论文与用户已有研究/选题的关系（支持/对立/拓展？）
3. **可引用价值评分**：从当前视角看，该论文是否值得引用

---

### 阶段 8：复现触发

当用户开始写作时，三个模型维度协同调取：

```
用户写作"引言"章节
    │
    ├─ 论证模型 → 引言论证步骤序列
    │               "同类论文引言通常采用：背景→渐进聚焦→缺口声明→本文回应"
    │
    ├─ 写作模式模型 → 引言句式模板
    │                   "让步式缺口声明模板 + 置信度 + 例句"
    │
    └─ 概念/选题模型 → 标题风格参考
                       "同类论文标题常用句式 + 选题切入角度"
```

每个维度提供的建议附带各自置信度标识。

## 快速命令参考

所有操作通过统一入口 `run.py` 调用：

```bash
# 获取论文
python run.py extract paper.pdf --output paper.txt
python run.py fetch local items --collection <key>

# 评分与精读
python run.py score template
python run.py coverage verify analysis.json paper.txt

# 批注与学习
python run.py compare analysis.json annotations.json
python run.py learn profile

# 模型管理
python run.py model add analysis.json
python run.py model list
python run.py model report <model_id>
python run.py model prune <model_id>

# 写作指导
python run.py prescribe recommend introduction
```

## 常见问题

### CNKI 论文提取乱码

CNKI 的 PDF 使用自定义字体 `HGFX_CNKI`，其字符映射表不完整，导致部分文字提取为乱码。这是已知局限，目前暂无完美解决方案。建议在 CNKI 网站中使用"导出→文字"功能获取纯文本后，再交给 Codex 分析。

## 置信度说明

所有基于模型给出的建议都必须附带置信度标识，格式：

```
建议：[内容]
置信度：████████░░ 0.72（基于 8 篇同类论文）
```

置信度的含义和计算方法见 `references/model-schema.md`。

## 阶段与规范交叉引用

| 阶段 | 涉及的规范 | 参考文档 | 相关命令 |
|------|-----------|---------|---------|
| 阶段1：质量评分 | 规范8（多维评分） | `references/quality-scoring.md` | `run.py score` |
| 阶段2：类型判断 | — | `references/humanities-structures.md` | — |
| 阶段3：精读 | **规范1-5**（理解层） | `references/analysis-framework.md` (§规范1-5) | `run.py coverage` |
| 阶段4：批注校准 | **规范6**（批注还原） | `references/annotation-learning.md` | `run.py compare`、`run.py learn` |
| 阶段5：理解验证 | **规范7**（时代局限） | `references/analysis-framework.md` (§规范7) | — |
| 阶段6：模型更新 | — | `references/model-schema.md` | `run.py model` |
| 阶段7：选题分析 | 规范8（研究关联） | `references/analysis-framework.md` (§规范8) | `run.py score` |
| 阶段8：复现触发 | 三维模型 | `references/model-schema.md` (§三个子模型维度) | `run.py prescribe` |

## 资源索引

| 用途 | 统一命令 | 后端脚本 | 参考文档 |
|------|---------|---------|---------|
| PDF 文本提取 | `run.py extract` | `scripts/extract_pdf_text.py` | — |
| Zotero 接入 | `run.py fetch` | `scripts/fetch_zotero.py` | `references/zotero-nutstore.md` |
| 质量评分 | `run.py score` | `scripts/analyze_paper.py` | `references/quality-scoring.md` |
| 精读分析（8规范）| — | — | `references/analysis-framework.md` |
| 覆盖率检查 | `run.py coverage` | `scripts/check_coverage.py` | `references/analysis-framework.md` |
| 数据存储 | `run.py data` | `scripts/accumulate_data.py` | — |
| 模型管理 | `run.py model` | `scripts/update_model.py` | `references/model-schema.md` |
| 批注对比 | `run.py compare` | `scripts/compare_annotations.py` | `references/annotation-learning.md` |
| 学习记录 | `run.py learn` | `scripts/record_learnings.py` | `references/annotation-learning.md` |
| 写作指导 | `run.py prescribe` | `scripts/update_prescription.py` | `references/chapter-writing.md` |
| 结构模式参考 | — | — | `references/humanities-structures.md` |

## 重要限制

- Zotero 集成需要 Zotero 应用正在运行
- 本 skill 构建的模型是经验性的——模型的质量取决于输入论文的质量和数量
- 写作指导是辅助性建议，最终的学术判断由用户做出
- 精读分析需要 Codex 投入大量上下文——对于长论文，建议分章节精读
