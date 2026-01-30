import sqlite3
import json
import os
import argparse
import hashlib

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "cleaned") # 修改为读取 cleaned 目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DB_NAME_LITE = "core.db"
DB_NAME_FULL = "liumo_full.db"

SCHEMA_V7_1 = """
CREATE TABLE IF NOT EXISTS poetry (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    dynasty TEXT NOT NULL,
    
    -- [兼容性保留字段]
    content TEXT,
    type TEXT,
    
    -- [V7.0 新增字段]
    layout_strategy TEXT DEFAULT 'GRID_STANDARD',
    content_json TEXT,
    display_content TEXT,
    tags TEXT,
    search_content TEXT
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

def get_db_path(db_type):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if db_type == 'lite':
        return os.path.join(OUTPUT_DIR, DB_NAME_LITE)
    else:
        return os.path.join(OUTPUT_DIR, DB_NAME_FULL)

def init_db(db_path):
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_V7_1)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_author ON poetry(author);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dynasty ON poetry(dynasty);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON poetry(title);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON poetry(tags);")
    
    conn.commit()
    return conn

def generate_id(item):
    """生成唯一ID: hash(title+author)"""
    # 优先使用 item 里已有的 id (如果 ai_cleaner 生成了)
    if item.get('id'): return item['id']
    raw = f"{item.get('title','')}_{item.get('author','')}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def process_lite(conn):
    print("构建 Lite 数据库...")
    cursor = conn.cursor()
    datasets = ["k12", "tang_300", "song_300"]
    
    total_count = 0
    seen_ids = set()
    
    for ds in datasets:
        # 清洗后的目录结构是 data/cleaned/[ds]/[file.json]，没有 raw 子目录
        raw_dir = os.path.join(DATA_DIR, ds)
        if not os.path.exists(raw_dir):
            print(f"警告: 数据集目录不存在 {raw_dir}")
            continue
            
        files = [f for f in os.listdir(raw_dir) if f.endswith(".json")]
        print(f"  处理 {ds}: {len(files)} 个文件")
        
        for f in files:
            path = os.path.join(raw_dir, f)
            with open(path, 'r', encoding='utf-8') as file:
                item = json.load(file)
                
            pid = generate_id(item)
            if pid in seen_ids:
                continue # 去重
            seen_ids.add(pid)
            
            # 字段映射与默认值填充
            title = item.get("title", "")
            author = item.get("author", "")
            dynasty = item.get("dynasty", "Unknown")
            content = item.get("content", "")
            
            # 优先使用已有的 V7.1 字段
            layout_strategy = item.get("layout_strategy", "GRID_STANDARD")
            content_json = item.get("content_json") # 可能为 None
            display_content = item.get("display_content", content)
            
            # 标签处理
            tags_list = item.get("tags", [])
            if item.get("type"):
                tags_list.append(item.get("type"))
            tags_str = ",".join(list(set(tags_list))) # 去重
            
            # 搜索内容: 标题 + 作者 + 内容 + 标签
            search_content = f"{title} {author} {content} {tags_str}"
            
            cursor.execute("""
                INSERT INTO poetry (
                    id, title, author, dynasty, content, type,
                    layout_strategy, content_json, display_content, tags, search_content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid, title, author, dynasty, content, item.get("type", ""),
                layout_strategy,
                content_json,
                display_content,
                tags_str,
                search_content
            ))
            
            total_count += 1
            
    # 写入元数据
    cursor.execute("INSERT OR REPLACE INTO metadata VALUES ('version', 'v1.7.0-lite')")
    cursor.execute("INSERT OR REPLACE INTO metadata VALUES ('build_date', '2026-01-29')")
    cursor.execute("INSERT OR REPLACE INTO metadata VALUES ('record_count', ?)", (str(total_count),))
    
    conn.commit()
    print(f"Lite DB build complete. Total records: {total_count}")

def main():
    parser = argparse.ArgumentParser(description="构建流墨数据库")
    parser.add_argument("--type", choices=['lite', 'full'], required=True, help="构建类型")
    args = parser.parse_args()
    
    db_path = get_db_path(args.type)
    conn = init_db(db_path)
    
    if args.type == 'lite':
        process_lite(conn)
    else:
        print("Full build not implemented yet.")
        
    conn.close()
    print(f"数据库已保存至: {db_path}")

if __name__ == "__main__":
    main()
