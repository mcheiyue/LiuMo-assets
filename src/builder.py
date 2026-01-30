import sqlite3
import json
import os
import argparse
from pathlib import Path

# === 配置 ===
DB_PATH = "dist/liumo_v8.db"
DEFAULT_INPUT = "assets/final/full"

def create_connection(db_file):
    """创建数据库连接"""
    conn = None
    try:
        # 确保目录存在
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
    
    # 1. 主数据表
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
    
    # 2. FTS5 全文索引表
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
        
        # Ensure content_json is a string
        content_json_val = item.get('content_json', '{}')
        if not isinstance(content_json_val, str):
            content_json_val = json.dumps(content_json_val, ensure_ascii=False)

        p_record = (
            item['id'],
            item['title'],
            item['author'],
            item['dynasty'],
            content_json_val,
            item['layout_strategy'],
            tags_str,
            item.get('source', '')
        )
        
        # search_text might need to be constructed if missing, but V8 pipeline should have it.
        # Fallback just in case, though schema says it should be there.
        search_text = item.get('search_text', '')
        if not search_text:
            # Simple fallback construction
            content_plain = item.get('content', '')
            search_text = f"{item['title']} {item['author']} {content_plain}" 

        fts_record = (
            item['id'],
            item['title'],
            item['author'],
            search_text
        )
        
        batch_poetry.append(p_record)
        batch_fts.append(fts_record)
        
        if len(batch_poetry) >= batch_size:
            cursor.executemany("INSERT INTO poetry (id, title, author, dynasty, content_json, layout_strategy, tags, source) VALUES (?,?,?,?,?,?,?,?)", batch_poetry)
            cursor.executemany("INSERT INTO poetry_fts (id, title, author, search_text) VALUES (?,?,?,?)", batch_fts)
            conn.commit()
            batch_poetry = []
            batch_fts = []
            print(f"  Processed chunk of {batch_size}...")
            
    if batch_poetry:
        cursor.executemany("INSERT INTO poetry (id, title, author, dynasty, content_json, layout_strategy, tags, source) VALUES (?,?,?,?,?,?,?,?)", batch_poetry)
        cursor.executemany("INSERT INTO poetry_fts (id, title, author, search_text) VALUES (?,?,?,?)", batch_fts)
        conn.commit()
    
    print(f"Imported {len(data)} records from {os.path.basename(file_path)}")

def optimize_db(conn):
    print("Optimizing database...")
    conn.execute("VACUUM")
    
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM poetry")
    count = cursor.fetchone()[0]
    print(f"Total records in poetry: {count}")
    
    cursor.execute("SELECT count(*) FROM poetry_fts")
    count_fts = cursor.fetchone()[0]
    print(f"Total records in poetry_fts: {count_fts}")

def main():
    parser = argparse.ArgumentParser(description="Build LiuMo V8.0 Database")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input JSON file or directory")
    parser.add_argument("--output", default=DB_PATH, help="Output SQLite DB path")
    args = parser.parse_args()
    
    print(f"Building database to {args.output} from {args.input}...")
    
    conn = create_connection(args.output)
    if not conn:
        return
        
    setup_schema(conn)
    
    input_path = Path(args.input)
    if input_path.is_dir():
        files = sorted(input_path.glob("*.json"))
        if not files:
            print(f"No JSON files found in {input_path}")
        for f in files:
            import_file(conn, str(f))
    elif input_path.is_file():
        import_file(conn, str(input_path))
    else:
        print(f"Invalid input: {args.input}")
        
    optimize_db(conn)
    conn.close()
    print("Done.")

if __name__ == '__main__':
    main()
