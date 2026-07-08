# paper-scholar

**论文精读与写作辅助工具** — 对人文社科论文进行章→段→句三层逐级精读，构建具有置信度支撑的写作模型。

读一篇不能只读一篇。paper-scholar 从每篇论文中提取可迁移的论证规律和写作模式，随积累越来越精准。

---

## 功能

- **精读论文**：按 8 条研读规范逐层分析（段落拆解、框架提炼、引用标注、表格对比、双向归类、批注还原、时代局限评估、多维评分）
- **积累模型**：从论证、写作模式、概念使用三个维度提取规律，自动聚类为可复用的写作模型
- **指导写作**：基于模型库生成章节布局、论证策略、句式模板，每条建议附带置信度
- **Zotero 集成**：读取论文库和批注，学习用户的分析风格
- **坚果云支持**：通过 WebDAV 获取 PDF 原文

---

## 快速开始

### 安装

```bash
# 方式一（推荐）：安装到当前项目
npx skills add SNLCC/paper-scholar
python .agents/skills/paper-scholar/run.py postinstall
python .agents/skills/paper-scholar/run.py configure

# 方式二：独立克隆使用（不依赖 Codex）
git clone https://github.com/SNLCC/paper-scholar.git
cd paper-scholar
python run.py postinstall
python run.py configure
```

> **提示**：建议设置别名简化命令：`alias ps='python .agents/skills/paper-scholar/run.py'`

### 快速上手

```bash
# 1. 精读一篇论文
ps extract paper.pdf --output paper.txt
# 将 paper.txt 交给支持 Codex 的 AI 助手，它会按 8 条规范逐层分析

# 2. 存储分析结果
ps data store analysis.json
ps model add analysis.json

# 3. 需要写作指导时
ps prescribe recommend introduction

# 4. 更新 skill
npx skills update
```

### 数据目录

精读成果、模型库、批注学习记录等用户数据存储在项目目录的 `.paper-scholar/` 下（可通过 `PAPER_SCHOLAR_DATA_DIR` 环境变量自定义路径）。

```bash
# 自定义数据目录
export PAPER_SCHOLAR_DATA_DIR=/path/to/your/data
ps data list      # 查看论文存档
ps model list     # 查看模型库
```

> **注意**：这些数据现在位于项目目录而非 skill 安装目录，因此 skill 更新时不会影响你的积累。如果你之前有旧版本的数据（在 `~/.codex/skills/paper-scholar/data/` 等位置），请手动迁移到新位置。

---

## 工作流

```
获取论文（PDF/Zotero/坚果云）
    ↓
质量评分（期刊40% + 作者25% + 论文特征35%）
    ↓  ← 动态调整（可升级/降级阅读深度）
论文类型判断
    ↓
100% 覆盖率精读（8条规范，三层分析）
    ↓  ← 与 Zotero 批注对比校准
理解验证（转述检验 / 反例检验 / 衰减预判）
    ↓
模型更新（去重合并 + 置信度计算 + 定期修剪）
    ↓
选题分析与论文评分
    ↓
复现触发（写作时自动调取相关模型）
```

---

## 三维模型体系

每篇论文精读后，从三个维度提取规律：

| 子模型 | 关注的问题 | 对写作的贡献 |
|--------|-----------|-------------|
| **论证模型** | 论文怎么"想"的？分类框架、论证结构、立场分化 | 帮用户搭建论证骨架 |
| **写作模式模型** | 论文怎么"写"的？引言功能序列、段落衔接、综合判断段 | 帮用户组织章节内容 |
| **概念/选题模型** | 论文选什么题？概念怎么界定？标题句式？ | 帮用户判断选题和标题 |

---

## 8 条研读规范

**理解层**（这篇论文在说什么、怎么说）：
1. 段落级别论证拆解
2. 分类框架提炼
3. 原文引用 + 位置标注
4. 表格化对比（≥3个并列项强制）
5. 双向归类（正向溯源 + 反向否定）

**反思层**（这篇论文的价值是什么、与我有什么关系）：
6. 批注逻辑还原 → 用户理解轨迹图
7. 时代局限评估
8. 多维评分 + 研究关联（支持/反驳/补充必填三项）

---

## 脚本清单

| 脚本 | 功能 |
|------|------|
| `run.py` | 统一命令行入口 |
| `postinstall.py` | pip 依赖安装 |
| `configure.py` | 配置向导（MinerU Token、Zotero API Key 等） |
| `extract_pdf_text.py` | PDF 文本提取（MinerU 在线首选 → PyMuPDF/pdfplumber 本地 fallback） |
| `fetch_zotero.py` | Zotero 三种接入模式（local/web/webdav） |
| `analyze_paper.py` | 期刊评分与选题分析 |
| `accumulate_data.py` | 论文数据写入 data/ |
| `check_coverage.py` | 覆盖率检查 |
| `sentence_coverage.py` | 逐句覆盖率闸门（机制 C） |
| `progress_reporter.py` | 进度追踪（机制 A） |
| `decision_checkpoint.py` | 决策点检查（机制 B） |
| `compare_annotations.py` | 分析结果 vs 用户批注对比 |
| `record_learnings.py` | 学习记录聚合 |
| `update_model.py` | 模型更新、置信度、冲突检测、修剪快照 |
| `update_prescription.py` | 写作指导积累与置信度升级 |

### MinerU 在线解析（首选引擎）

PDF 文本提取默认使用 **MinerU 在线 API**，对扫描版、双栏、表格、公式的解析精度最高。

```bash
# 免 Token 轻量 API（≤10MB，≤20页，IP 限频）
python run.py extract paper.pdf --engine mineru

# 精准 API（需设置 Token，≤200MB/≤200页）
export MINERU_TOKEN=your_token_here
python run.py extract paper.pdf --force-mineru

# 本地引擎（离线场景，按需安装）
python run.py extract paper.pdf --engine local           # 强制本地引擎
python run.py extract paper.pdf --engine pymupdf-v62 --show-info  # 双栏自检
```

> 本地引擎（PyMuPDF / pdfplumber）按需安装 —— 首次使用时脚本会提示并引导安装，或在 MinerU 不可用时自动提示。

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。

### 外部依赖

| 库 | 版本 | 许可证 | 说明 |
|----|------|--------|------|
| [requests](https://github.com/psf/requests) | `>=2.28.0` | Apache 2.0 | MinerU API 调用（唯一硬依赖） |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | 按需安装 | AGPL | 本地离线引擎，首次使用时提示安装 |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | 按需安装 | MIT | 本地离线引擎备选，按需安装 |

