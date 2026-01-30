import json
import os
import shutil
import re
from collections import defaultdict

# 配置路径
DATA_DIR = "data"
SOURCE_DIR = "assets/raw"
OUTPUT_BASE = "data/curated"

# 索引文件
INDEX_FILES = {
    "k12": "assets/indices/k12_index.json",
    "tang_300": "assets/indices/tang300_index.json",
    "song_300": "assets/indices/song300_index.json"
}

# 作者别名/映射表
AUTHOR_ALIASES = {
    "曹操": ["佚名", "魏武帝"],
    "汉乐府": ["佚名", "无名氏", "郭茂倩"],
    "北朝民歌": ["佚名", "无名氏"],
    "佚名": ["无名氏"],
    "无名氏": ["佚名"],
    "李桥": ["李峤"], # 修正错别字
    "陶渊明": ["陶潜"],
    "陶潜": ["陶渊明"],
    "辛弃疾": ["辛稼轩"],
    "苏轼": ["苏东坡"],
    "王安石": ["王荆公"],
}

T2S_MAP = {}

def load_t2s_map():
    """加载简繁转换表"""
    global T2S_MAP
    map_file = "assets/indices/STCharacters.txt"
    if not os.path.exists(map_file):
        print("Warning: STCharacters.txt not found, skipping T2S conversion.")
        return

    print("Loading T2S map...")
    try:
        with open(map_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    simp = parts[0]
                    trads = parts[1].split(' ')
                    for trad in trads:
                        T2S_MAP[trad] = simp
    except Exception as e:
        print(f"Error loading T2S map: {e}")
    print(f"Loaded {len(T2S_MAP)} T2S mappings.")

def to_simp(text):
    """繁体转简体"""
    if not text: return ""
    return "".join([T2S_MAP.get(c, c) for c in text])

def normalize_author(author):
    if not author: return "Unknown"
    # 先做简繁转换
    author = to_simp(author)
    # 移除常见朝代前缀和标点 (唐·李白, 宋：苏轼, 两汉：诸葛亮)
    import re
    return re.sub(r'^.*?[：·]', '', author).strip()

def normalize_content(content):
    if isinstance(content, list):
        return "\n".join(content)
    return str(content)

def clean_title_for_fuzzy(title):
    """生成用于模糊匹配的标题键"""
    if not title: return ""
    # 1. 转简体
    title = to_simp(title)
    # 2. 移除括号及内容（通常是注释）
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'（.*?）', '', title)
    # 3. 移除特定后缀
    suffixes = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
                "之一", "之二", "之三", "之四", "之五",
                "节选", "选", "·"]
    for s in suffixes:
        title = title.replace(s, "")
    # 4. 移除所有非汉字字符（标点、空格、数字等）
    # \u4e00-\u9fff 是常用汉字范围
    title = re.sub(r'[^\u4e00-\u9fff]', '', title)
    return title

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def build_lookup_table():
    """建立全量数据的查找表"""
    print("正在建立全量数据索引...")
    # Exact match: (author, title) -> [entries]
    exact_lookup = defaultdict(list)
    # Fuzzy match: (author, fuzzy_title) -> [entries]
    fuzzy_lookup = defaultdict(list)
    # Author index: author -> list of entries (for fallback scan)
    author_lookup = defaultdict(list)
    
    files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".json")]
    total_scanned = 0
    
    # 优先加载 manual_supplement.json
    manual_path = "assets/patches/manual_supplement.json"
    if os.path.exists(manual_path):
        print("Loading manual supplement data...")
        data = load_json(manual_path)
        # 将其视为一个普通文件，但给予优先权（因为先处理，append 到 list 前面？）
        # 不，append 是往后加。exact_lookup[key][0] 取的是第一个。
        # 所以我们应该先处理 manual，让它占据 index 0。
        files.insert(0, manual_path) # 但 manual_path 不在 SOURCE_DIR，得特殊处理
    
    # 我们把 manual_path 放到一个单独的循环里先处理
    if os.path.exists(manual_path):
        data = load_json(manual_path)
        # manual_supplement is a list
        items = data
        for item in items:
            raw_author = item.get('author')
            raw_title = item.get('title', '')
            raw_rhythmic = item.get('rhythmic', '')

            author = normalize_author(raw_author)
            title = to_simp(raw_title).strip()
            rhythmic = to_simp(raw_rhythmic).strip()
            
            entry = {
                "source_file": "manual_supplement.json",
                "data": item,
                "clean_title": title,
                "is_manual": True 
            }
            
            # Author Index
            author_lookup[author].insert(0, entry) # Insert at beginning

            # Title Indexing
            if title:
                exact_lookup[(author, title)].insert(0, entry)
                fuzzy_key = clean_title_for_fuzzy(title)
                if fuzzy_key:
                    fuzzy_lookup[(author, fuzzy_key)].insert(0, entry)
            
            # Rhythmic
            if rhythmic and rhythmic != title:
                exact_lookup[(author, rhythmic)].insert(0, entry)
                fuzzy_key_r = clean_title_for_fuzzy(rhythmic)
                if fuzzy_key_r:
                    fuzzy_lookup[(author, fuzzy_key_r)].insert(0, entry)
        print(f"手动补丁已加载，共 {len(items)} 条。")

    for f in files:
        if f == manual_path: continue # Skip if we hacked it into the list
        path = os.path.join(SOURCE_DIR, f)
        data = load_json(path)
        items = data if isinstance(data, list) else data.get('content', [])
        
        for item in items:
            raw_author = item.get('author')
            raw_title = item.get('title', '')
            raw_rhythmic = item.get('rhythmic', '') # 宋词词牌

            author = normalize_author(raw_author)
            title = to_simp(raw_title).strip()
            rhythmic = to_simp(raw_rhythmic).strip()
            
            entry = {
                "source_file": f,
                "data": item,
                "clean_title": title
            }
            
            # 1. Author Index
            author_lookup[author].append(entry)

            # 2. Title Indexing
            if title:
                exact_lookup[(author, title)].append(entry)
                fuzzy_key = clean_title_for_fuzzy(title)
                if fuzzy_key:
                    fuzzy_lookup[(author, fuzzy_key)].append(entry)
            
            # 3. Rhythmic Indexing (for Ci)
            if rhythmic and rhythmic != title:
                exact_lookup[(author, rhythmic)].append(entry)
                fuzzy_key_r = clean_title_for_fuzzy(rhythmic)
                if fuzzy_key_r:
                    fuzzy_lookup[(author, fuzzy_key_r)].append(entry)
                
        total_scanned += len(items)
        
    print(f"索引建立完成，扫描了 {total_scanned} 首诗词。")
    return exact_lookup, fuzzy_lookup, author_lookup

def find_best_match(t_author, t_title, exact_lookup, fuzzy_lookup, author_lookup):
    # 候选标题列表（处理 "A / B" 这种情况）
    candidate_titles = [t.strip() for t in t_title.split('/')]
    
    # 候选作者列表
    candidate_authors = [t_author]
    if t_author in AUTHOR_ALIASES:
        candidate_authors.extend(AUTHOR_ALIASES[t_author])
        
    # 1. 精确匹配 & 2. 模糊匹配 (Key lookup)
    for auth in candidate_authors:
        for tit in candidate_titles:
            # Exact
            key = (auth, tit)
            if key in exact_lookup:
                return exact_lookup[key][0]['data']
            
            # Fuzzy
            f_key = (auth, clean_title_for_fuzzy(tit))
            if f_key in fuzzy_lookup:
                return fuzzy_lookup[f_key][0]['data']

    # 3. 深度扫描 (Deep Scan) - 在候选作者的所有作品中查找
    # 这是一个比较耗时的操作，但对于几百首的目标集合是可以接受的
    for auth in candidate_authors:
        candidates = author_lookup.get(auth)
        if not candidates: continue
        
        for tit in candidate_titles:
            clean_target = clean_title_for_fuzzy(tit)
            if not clean_target: continue
            
            best_cand = None
            max_score = 0
            
            for cand_entry in candidates:
                cand_clean = clean_title_for_fuzzy(cand_entry['clean_title'])
                if not cand_clean: continue
                
                # 策略A: 包含关系 (Target 包含 Candidate 或 Candidate 包含 Target)
                # 且长度差异不大
                if (clean_target in cand_clean) or (cand_clean in clean_target):
                    # 避免 "春" 匹配 "春晓" 这种太短的误判
                    # 要求重叠部分至少占较短者的 60% (实际上包含就是100%)
                    # 这里主要防范的是 clean_target 只有1个字的情况
                    if len(clean_target) < 2 and clean_target != cand_clean:
                        continue
                        
                    # 优先选择长度差异最小的
                    diff = abs(len(cand_clean) - len(clean_target))
                    score = 100 - diff
                    
                    # 特例：如果是组诗（包含"其"），优先匹配
                    if "其" in cand_entry['clean_title']: 
                         # 这里其实 logic 稍微复杂，因为 fuzzy title 已经去掉了 "其"
                         # 但我们可以检查原始 title
                         pass
                         
                    if score > max_score:
                        max_score = score
                        best_cand = cand_entry['data']
            
            if best_cand:
                return best_cand
                    
    return None

def process_dataset(dataset_name, index_file, lookups):
    exact_lookup, fuzzy_lookup, author_lookup = lookups
    print(f"\n开始处理数据集: {dataset_name} ...")
    
    index_data = load_json(index_file)
    items = index_data.get('content', index_data) if isinstance(index_data, dict) else index_data
    
    extracted_count = 0
    missing_count = 0
    
    missing_log_path = os.path.join(DATA_DIR, f"{dataset_name}_missing.txt")
    missing_list = []

    output_dir = os.path.join(OUTPUT_BASE, dataset_name, "raw")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    for target in items:
        # 获取目标信息
        t_author_raw = target.get('author')
        t_title_raw = target.get('title', target.get('rhythmic', ''))
        
        t_author = normalize_author(t_author_raw)
        t_title = to_simp(t_title_raw).strip()
        
        match = find_best_match(t_author, t_title, exact_lookup, fuzzy_lookup, author_lookup)
        
        if not match:
            missing_count += 1
            missing_list.append(f"{t_title} - {t_author}")
            continue
            
        # 数据清洗与标准化
        clean_item = {
            "title": t_title, # 使用目标集中的标题，保证一致性
            "author": t_author,
            "dynasty": target.get('dynasty', match.get('dynasty', 'Unknown')),
            "content": normalize_content(match.get('content', '')),
            "type": match.get('type', 'Unknown'),
            "tags": [],
            "source": dataset_name,
            # 保留一些原始信息用于调试
            "original_title": match.get('title', '')
        }
        
        # 强制修正朝代和标签
        if dataset_name == "tang_300":
            clean_item["dynasty"] = "唐"
            clean_item["tags"].append("唐诗三百首")
        elif dataset_name == "song_300":
            clean_item["dynasty"] = "宋"
            clean_item["tags"].append("宋词三百首")
            clean_item["type"] = "词"
        elif dataset_name == "k12":
            clean_item["tags"].append("K12")
            if 'dynasty' in target:
                clean_item["dynasty"] = target['dynasty']

        # 文件名处理
        safe_title = "".join(x for x in t_title if x.isalnum() or x in ('·', ' ', '_'))
        if len(safe_title) > 50: safe_title = safe_title[:50]
        
        filename = f"{t_author}_{safe_title}.json"
        
        # 防止重名覆盖
        counter = 1
        while os.path.exists(os.path.join(output_dir, filename)):
            filename = f"{t_author}_{safe_title}_{counter}.json"
            counter += 1
        
        with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(clean_item, f, ensure_ascii=False, indent=2)
            
        extracted_count += 1
        
    with open(missing_log_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(missing_list))
        
    print(f"完成 {dataset_name}: 提取 {extracted_count} 首，缺失 {missing_count} 首。详见 {missing_log_path}")

def main():
    if not os.path.exists(DATA_DIR):
        print(f"错误: 找不到数据目录 {DATA_DIR}")
        return
        
    load_t2s_map()
    lookups = build_lookup_table()
    
    for name, path in INDEX_FILES.items():
        if os.path.exists(path):
            process_dataset(name, path, lookups)
        else:
            print(f"索引文件不存在: {path}")

if __name__ == "__main__":
    main()
