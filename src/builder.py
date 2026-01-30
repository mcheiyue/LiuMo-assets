import sqlite3
import json
import os
import argparse
from pathlib import Path
import re
import hashlib

# === 配置 ===
DB_PATH = "output/liumo_v8.db"
DEFAULT_INPUT_DIR = "assets/final"

def build_search_text(title, author, content):
    """
    Build search text optimized for unicode61 tokenizer.
    Strategy: Add spaces between EVERY character (Chinese friendly).
    "床前明月光" -> "床 前 明 月 光"
    """
    full_text = f"{title} {author} {content}"
    cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', full_text)
    spaced_text = " ".join(list(cleaned))
    return spaced_text

def create_connection(db_file):
    """创建数据库连接"""
    conn = None
    try:
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
    return None

def setup_schema(conn):
    """初始化数据库表结构 (V8.0 Schema) - 重置数据库"""
    cursor = conn.cursor()
    
    print("Setting up V8.0 Schema...")
    cursor.execute("DROP TABLE IF EXISTS poetry")
    cursor.execute("DROP TABLE IF EXISTS poetry_fts")
    
    cursor.execute("""
    CREATE TABLE poetry (
        id TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        dynasty TEXT,
        content_json TEXT,
        layout_strategy TEXT,
        tags TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE VIRTUAL TABLE poetry_fts USING fts5(
        id UNINDEXED,
        title,
        author,
        search_text,
        tokenize='unicode61 remove_diacritics 0'
    );
    """)
    conn.commit()

def generate_id(title, author, content_json_str):
    """Generate deterministic ID using Title + Author + Content Snippet."""
    try:
        content_obj = json.loads(content_json_str)
        lines = []
        if 'paragraphs' in content_obj and content_obj['paragraphs']:
            lines = content_obj['paragraphs'][0].get('lines', [])
        snippet = "".join(lines)[:30]
    except:
        snippet = ""
        
    raw = f"{title.strip()}|{author.strip()}|{snippet}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def import_file(conn, file_path):
    print(f"Processing {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return
        
    cursor = conn.cursor()
    batch_size = 5000
    batch_poetry = []
    batch_fts = []
    
    for item in data:
        tags_str = json.dumps(item.get('tags', []), ensure_ascii=False)
        content_json_val = item.get('content_json', '{}')
        if not isinstance(content_json_val, str):
            content_json_val = json.dumps(content_json_val, ensure_ascii=False)

        # FTS5 & ID Logic
        search_text = item.get('search_text', '')
        if not search_text:
            content_plain = item.get('content', '')
            if isinstance(content_plain, list):
                content_plain = "".join(str(x) for x in content_plain)
            if not content_plain:
                try:
                    cobj = json.loads(content_json_val)
                    lines = []
                    if 'paragraphs' in cobj:
                        for p in cobj['paragraphs']:
                            lines.extend(p.get('lines', []))
                    content_plain = "".join(lines)
                except:
                    pass
            search_text = build_search_text(item['title'], item['author'], content_plain)

        new_id = generate_id(item['title'], item['author'], content_json_val)

        p_record = (
            new_id,
            item['title'],
            item['author'],
            item['dynasty'],
            content_json_val,
            item['layout_strategy'],
            tags_str,
            item.get('source', '')
        )

        fts_record = (
            new_id,
            item['title'],
            item['author'],
            search_text
        )
        
        batch_poetry.append(p_record)
        batch_fts.append(fts_record)
        
        if len(batch_poetry) >= batch_size:
            cursor.executemany("INSERT OR REPLACE INTO poetry (id, title, author, dynasty, content_json, layout_strategy, tags, source) VALUES (?,?,?,?,?,?,?,?)", batch_poetry)
            cursor.executemany("INSERT OR REPLACE INTO poetry_fts (id, title, author, search_text) VALUES (?,?,?,?)", batch_fts)
            conn.commit()
            batch_poetry = []
            batch_fts = []
            print(f"  Processed chunk of {batch_size}...")
            
    if batch_poetry:
        cursor.executemany("INSERT OR REPLACE INTO poetry (id, title, author, dynasty, content_json, layout_strategy, tags, source) VALUES (?,?,?,?,?,?,?,?)", batch_poetry)
        cursor.executemany("INSERT OR REPLACE INTO poetry_fts (id, title, author, search_text) VALUES (?,?,?,?)", batch_fts)
        conn.commit()
    
    print(f"Imported {len(data)} records from {os.path.basename(file_path)}")

def optimize_db(conn):
    print("Optimizing database (VACUUM)...")
    conn.execute("VACUUM")
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM poetry")
    print(f"Total records in poetry: {cursor.fetchone()[0]}")
    cursor.execute("SELECT count(*) FROM poetry_fts")
    print(f"Total records in poetry_fts: {cursor.fetchone()[0]}")

def main():
    parser = argparse.ArgumentParser(description="Build LiuMo V8.0 Database")
    parser.add_argument("--type", choices=['lite', 'full'], required=True, help="Build type: lite or full")
    parser.add_argument("--base_dir", default="assets/final", help="Base directory for assets")
    parser.add_argument("--output_dir", default="output", help="Output directory")
    args = parser.parse_args()
    
    if args.type == 'lite':
        input_dir = os.path.join(args.base_dir, "lite")
        db_name = "core.db"
    else:
        input_dir = os.path.join(args.base_dir, "full")
        db_name = "full.db"
        
    output_path = os.path.join(args.output_dir, db_name)
    print(f"Building [{args.type.upper()}] database...")
    print(f"Input: {input_dir}")
    print(f"Output: {output_path}")
    
    conn = create_connection(output_path)
    if not conn: return
    setup_schema(conn)
    
    input_path = Path(input_dir)
    if not input_path.is_dir():
        print(f"Invalid input directory: {input_path}")
        return

    all_files = sorted(input_path.rglob("*.json"))
    files_to_process = []
    
    # Identify part files
    part_files_map = {}
    for f in all_files:
        if '_part' in f.name:
            prefix = f.name.split('_part')[0] + '.json'
            part_files_map[prefix] = True
            
    for f in all_files:
        if f.name == 'build_stats.json': continue
        if f.name in part_files_map:
            print(f"Skipping merged file {f.name} because parts exist.")
            continue
        files_to_process.append(f)

    if not files_to_process:
        print(f"No JSON files found in {input_path}")
    else:
        for f in files_to_process:
            import_file(conn, str(f))
        
    optimize_db(conn)
    conn.close()
    print(f"Done. Generated {output_path}")

if __name__ == '__main__':
    main()
