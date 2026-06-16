# Zotero 与坚果云集成指南

本文档说明通过 paper-scholar skill 从 Zotero 和坚果云获取论文原文和批注。

---

## 三种接入方式

本 skill 提供三种互补的接入方式，可根据场景选用：

| 方式 | 命令 | 前提条件 | 适用场景 |
|------|------|---------|---------|
| **本地 API** | `local` | Zotero 桌面端正在运行 | 日常使用，最便捷 |
| **Web API** | `web` | Zotero API Key（在线申请） | Zotero 未运行，或远程访问 |
| **WebDAV** | `webdav` | 坚果云账号 + 应用密码 | 直接从云端下载 PDF 原文 |

---

## 方式一：本地 API（默认推荐）

Zotero 桌面端在运行时暴露本地 REST API，无需认证。

### 端点

`http://localhost:23119/api/`

### 使用

```bash
# 列出所有分类
python scripts/fetch_zotero.py local collections

# 列出某分类中的论文
python scripts/fetch_zotero.py local items --collection {key}

# 查看论文详情 + 批注 + PDF路径
python scripts/fetch_zotero.py local item {key} --annotations --pdf-path
```

### 限制

- Zotero 必须正在运行
- 仅限本机访问

---

## 方式二：Web API（远程访问）

通过 Zotero 的 Web API 获取数据，无需桌面端运行。

### 获取 API Key

1. 登录 https://www.zotero.org/settings/keys
2. 点击 "Create new private key"
3. 勾选必要的权限（至少需要 "Read" 权限）
4. 复制生成的 API Key

### 获取 User ID（可选）

可通过 API 自动获取。如果命令行未提供 `--user-id`，脚本会自动解析。

### 使用

```bash
# 列出分类
python scripts/fetch_zotero.py web --api-key "你的API_KEY" collections

# 列出论文
python scripts/fetch_zotero.py web --api-key "你的API_KEY" items

# 查看论文详情和批注
python scripts/fetch_zotero.py web --api-key "你的API_KEY" item {key} --annotations
```

### 建议

- API Key 建议通过环境变量 `ZOTERO_API_KEY` 传入，避免明文写在命令行
- Web API 有请求频率限制，批量操作时注意控制节奏

---

## 方式三：WebDAV（坚果云获取 PDF）

当 Zotero 使用坚果云作为附件存储时，可直接通过 WebDAV 协议下载 PDF 原文。

### 配置坚果云应用密码

1. 登录 https://www.jianguoyun.com/
2. 进入 **账户信息 → 安全选项 → 应用密码**
3. 点击 **添加应用密码**，名称填写 `paper-scholar`
4. 复制生成的 **应用密码**（注意：这不是你的坚果云登录密码）

### WebDAV 端点

```
https://dav.jianguoyun.com/dav/
```

### Zotero 在坚果云中的目录结构

Zotero 使用 WebDAV 同步时，文件通常存储在：

```
/dav/Zotero/{zotero_user_id}/storage/{hash}/{filename}.pdf
```

### 使用

```bash
# 列出坚果云中的 Zotero 存储目录
python scripts/fetch_zotero.py webdav --user "your@email.com" --password "应用密码" ls /dav/Zotero/

# 递归浏览找到论文 PDF
python scripts/fetch_zotero.py webdav --user "your@email.com" --password "应用密码" ls /dav/Zotero/{user_id}/storage/

# 下载 PDF 到本地
python scripts/fetch_zotero.py webdav --user "your@email.com" --password "应用密码" get \
    /dav/Zotero/{user_id}/storage/{hash}/paper.pdf \
    ./papers/paper.pdf
```

### 建议

- 应用密码建议通过环境变量 `NUTSTORE_APP_PASSWORD` 传入
- 使用 WebDAV 前，建议先用 `zotero local item {key} --pdf-path` 获取文件在坚果云中的相对路径

---

## 完整工作流：从 Zotero 论文到精读

推荐的端到端流程：

```bash
# 1. 查看 Zotero 中的分类，找到目标论文
python scripts/fetch_zotero.py local collections

# 2. 列出论文
python scripts/fetch_zotero.py local items --collection {key}

# 3. 获取论文详情、批注和 PDF 路径
python scripts/fetch_zotero.py local item {paper_key} --annotations --pdf-path

# 4a. 如果 PDF 存储在本地 → 直接提取文本
python scripts/extract_pdf_text.py {pdf_path} --output paper.txt

# 4b. 如果 PDF 在坚果云 → 通过 WebDAV 下载
python scripts/fetch_zotero.py webdav --user "$NUTSTORE_USER" --password "$NUTSTORE_PASS" \
    get {remote_pdf_path} ./paper.pdf
python scripts/extract_pdf_text.py ./paper.pdf --output paper.txt

# 5. 开始精读分析
```

---

## 环境变量配置（推荐）

为避免每次输入认证信息，可设置环境变量：

```bash
# Windows PowerShell
$env:ZOTERO_API_KEY = "你的API_KEY"
$env:NUTSTORE_USER = "your@email.com"
$env:NUTSTORE_PASS = "你的应用密码"
```

或在 Python 脚本中读取环境变量（fetch_zotero.py 已预留此接口）。
