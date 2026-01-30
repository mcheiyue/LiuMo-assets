import json
import os
import glob

# 本地 chinese-poetry 仓库路径 (注意: 这里是假设路径，实际运行需确保正确)
# 您的环境是: D:\Github\liumo\data\raw\chinese-poetry
# 但由于我在 liumo-assets-prep 下运行，我需要用相对路径或绝对路径
SOURCE_BASE = r"D:\Github\liumo\data\raw\chinese-poetry"
OUTPUT_DIR = "data/dist"

CONFIG = [
    {
        "name": "nalan",
        "path": "纳兰性德",
        "pattern": "*.json",
        "default_type": "ci",
        "default_dynasty": "清"
    },
    {
        "name": "wudai",
        "path": "五代诗词/huajianji",
        "pattern": "*.json", 
        "default_type": "ci",
        "default_dynasty": "五代"
    },
    { 
        "name": "wudai_nantang",
        "path": "五代诗词/nantang",
        "pattern": "*.json",
        "default_type": "ci",
        "default_dynasty": "五代"
    },
    {
        "name": "shijing",
        "path": "诗经",
        "pattern": "shijing.json",
        "default_type": "shi", # 诗经也是诗
        "default_dynasty": "先秦"
    },
    {
        "name": "caocao",
        "path": "曹操诗集",
        "pattern": "caocao.json",
        "default_type": "shi",
        "default_dynasty": "魏晋"
    }
]

def import_dataset(config):
    src_dir = os.path.join(SOURCE_BASE, config["path"])
    if not os.path.exists(src_dir):
        print(f"Skipping {config['name']}, path not found: {src_dir}")
        return []

    items = []
    # 支持 glob pattern
    files = glob.glob(os.path.join(src_dir, config["pattern"]))
    
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # chinese-poetry 数据可能是 list 或 dict (content字段)
            raw_items = data.get('content', data) if isinstance(data, dict) else data
            
            for raw in raw_items:
                # 标准化字段
                clean = {
                    "title": raw.get("title", raw.get("rhythmic", "")),
                    "author": raw.get("author", "Unknown"),
                    "content": "".join(raw.get("paragraphs", raw.get("content", []))), # 诗经 paragraphs -> content
                    "dynasty": raw.get("dynasty", config["default_dynasty"]),
                    "type": config["default_type"],
                    "tags": [config["name"], config["default_dynasty"]]
                }
                
                # 特殊处理：诗经章节
                if config["name"] == "shijing":
                    clean["tags"].append(raw.get("chapter", ""))
                    clean["tags"].append(raw.get("section", ""))
                
                items.append(clean)
                
    return items

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for conf in CONFIG:
        print(f"Importing {conf['name']}...")
        items = import_dataset(conf)
        if items:
            out_file = os.path.join(OUTPUT_DIR, f"{conf['name']}.json")
            # 如果已有 wudai.json，合并
            if "wudai" in conf["name"]:
                out_file = os.path.join(OUTPUT_DIR, "wudai.json")
                if os.path.exists(out_file):
                    with open(out_file, 'r', encoding='utf-8') as f:
                        items.extend(json.load(f))
            
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"  Saved {len(items)} records to {out_file}")

if __name__ == "__main__":
    main()
