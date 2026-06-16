# 写作模型 Schema 与置信度体系

本文档定义写作模型的数据结构和置信度计算系统。

---

## 模型核心概念

一个"写作模型"是对**一类论文**的结构规律的形式化抽象。它不是对单篇论文的描述，而是从多篇同类论文中提取的共同模式。

### 三个子模型维度

每篇论文精读后，从三个平行维度提取规律，存入同一个模型文件中：

```
                    ┌──────────────────────────────┐
                    │     同一模型族 .json           │
                    │  (共享 papers_analyzed 列表)    │
                    ├──────────────────────────────┤
                    │  ① 论证模型                    │
                    │    分类框架 / 论证结构 / 立场分化 │
                    ├──────────────────────────────┤
                    │  ② 写作模式模型                 │
                    │    引言功能 / 正文组织 / 段落衔接 │
                    ├──────────────────────────────┤
                    │  ③ 概念使用/选题模型            │
                    │    概念界定 / 选题判断 / 标题表达 │
                    └──────────────────────────────┘
```

三个子模型共享同一组论文基础，但各自独立演化、各有置信度。

| 子模型 | 关注的问题 | 对写作指导的贡献 |
|--------|-----------|----------------|
| **论证模型** | 这类论文怎么"想"的？论证的骨架是什么？ | 帮助用户搭建论证框架 |
| **写作模式模型** | 这类论文怎么"写"的？段落怎么组织？ | 帮助用户组织章节内容 |
| **概念/选题模型** | 这类论文选什么题、怎么界定概念的？ | 帮助用户判断选题和标题 |

### 三维度详细说明

#### ① 论证模型（Argumentation Model）

关注论文的**论证骨架**，包括：

| 要素 | 说明 | 示例 |
|------|------|------|
| **分类框架** | 论文如何对已有研究进行分类 | "按范式分为三派：实证主义、诠释主义、批判理论" |
| **论证结构** | 核心论证的推进方式 | "提出问题 → 分析矛盾 → 提出新框架 → 论证新框架的优越性" |
| **立场分化** | 该领域有哪些不同学术立场 | "立场A主张...，立场B反驳...，本文采取中间路线" |

精读时提取论证模型的问题：
- 这篇论文如何对既有文献进行分类？分类维度是什么？
- 核心论证从起点到终点经过哪些步骤？
- 论文在学术争论中采取了什么立场？它如何回应对立观点？

#### ② 写作模式模型（Writing Pattern Model）

关注论文的**文本组织方式**，包括：

| 要素 | 说明 |
|------|------|
| **引言功能序列** | 引言的句子按什么功能顺序排列 |
| **正文组织原则** | 正文各段落按什么逻辑组织 |
| **段落衔接模式** | 段与段之间的过渡策略 |
| **综合判断段落写法** | 综述/讨论段落的典型写法 |

精读时提取写作模式模型的问题：
- 引言有多少句？每句按什么功能顺序排列？
- 正文段落之间如何过渡？用了什么衔接词/策略？
- 哪些段落是"综合判断型"段落？它们有什么共同结构？

#### ③ 概念使用/选题模型（Concept Usage & Topic Selection Model）

关注论文的**选题和概念维度**，包括：

| 要素 | 说明 |
|------|------|
| **概念界定方式** | 核心概念如何被定义和操作化 |
| **选题切入角度** | 论文从什么角度选择研究问题 |
| **标题表达模式** | 论文标题的句式和结构 |
| **章节标题风格** | 各章节标题的命名方式 |

精读时提取概念模型的问题：
- 论文的核心概念是什么？它如何定义这个概念的？
- 这个研究问题为什么被认为"值得研究"？依据是什么？
- 论文标题是什么句式？（"A与B：基于C的研究" / "从X视角看Y"）

### 三子模型在写作指导中的协同

当用户需要写作指导时，三个子模型协同工作：

```
用户需求："我要写一篇关于数字经济的论文"
    │
    ├─ 论证模型 → 推荐论证框架
    │              "这类论文通常采用「文献分歧→新分析维度→综合框架」的论证路线"
    │
    ├─ 写作模式模型 → 推荐章节组织和段落写法
    │                   "引言建议采用五句式序列：背景→缺口→问题→方法→预览"
    │
    └─ 概念/选题模型 → 推荐选题方向和标题表达
                        "同领域标题常用「数字经济的X效应：基于Y的实证分析」句式"
```

### 置信度的三维化

每个子模型拥有独立的置信度，基于各自维度的数据积累量：

```json
{
  "confidence": 0.72,
  "argumentation_model": { "confidence": 0.68 },
  "writing_pattern_model": { "confidence": 0.75 },
  "concept_usage_model": { "confidence": 0.55 }
}
```

这意味着"写作模式"的规律积累得比较充分（0.75），而"概念使用"的规律还比较初步（0.55）。

### 模型的生命周期

```
单篇精读 → 提取结构特征 → 与已有模型匹配
    ├─ 匹配成功（相似度 ≥ 阈值）→ 合并进该模型，置信度提升
    └─ 匹配失败（无足够相似模型）→ 创建新模型族
```

---

## 模型 JSON Schema

模型文件存储在 `models/` 目录下，每个模型一个 `.json` 文件。

```json
{
  "model_id": "model_20250101_120000",
  "label": "理论建构型论文结构",
  "type_family": "auto",

  "type_signature": "建立合法性 → 建构理论框架 → 提出假设 → 方法说明 → 分析验证 → 理论讨论",

  "created": "2025-01-01T12:00:00",
  "updated": "2025-01-15T14:30:00",

  "papers_analyzed": [
    {"paper_id": "ABC123", "added": "2025-01-01T12:00:00"},
    {"paper_id": "DEF456", "added": "2025-01-10T09:00:00"},
    {"paper_id": "GHI789", "added": "2025-01-15T14:30:00"}
  ],
  "papers_count": 3,
  "confidence": 0.7241,

  "structural_patterns": {
    "section_sequence": [
      {
        "position": 1,
        "typical_title_variants": ["Introduction", "引言"],
        "rhetorical_function": "建立研究合法性",
        "frequency": 1.0,
        "core_purpose": "让读者认可该研究问题值得关注",
        "typical_length_ratio": 0.12,
        "rhetorical_moves": [
          {"move": "设立研究背景", "frequency": 1.0},
          {"move": "指出研究缺口", "frequency": 0.8}
        ]
      },
      {
        "position": 2,
        "typical_title_variants": ["Theoretical Framework", "Theory and Hypotheses"],
        "rhetorical_function": "建构理论框架",
        "frequency": 1.0,
        "core_purpose": "建立分析的概念工具和理论视角",
        "typical_length_ratio": 0.18,
        "chapter_internal_logic": "理论资源A介绍 → 资源B介绍 → 整合为统一框架 → 推导假设",
        "rhetorical_moves": [
          {"move": "引入核心理论", "frequency": 1.0},
          {"move": "概念操作化", "frequency": 0.7},
          {"move": "推导研究假设", "frequency": 0.9}
        ]
      }
    ],

    "argument_flow_pattern": "缺口填补型",

    "core_narrative_arc": "既有研究取得了一定进展但仍存在缺口 → 本文提出一个整合性理论框架 → 通过实证数据验证 → 重新审视既有研究"
  },

  "chapter_templates": {
    "chapter_1_introduction": {
      "purpose": "让读者在最短时间内理解研究价值，并愿意继续阅读",
      "internal_arc": "宽泛背景 → 逐渐聚焦 → 指出具体缺口 → 宣布本文回应方式",
      "recommended_length": "全文的 10-15%",
      "common_moves": [
        {"step": "开场句", "strategy": "用一个有冲击力的统计、现象或问题引入领域重要性"},
        {"step": "文献定位", "strategy": "简要回顾关键文献，建立对话基础"},
        {"step": "缺口声明", "strategy": "明确指出既有研究尚未解决的问题"},
        {"step": "本文回应", "strategy": "宣布本文如何填补该缺口"}
      ]
    }
  },

  "rhetorical_devices": [
    {
      "device": "让步式缺口声明",
      "pattern": "While [已有贡献]..., [缺口] remains underexplored...",
      "frequency": 0.9,
      "example": "While prior work has established the direct effects of X on Y, the mechanisms through which X operates in the context of Z remain poorly understood."
    },
    {
      "device": "三重推进式段落结构",
      "pattern": "主张 → 证据 → 解释（三段式段落）",
      "frequency": 0.7,
      "example": "..."
    }
  ]
}
```

---

## 置信度体系

### 定义

置信度（confidence）是一个 0.0–1.0 之间的浮点数，表示一个写作模型的可靠程度。它回答的问题是："基于目前积累的证据，这个模型对同类论文的预测有多可靠？"

### 计算公式

```
confidence = 0.4 × size_score + 0.6 × consistency_score

size_score     = 1 - exp(-n / 5)
consistency_score = 0.0~1.0（模型内论文结构相似度的平均值）
```

- **size_score**：样本量维度。n=0→0.0，n≈5→0.63，n≈15→0.95（递减增益）
- **consistency_score**：一致性维度。模型内各论文之间结构相似度的平均值

### 置信度解读

| 置信度范围 | 含义 | 建议用途 |
|-----------|------|---------|
| 0.00–0.20 | 初步观察：仅基于 1-2 篇论文 | 可参考，但应注明局限 |
| 0.20–0.50 | 基本模式：3-5 篇论文，模式初步显现 | 可用于构建初稿大纲 |
| 0.50–0.75 | 可靠模式：6-12 篇论文，内部一致性较高 | 可作为核心写作指导 |
| 0.75–0.90 | 成熟模型：12-20 篇论文，结构高度一致 | 可作为该类型论文的权威参考 |
| 0.90–1.00 | 高度稳定：20+ 篇论文，模式几乎确定 | 可用于自动生成完整大纲 |

### 置信度的呈现方式

在写作指导输出中，每条建议附带置信度标识：

```
建议：引言应采用"宽泛背景 → 逐步聚焦 → 缺口声明 → 本文回应"的推进路线
置信度：████████░░ 0.72（基于 8 篇同类论文）
```

### 多维置信度

除了整体置信度，模型还为每个结构要素维护独立置信度：

```json
{
  "section_confidence": {
    "引言": 0.85,
    "理论框架": 0.72,
    "研究假设": 0.91,
    "方法": 0.65
  },
  "rhetorical_device_confidence": {
    "让步式缺口声明": 0.88,
    "三段式段落": 0.54,
    "设问式过渡": 0.32
  }
}
```

这表示"研究假设推导"的模式非常稳定（0.91），但"设问式过渡"的使用仅基于少量观察（0.32）。

---

## 模型文件管理

### 目录结构

```
models/
├── model_20250101_120000.json    # 模型文件
├── model_20250110_090000.json
├── model_20250301_000000.json
├── archive/                       # 归档的旧版本模型
├── snapshots/                     # 模型快照（用于回滚）
└── README.md                     # 模型目录说明
```

### 命令（通过 manage_models.py）

```bash
# 列出所有模型
python scripts/manage_models.py list

# 将精读结果加入模型库（自动匹配或创建）
python scripts/manage_models.py add analysis_output.json

# 查找最匹配的模型
python scripts/manage_models.py match analysis_output.json

# 导出模型（供其他项目使用）
python scripts/manage_models.py export model_id output.json

# 导入模型
python scripts/manage_models.py import model_file.json

# 修剪模型（移除低置信度/低频节点）
python scripts/manage_models.py prune <model_id> [--min-frequency 0.3]

# 创建快照
python scripts/manage_models.py snapshot <model_id>

# 回滚到快照
python scripts/manage_models.py rollback <model_id> <snapshot_id>
```

---

## 模型进化与去冗余策略

### 问题

简单地将每篇新论文合并到模型中会导致：
- 低频噪声模式不断堆积
- 模型文件越来越大
- 核心规律被边缘模式稀释
- 写作指导的清晰度下降

### 解决方案：三层进化策略

### 第一层：入库去重（即时）

每次 `add` 操作时执行：

```python
def add_analysis(analysis):
    model = find_or_create_model(analysis)

    # 去重：检查各结构节点是否已存在类似项
    for new_section in analysis.sections:
        existing = find_similar_section(model, new_section)
        if existing:
            # 合并：更新频率，保留高频特征
            merge_section(existing, new_section)
        else:
            # 追加：新模式，设初始频率
            model.sections.append(new_section)

    # 更新置信度
    model.confidence = recompute_confidence(model)
```

**关键**：不是简单地 `append`，而是 `merge or append`。

### 第二层：修剪（定期）

定期运行的清理操作，移除低价值节点：

| 修剪目标 | 阈值 | 理由 |
|---------|------|------|
| 低频修辞步骤 | frequency < 0.3 | 只有不到1/3的同类论文使用，不构成"规律" |
| 低置信度修辞设备 | confidence < 0.15 | 样本太少，不具有参考价值 |
| 空段落模板 | 无内容 | 占位但未被填充的模板 |
| 重复条目 | 完全一致 | 合并操作遗留 |

```bash
python scripts/manage_models.py prune <model_id> [--min-frequency 0.3]
```

修剪不会删除论文记录（papers_analyzed），只会清理结构模式节点。

### 第三层：快照与回滚（重大变更前）

在对模型进行重大变更（如修剪、批量添加）之前，创建快照：

```bash
python scripts/manage_models.py snapshot <model_id>
# → 创建 models/snapshots/model_id_20250301_120000.json
```

如果修剪后发现误删了重要模式，可回滚：

```bash
python scripts/manage_models.py rollback <model_id> <snapshot_id>
```

### 进化周期建议

```
每添加 5 篇论文 → 执行一次 prune（轻量修剪）
每添加 15 篇论文 → 创建快照 → prune（深度修剪）
每添加 30 篇论文 → 审阅模型体系 → 合并相似模型族
```

### 模型体系的定期审阅

随着模型数量增长，不同模型族之间可能出现重叠。定期审阅时：

1. 列出所有模型的 `type_signature`
2. 计算模型间的语义相似度
3. 相似度 > 0.7 的考虑合并
4. 合并后重新计算置信度
