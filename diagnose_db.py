import sqlite3
import os

DB_PATH = 'liumo_full.db'

def diagnose():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Force UTF-8 for output
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("=== 1. 核心诗人检查 (Missing Top Poets) ===")
    top_poets = ['李白', '王维', '孟浩然', '杜牧', '李商隐', '杜甫', '白居易']
    for poet in top_poets:
        cursor.execute("SELECT COUNT(*) FROM poetry WHERE author = ?", (poet,))
        count = cursor.fetchone()[0]
        status = "[EXIST]" if count > 0 else "[MISSING]"
        print(f"{poet}: {count} 首 - {status}")

    print("\n=== 2. 朝代错乱检查 (Dynasty Mismatch) ===")
    # 检查被标记为“唐”及其变体的非唐代诗人
    suspicious_cases = [
        ('陆游', '宋'), ('苏轼', '宋'), ('范成大', '宋'), 
        ('文天祥', '宋'), ('朱熹', '宋'), ('戴表元', '元')
    ]
    
    print("检查被错误标记为 '唐' (包含 'Tang') 的非唐代诗人:")
    for author, actual_dynasty in suspicious_cases:
        # 查找该作者被标记为含有 'Tang' 或 '唐' 的记录
        cursor.execute("""
            SELECT COUNT(*), dynasty FROM poetry 
            WHERE author = ? AND (dynasty LIKE '%唐%' OR dynasty LIKE '%Tang%')
            GROUP BY dynasty
        """, (author,))
        results = cursor.fetchall()
        if results:
            for count, dyn in results:
                print(f"[WARN] {author} ({actual_dynasty}) -> 被标为 '{dyn}': {count} 首")
        else:
            print(f"[OK] {author} 未发现被标为唐代")

    print("\n=== 3. 朝代完整性检查 (Dynasty Coverage) ===")
    dynasties = ['明', 'Ming', '清', 'Qing', '宋', 'Song', '元', 'Yuan']
    print("统计各朝代记录数:")
    for dyn in dynasties:
        cursor.execute("SELECT COUNT(*) FROM poetry WHERE dynasty LIKE ?", (f'%{dyn}%',))
        count = cursor.fetchone()[0]
        print(f"朝代 '{dyn}': {count} 首")

    print("\n=== 4. Content 格式抽样 (Content Format Sample) ===")
    cursor.execute("SELECT id, title, content FROM poetry LIMIT 3")
    rows = cursor.fetchall()
    for r in rows:
        print(f"ID: {r[0]}, Title: {r[1]}")
        print(f"Content (前100字): {r[2][:100]!r}")
        print("-" * 20)

    print("\n=== 5. 体裁分布检查 (Genre Distribution) ===")
    cursor.execute("SELECT type, COUNT(*) FROM poetry GROUP BY type")
    results = cursor.fetchall()
    for genre, count in results:
        print(f"体裁 '{genre}': {count} 首")

    print("\n=== 6. 特定作者体裁检查 (Author Genre Check) ===")
    target_authors = ['苏轼', '李白', '柳永', '关汉卿']
    for author in target_authors:
        print(f"--- {author} ---")
        cursor.execute("SELECT type, COUNT(*) FROM poetry WHERE author = ? GROUP BY type", (author,))
        res = cursor.fetchall()
        for g, c in res:
            print(f"  {g}: {c} 首")

    print("\n=== 7. 特殊体裁探测 (Special Genre Probe) ===")
    # 检查诗经、楚辞是否有独立标识
    special_titles = ['离骚', '关雎', '硕鼠']
    for title in special_titles:
        cursor.execute("SELECT title, author, dynasty, type FROM poetry WHERE title = ?", (title,))
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f"  {r[0]} ({r[1]}/{r[2]}) -> type: '{r[3]}'")
        else:
            print(f"  {title}: [NOT FOUND]")

    conn.close()


if __name__ == '__main__':
    diagnose()
