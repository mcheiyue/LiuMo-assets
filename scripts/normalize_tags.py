#!/usr/bin/env python3
"""
LiuMo Tag & Dynasty Normalization Script (V8.0)
- Normalizes dynasty field to standardized short names
- Auto-generates English-code tags from type, dynasty, source fields
- Removes Chinese/English duplicate tags
- Idempotent: safe to run multiple times
"""

import json
import glob
import os
from collections import Counter

# === Dynasty Normalization Map ===
DYNASTY_MAP = {
    "唐代": "唐", "唐朝": "唐",
    "宋代": "宋", "宋朝": "宋",
    "元代": "元", "元朝": "元",
    "明代": "明", "明朝": "明",
    "清代": "清", "清朝": "清",
    "汉代": "汉", "汉朝": "汉",
    "秦代": "秦", "秦朝": "秦",
    "隋代": "隋", "隋朝": "隋",
    "晋代": "晋", "晋朝": "晋",
    "三国": "三国",
    "南北朝": "南北朝",
    # These are already normalized, keep as-is
    "唐": "唐", "宋": "宋", "元": "元", "明": "明", "清": "清",
    "汉": "汉", "秦": "秦", "隋": "隋", "晋": "晋",
    "先秦": "先秦", "现代": "现代", "当代": "当代", "近代": "近代",
    "南朝": "南朝", "五代": "五代", "魏晋": "魏晋",
    "春秋": "春秋", "战国": "战国",
    "辽": "辽", "金": "金",
    "蒙学": "蒙学", "古文": "古文", "未知": "未知",
}

# === Type to Genre Tag Map ===
TYPE_TAG_MAP = {
    "shi": "shi",
    "ci": "ci",
    "qu": "qu",
    "wen": "wen",
    "fu": "fu",
    "modern": "modern",
    # Special subtypes — preserved for better filtering,
    # displayed in Chinese via TAG_DISPLAY_MAP on frontend
    "prose": "prose",
    "fragment": "fragment",
    "yuefu": "yuefu",      # 乐府
    "乐府": "yuefu",      # 乐府 (Chinese type from tang_300.json)
    "shijing": "shijing",  # 诗经
    "guwen": "guwen",      # 古文
    "mengxue": "mengxue",  # 蒙学
}

# === Source to Collection Tag Map ===
SOURCE_TAG_MAP = {
    "k12": "K12",
    "tang_300": "tang_300",
    "song_300": "song_300",
}

# === Allowed tag values (only these English codes are valid in output) ===
ALLOWED_TAGS = set(TYPE_TAG_MAP.values()) | set(SOURCE_TAG_MAP.values())

# === Dynasty tag set (these must NOT appear in tags — dynasty has its own filter) ===
DYNASTY_TAG_SET = {
    "唐代", "唐朝", "宋代", "宋朝", "元代", "元朝",
    "明代", "明朝", "清代", "清朝", "汉代", "汉朝",
    "秦代", "秦朝", "隋代", "隋朝", "晋代", "晋朝",
    "唐", "宋", "元", "明", "清", "汉", "秦", "隋", "晋",
    "先秦", "南朝", "五代", "魏晋", "南北朝",
    "春秋", "战国", "三国", "辽", "金",
    "现代", "当代", "近代",
}

# === Chinese tags to remove (replaced by English codes) ===
CHINESE_TAG_BLACKLIST = {
    "五代", "诗经", "唐代", "宋代", "元代", "明代", "清代",
    "汉代", "秦代", "隋代", "唐朝", "宋朝", "元朝", "明朝", "清朝",
    "唐诗三百首", "宋词三百首",
    "诗", "词", "曲", "文", "赋", "现代诗",
    "wudai", "shijing", "caocao", "nalan",
}


def normalize_dynasty(dynasty: str) -> str:
    """Normalize dynasty to standard short name."""
    if not dynasty:
        return "未知"
    return DYNASTY_MAP.get(dynasty.strip(), dynasty.strip())


# === Source filename to subtype tag map ===
# When type field is too broad (e.g., shi), use source file to add subtype tags
FILE_SUBTYPE_MAP = {
    "shijing.json": "shijing",    # shi jing
    "gu_wen.json": "guwen",      # gu wen
    "meng_xue.json": "mengxue",  # meng xue
}


def generate_tags(item: dict, source_filename: str = "") -> list:
    """Generate normalized English-code tags for a poetry entry."""
    tags = set()

    # 1. Genre tag from type field
    type_val = item.get("type", "").strip().lower()
    if type_val in TYPE_TAG_MAP:
        tags.add(TYPE_TAG_MAP[type_val])

    # 2. Subtype tag from source filename (e.g., shijing.json -> shijing)
    if source_filename and source_filename in FILE_SUBTYPE_MAP:
        tags.add(FILE_SUBTYPE_MAP[source_filename])

    # 3. Dynasty tag — REMOVED. Dynasty is already a separate field with its own filter in UI.
    #    Do NOT add dynasty to tags; it clutters the "分类" (category) filter.

    # 4. Collection tag from source field
    source_val = item.get("source", "").strip().lower()
    if source_val in SOURCE_TAG_MAP:
        tags.add(SOURCE_TAG_MAP[source_val])

    # 5. Preserve existing valid tags (whitelist only: ALLOWED_TAGS + filter out dynasty names)
    existing_tags = item.get("tags", [])
    if isinstance(existing_tags, list):
        for t in existing_tags:
            t_str = str(t).strip()
            # Keep only if: (a) in ALLOWED_TAGS, AND (b) NOT a dynasty name
            if t_str and t_str in ALLOWED_TAGS and t_str not in DYNASTY_TAG_SET:
                tags.add(t_str)

    return sorted(tags)


def process_file(filepath: str) -> dict:
    """Process a single JSON file. Returns stats dict."""
    stats = {
        "file": os.path.basename(filepath),
        "total": 0,
        "dynasty_normalized": 0,
        "tags_added": 0,
        "tags_changed": 0,
    }

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both {"data": [...]} and direct [...] formats
    if isinstance(data, list):
        items = data
        is_wrapped = False
    elif isinstance(data, dict) and "data" in data:
        items = data["data"]
        is_wrapped = True
    else:
        print(f"  WARNING: Unknown JSON format in {filepath}, skipping")
        return stats

    if not isinstance(items, list):
        print(f"  WARNING: items is not a list in {filepath}, skipping")
        return stats

    modified = False
    for item in items:
        if not isinstance(item, dict):
            continue
        stats["total"] += 1

        # Normalize author: Unknown -> 佚名
        old_author = item.get("author", "")
        if old_author.strip() == "Unknown":
            item["author"] = "佚名"
            modified = True

        # Normalize dynasty
        old_dynasty = item.get("dynasty", "")
        new_dynasty = normalize_dynasty(old_dynasty)
        if old_dynasty != new_dynasty:
            item["dynasty"] = new_dynasty
            stats["dynasty_normalized"] += 1
            modified = True

        # Generate new tags
        old_tags = item.get("tags", [])
        if not isinstance(old_tags, list):
            old_tags = []
        new_tags = generate_tags(item, os.path.basename(filepath))

        old_tags_set = set(old_tags)
        new_tags_set = set(new_tags)

        if old_tags_set != new_tags_set:
            item["tags"] = new_tags
            if not old_tags:
                stats["tags_added"] += 1
            else:
                stats["tags_changed"] += 1
            modified = True

    # Write back if modified
    if modified:
        output = {"data": items} if is_wrapped else items
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    return stats


def main():
    raw_dir = "assets/raw"
    if not os.path.isdir(raw_dir):
        print(f"Error: '{raw_dir}' directory not found. Run from LiuMo-assets root.")
        return

    json_files = sorted(glob.glob(os.path.join(raw_dir, "*.json")))
    if not json_files:
        print(f"No JSON files found in '{raw_dir}'")
        return

    print(f"Processing {len(json_files)} files in {raw_dir}/...")
    print()

    total_stats = Counter()
    for fp in json_files:
        try:
            stats = process_file(fp)
            print(f"  {stats['file']}: {stats['total']} poems, "
                  f"dynasty_norm={stats['dynasty_normalized']}, "
                  f"tags_added={stats['tags_added']}, "
                  f"tags_changed={stats['tags_changed']}")
            for k, v in stats.items():
                if k != "file":
                    total_stats[k] += v
        except Exception as e:
            print(f"  ERROR processing {os.path.basename(fp)}: {e}")

    print()
    print("=" * 60)
    print(f"SUMMARY: {total_stats['total']} poems processed across {len(json_files)} files")
    print(f"  Dynasty normalizations: {total_stats['dynasty_normalized']}")
    print(f"  Tags added (was empty): {total_stats['tags_added']}")
    print(f"  Tags changed (was populated): {total_stats['tags_changed']}")
    print(f"  Total tag operations:     {total_stats['tags_added'] + total_stats['tags_changed']}")
    print("=" * 60)
    print()
    print("Done. All raw JSON files are now normalized.")
    print("Next step: re-run consolidate_v8.py and builder.py to rebuild the database.")


if __name__ == "__main__":
    main()
