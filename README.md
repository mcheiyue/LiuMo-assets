# 流摹资源库 (LiuMo Assets)

这是 [流摹 (LiuMo)](https://github.com/mcheiyue/liumo) 的官方数据与资源仓库。本仓库采用“数据即源码 (Data as Code)”的理念，将庞大的二进制数据库解耦为可读、可维护的文本文件。

## 📂 目录结构

- **`data/`**: 诗词源数据（按朝代/体裁分类的 JSON 文件）。
  - `shi/tang_part*.json`: 唐诗（约 30万+ 首，已拆分）
  - `shi/song.json`: 宋诗
  - `ci/song.json`: 宋词
  - `modern/modern.json`: 现代诗
  - ...以及其他朝代与体裁
- **`fonts/`**: 字体资源文件（包含内置的霞鹜文楷等）。
- **`scripts/`**: 构建脚本，用于将 JSON 数据合并为 App 可用的 SQLite 数据库。

## 🚀 自动构建流程

本仓库配置了 GitHub Actions (CI/CD)。每当 `data/` 目录发生变更并推送到 `main` 分支时：

1.  **构建**: 自动运行 `scripts/build_db.py`，将数千个 JSON 条目合并。
2.  **打包**: 生成 `liumo_full.db.gz` 压缩数据库。
3.  **发布**: 创建一个新的 GitHub Release（版本号格式为 `data-YYYY.MM.DD`）。

**主应用 (LiuMo)** 会在构建过程中，自动拉取本仓库最新的 Release 产物，确保 App 始终拥有最新的诗词库，而无需更新 App 代码。

## 🤝 如何贡献数据

如果你发现诗词有误，或想添加新的诗词：

1.  在 `data/` 目录下找到对应的 JSON 文件（如 `modern/modern.json`）。
2.  直接编辑文件或添加新的 JSON 条目。
3.  提交 Pull Request。
4.  合并后，新的数据库会自动构建并推送给所有用户。

## 🛠️ 本地开发

如果你需要手动构建数据库：

```bash
# 需要 Python 3.10+
python scripts/build_db.py
```
构建完成后，会在根目录生成 `liumo_full.db` 文件。
