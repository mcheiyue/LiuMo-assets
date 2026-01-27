import sqlite3
import json
import os
import glob
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DB = os.path.join(BASE_DIR, 'liumo_full.db')

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS poetry (
        id TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        dynasty TEXT,
        content TEXT,
        type TEXT
    )
    ''')
    conn.commit()

def build():
    if os.path.exists(OUTPUT_DB):
        os.remove(OUTPUT_DB)
        
    conn = sqlite3.connect(OUTPUT_DB)
    init_db(conn)
    cursor = conn.cursor()
    
    print(f'Building database from {DATA_DIR}...')
    
    count = 0
    # Walk through all json files
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if not file.endswith('.json'):
                continue
                
            path = os.path.join(root, file)
            # Derive info from path? e.g. shi/tang.json
            # Actually data is self-contained in JSON usually, or we infer
            
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    items = json.load(f)
                    if not isinstance(items, list):
                        continue
                        
                    for item in items:
                        # Ensure content is JSON string if it's a list
                        content_val = item.get('content')
                        if isinstance(content_val, list):
                            content_val = json.dumps(content_val, ensure_ascii=False)
                        
                        cursor.execute('''
                        INSERT OR IGNORE INTO poetry (id, title, author, dynasty, content, type)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            item.get('id'),
                            item.get('title'),
                            item.get('author'),
                            item.get('dynasty'),
                            content_val,
                            item.get('type')
                        ))
                        count += 1
                except Exception as e:
                    print(f'Error reading {file}: {e}')
    
    conn.commit()
    conn.close()
    print(f'✅ Database built successfully! Total records: {count}')

if __name__ == '__main__':
    build()
