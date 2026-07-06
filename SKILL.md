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

数据目录说明：
  精读成果、模型库、学习记录等积累数据存储在项目目录的 .paper-scholar/ 下。
  如需自定义，设置环境变量：export PAPER_SCHOLAR_DATA_DIR=/path/to/data

MinerU 在线解析（首选引擎）：
  PDF 提取默认使用 MinerU 在线 API（精度最高，支持扫描件/双栏/表格/公式）。
  无 Token 也可用轻量 API（≤10MB/≤20页，免登录 IP 限频）。
  设置 Token 可使用精准解析：export MINERU_TOKEN=your_token

本地引擎（离线 fallback）：
  当 MinerU 不可用或超限时，会提示安装 PyMuPDF 或 pdfplumber 作为本地引擎。
  也可通过 --engine local 强制使用本地引擎。

然后告诉我你想做什么。
"""

## 三大强制机制（流程保障）

以下三个机制贯穿全流程，确保精读质量可控、过程透明、结果可达：

### 机制 A：每步完成必报告

**目的**：防沉默偷懒，确保每一步都有明确产出再进入下一步。

**要求**：
- 每完成一步（阶段 0-8），必须输出进度报告
- 报告格式：
  ```bash
  python run.py progress init --paper "<标题>" --key "<Zotero Key>" --type "<类型>" --level "<精读/泛读/浏览>"
  python run.py progress report --step <N> --status completed --detail "<产出摘要>"
  python run.py progress show          # 查看完整进度
  ```
- **禁止**：一次完成多步只报告一次。每步独立报告。
- 状态标识：`[✓] 完成` / `[🔄] 进行中` / `[ ] 待处理` / `[⚠] 阻塞` / `[⏭] 跳过`

### 机制 B：关键决策点停顿询问

**目的**：防模糊自判断——遇到模糊/不确定时，不能自行决定，必须停顿询问主人。

**触发点**（遇到以下情况必须停顿）：
1. **类型判断含糊**：论文类型不在标准类别内、或发现新类型（如对话体）
2. **覆盖率未达标**：逐句覆盖率 < 100% 且需要决定是否补做
3. **理解验证不通过**：三检任一不通过，需要决定是重读还是继续
4. **模型冲突**：新分析与现有模型方向不一致

**执行方式**：
```bash
python run.py decision check --step <N> --context "<当前上下文>"
python run.py decision ask --question "<问题>" --option-a "<选项A>" --option-b "<选项B>"
```

**原则**：模糊时不能自判断。选项必须清晰，让主人能直接做决定。

### 机制 C：逐句分析闸门

**目的**：防虚报覆盖率——句级覆盖率未达到 100% 时，不得进入下一步。

**句子计数规则**：
- 仅计以句号（。）、问号（？）、感叹号（！）结尾的完整句子
- 引号内、括号内的内容不单独计句
- 图表标题、公式、列表项不计入

**闸门流程**：
1. 提取文本 → 运行 `python run.py scoverage --input paper.txt` 获得各章节句子数
2. 逐节核对"已分析"列，填写人工通过数
3. **闸门判定**：
   - ✅ **通过**：所有章节覆盖率 = 100% → 进入阶段 4
   - ✗ **未通过**：任一章节 < 100% → 阻断，记录未覆盖内容，告知主人，等待决定
4. **特别禁止**：不得以"总体覆盖率达标"替代"逐句覆盖"。每句都必须有明确标注。

**典型错误**（直接判定不通过）：
- 跳过整段（"这段不重要"）
- 跳过复杂句子（"这句太难分析"）
- 用"内容概括"替代"逐句标注"

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

**升级为精读时，必须明确报告以下三项，不能默默升级：**
```
升级报告模板：
- 原级别：<浏览 / 泛读>
- 新级别：精读
- 升级理由：<具体理由，例：与主人研究高度相关 / 主题价值高>
- 需补做项：<补做精细分析 + 理解验证 + 模型更新所有项>
```

调整记录写入分析报告的"评分日志"。

---

### 阶段 2：论文类型判断

基于全文内容（而非标题）判断论文类型。不预设分类标签，而是从内容中推断其结构族系。

常见类型参考：学术述评 / 理论建构 / 理论分析 / 混合型 / 其他

类型判断将影响后续分析的侧重点，但不影响覆盖率。

---

### 阶段 3：100% 覆盖率精读（闸门管控）

严格遵守 `references/analysis-framework.md` 的三层框架：
1. **篇章级**：实际修辞功能（读内容判定，不看标题）、章节内部逻辑展开、章节间衔接
2. **段落级**：实际段落功能、段落内部逻辑展开、修辞策略
3. **句级**：逐句标注（类型、功能、位置、与前句关系、作者意图、可迁移模板）

**三项覆盖率检查**：章节数、段落数、句数逐一核对，任何跳过得记录原因。

**闸门检查（机制 C）**：
```bash
python run.py scoverage --input paper.txt          # 获取各章节句子数
python run.py scoverage --input paper.txt --output report.md  # 生成报告
```

逐句分析完成后，必须运行闸门检查。只有所有章节句级覆盖率 = 100% 才能进入阶段 4。未通过时记录未覆盖内容并告知主人。

**特别禁止**：不得以"总体覆盖率达标"替代"逐句覆盖"。每句都必须有明确标注。

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

精读完成后，对论文的核心论证做三重检验。**只有三项全部通过才能进入阶段 6（模型更新）。任一项未通过则报告主人并等待决定。**

| 检验 | 通过标准 | 不通过处理 |
|------|---------|-----------|
| **转述检验** | 能用非专业语言向他人说清核心论点，无关键遗漏 | 不通过 → 需重读 |
| **反例检验** | 能找到至少一个动摇论点的例子，并判断论文是否已处理 | 不通过 → 需决定重读还是继续 |
| **衰减预判** | 重读时是否会有新的理解冲击？有冲击 → 通过 | 无冲击 → 需重读 |

三检结果记录在精读报告的末尾。判定格式：
```
理解验证：✅ 通过（三项全部达标）→ 进入模型更新
理解验证：✗ 未通过（<具体哪项>不达标）→ 报告主人，等待决定
```

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

**从精读中抽象组织方式：** 精读完成后，从论文中提取可迁移的组织模式：

| 维度 | 操作 | 示例 |
|------|------|------|
| **引言功能序列** | 分析引言中每段的功能排列顺序 | 历史背景 → 过渡 → 转折点 → 本文任务 |
| **正文组织原则** | 正文按什么维度分类 | 流派分类 / 时间线索 / 问题域划分 |
| **关键认知工具** | 作者用了哪些分析工具 | 转折点标记 / 方法论视角提炼 / 综合判断段 |
| **段落衔接技巧** | 段落间如何过渡 | 承上启下句 / 设问引导 / 对比过渡 |
| **综合判断段写法** | 分类叙述后用哪类段落收束 | 综上可见 / 总体而言 / 需要指出的是 |

提取结果存入写作模式模型，用于生成写作指导。

---

### 阶段 7：选题分析与论文评分

对于入库的论文，提供额外的分析维度：

1. **时代局限评估**：论文的时效性（数据是否过时？理论框架是否仍有效？）
2. **与研究关联**：该论文与用户已有研究/选题的关系（支持/对立/拓展？）
3. **可引用价值评分**：从当前视角看，该论文是否值得引用

---

### 阶段 8：复现触发

当用户开始写作时，根据以下条件自动调取相关模型：

| 触发场景 | 调取内容 |
|---------|---------|
| 主人提及某篇论文标题 | 调取该论文的完整分析记录（data/） |
| 主人提及某个概念 | 调取该概念所在的概念/选题模型 |
| 主人进入写作阶段 | 主动调取同类论文的写作模式模型 + 处方库 |
| 主人提出结构问题 | 调取位置-任务-成功标准模型 |
| 主人需要反例验证 | 调取冲突检测记录 + 相关模型 |
| 主人询问历史错误 | 调取学习记录（.learnings/） |

**复现内容（五要素）：**
1. 论文核心论点与论证结构（从 data/ 读取）
2. 该论文所属类型的模型特征（从 models/ 读取）
3. 原文引用与位置
4. 主人批注的论证线索
5. 最新处方库中相关条目

三个模型维度协同调取：

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
# 指定数据目录（默认 .paper-scholar/）
python run.py --data-dir /path/to/data <command>

# 获取论文（MinerU 在线解析 → 提示安装本地引擎）
python run.py extract paper.pdf --output paper.txt
python run.py extract paper.pdf --engine mineru
python run.py extract paper.pdf --force-mineru --mineru-token <token>
python run.py extract paper.pdf --engine local           # 强制本地引擎（离线）
python run.py extract paper.pdf --engine pymupdf-v62 --show-info  # 双栏自检
python run.py fetch local items --collection <key>

# 评分与精读
python run.py score template
python run.py coverage verify analysis.json paper.txt
python run.py scoverage --input paper.txt              # 逐句覆盖率闸门

# 进度追踪 + 决策检查
python run.py progress init --paper "Title" --key <key> --type T --level 精读
python run.py progress report --step 4 --status completed
python run.py progress show
python run.py decision check --step 3

# 批注与学习
python run.py compare analysis.json annotations.json
python run.py learn profile

# 模型管理+进化
python run.py model add analysis.json
python run.py model list
python run.py model report <model_id>
python run.py model prune <model_id>
python run.py model self-assess          # 自评估：检测相似模型、低置信度提示
python run.py model evolution-status     # 查看进化状态

# 写作指导（支持所有章节类型）
python run.py prescribe recommend introduction
python run.py prescribe recommend methodology
python run.py prescribe recommend conclusion
python run.py prescribe recommend 方法
python run.py prescribe recommend 结论
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
| 全流程 | 三大强制机制 A/B/C | `SKILL.md` (§三大强制机制) | `run.py progress`、`run.py decision`、`run.py scoverage` |
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
| 理解验证 | — | — | `references/understanding-verification.md` |
| 数据存储 | `run.py data` | `scripts/accumulate_data.py` | — |
| 批注标签库 | — | — | `references/annotation-tags.md` |
| 批注对比（语义对齐）| `run.py compare` | `scripts/compare_annotations.py` | `references/annotation-learning.md` |
| 学习记录 | `run.py learn` | `scripts/record_learnings.py` | `references/annotation-learning.md` |
| 模型管理+进化 | `run.py model` | `scripts/update_model.py` | `references/model-schema.md` |
| 写作标准（位置-任务-成功标准）| — | — | `references/writing-standards.md` |
| 写作指导 | `run.py prescribe` | `scripts/update_prescription.py` | `references/chapter-writing.md` |
| 逐句覆盖率闸门 | `run.py scoverage` | `scripts/sentence_coverage.py` | `SKILL.md` (§机制 C) |
| 进度追踪 | `run.py progress` | `scripts/progress_reporter.py` | `SKILL.md` (§机制 A) |
| 决策点检查 | `run.py decision` | `scripts/decision_checkpoint.py` | `SKILL.md` (§机制 B) |
| 完整工作流 | — | — | `references/complete-workflow.md` |
| 复现触发 | — | — | `references/reproduction-trigger.md` |
| 结构模式参考 | — | — | `references/humanities-structures.md` |

## 重要限制

- Zotero 集成需要 Zotero 应用正在运行
- 本 skill 构建的模型是经验性的——模型的质量取决于输入论文的质量和数量
- 写作指导是辅助性建议，最终的学术判断由用户做出
- 精读分析需要 Codex 投入大量上下文——对于长论文，建议分章节精读
