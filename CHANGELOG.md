# 更新日志 (Changelog)

## v8.2.0 - 数据修复与乐府标签 (2026-05-08)

### 🐛 关键修复 (Critical Fixes)
- **诗经标签恢复**: 修复了 `consolidate_v8.py` 去重逻辑导致诗经 305 首被截断为 19 首的问题。现在采用标签合并策略，当 key 重复时将新条目的 tags 合并到已有条目。
- **FTS 搜索修复**: 修复了 `builder.py` 中 `build_search_text()` 将每个汉字用空格隔开的问题。现已移除逐字空格插入逻辑，返回清理后的连续文本，恢复 unicode61 tokenizer 的自然分词。

### ✨ 新增功能 (Features)
- **乐府标签**: 新增 `tag_yuefu.py` 脚本，从古诗文网搜集《乐府诗集》完整标题列表（11 大类，160+ 标题），通过标题匹配为源数据追加 `yuefu` 标签。
- **标签规范化**: 更新 `consolidate_v8.py` 的 `generate_tags()` 函数，添加 `TYPE_TAG_MAP`、`FILE_SUBTYPE_MAP`、`ALLOWED_TAGS` 白名单，确保标签体系一致性。

### 📊 数据统计 (Data Stats)
- 诗经: 19 → **305** 首
- 乐府: 0 → **1003** 首
- 总计: **402,229** 首

---

## v8.0.0 - 架构重生 (2026-01-31)

### 🚀 核心架构 (Core Architecture)
- **全新 Schema**: 移除冗余字段，采用扁平化 `content_json` 存储结构化段落。
- **混合清洗管道**: 实施"规则优先 + AI 兜底"的混合清洗策略。
- **资源完全解耦**: 由 `LiuMo-assets` 独立管理数据构建与发布。
