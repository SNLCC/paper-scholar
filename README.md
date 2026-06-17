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

### 一键安装

```bash
python -c "$(curl -fsSL https://raw.githubusercontent.com/SNLCC/paper-scholar/main/install.py)"
```

### 或者手动安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装到 Codex（将 skill 复制到 ~/.codex/skills/）
python run.py install

# 3. 精读一篇论文
python run.py extract paper.pdf --output paper.txt
# 将 paper.txt 交给支持 Codex 的 AI 助手，它会按 8 条规范逐层分析

# 4. 存储分析结果
python run.py data store analysis.json
python run.py model add analysis.json

# 5. 查看所有命令
python run.py --help
```

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
| `extract_pdf_text.py` | PDF 文本提取（pdfplumber + 零依赖降级） |
| `fetch_zotero.py` | Zotero 三种接入模式（local/web/webdav） |
| `analyze_paper.py` | 期刊评分与选题分析 |
| `accumulate_data.py` | 论文数据写入 data/ |
| `check_coverage.py` | 覆盖率检查 |
| `compare_annotations.py` | 分析结果 vs 用户批注对比 |
| `record_learnings.py` | 学习记录聚合 |
| `update_model.py` | 模型更新、置信度、冲突检测、修剪快照 |
| `update_prescription.py` | 写作指导积累与置信度升级 |

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。

### 外部依赖

| 库 | 版本 | 许可证 | 说明 |
|----|------|--------|------|
| [pdfplumber](https://github.com/jsvine/pdfplumber) | `==0.11.10` | MIT | PDF 文本提取，已在此版本上验证 |

