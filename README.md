# 流摹资源库 (LiuMo Assets)

这是 [流摹 (LiuMo)](https://github.com/mcheiyue/liumo) 的官方数据与资源仓库。本仓库采用“数据即源码 (Data as Code)”的理念，为流摹应用提供高质量的诗词数据源。

> **V8.0 架构升级说明**：
> 自 V8.0 起，本仓库启用了全新的数据规范。移除了旧版 `content/type` 的嵌套结构，采用扁平化、强类型的 JSON 结构，并引入了更高效的构建管线。

## 📂 目录结构

- **`assets/`**: V8.0 标准化后的诗词源数据。
  - 采用新版 JSON Schema，字段更精简，元数据更丰富。
- **`src/`**: 构建系统的核心代码。
  - `builder.py`: 数据库构建器，负责验证、清洗并打包数据。
- **`fonts/`**: 字体资源文件。

## 🚀 自动构建流程 (V8.0 Pipeline)

本仓库配置了 GitHub Actions (CI/CD)。当 `main` 分支有更新时：

1.  **构建**: 运行 `src/builder.py`，执行严谨的数据校验。
2.  **打包**: 生成适配 V8.0 客户端的 `liumo_assets_v8.db.gz`。
3.  **发布**: 自动发布 Release，供客户端增量更新。

**主应用 (LiuMo)** 仅支持 V1.7.0+ 版本使用本仓库构建的 V8.0 数据包。

## 🤝 如何贡献数据

1.  在 `assets/` 下添加或修改 JSON 文件。
2.  确保遵循 V8.0 JSON Schema（参考现有文件）。
3.  提交 Pull Request，CI 会自动进行格式与完整性检查。

## 🛠️ 本地开发

```bash
# 需要 Python 3.10+
python src/builder.py
```
构建产物将输出至 `dist/` 目录。
