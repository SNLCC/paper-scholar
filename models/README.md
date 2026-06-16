# 模型目录

此目录用于存储 paper-scholar 技能积累的论文写作模型。

## 模型文件

每个 `.json` 文件代表一个写作模型（一类论文的结构模式抽象）。
模型由 `scripts/manage_models.py` 自动创建和维护。

## 使用

```bash
# 列出所有模型
python scripts/manage_models.py list

# 查看模型详情
python scripts/manage_models.py show <model_id>
```

## 导出/导入

模型可以导出到其他项目使用，也可以从外部导入：

```bash
python scripts/manage_models.py export <model_id> <output_path>
python scripts/manage_models.py import <input_path>
```

## 注意

- 此目录下的文件由脚本自动维护，不建议手动编辑
- 删除模型文件将丢失对应类型论文的积累数据
