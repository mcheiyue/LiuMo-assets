
import json
import hashlib
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple

# === 配置 ===
PROJECT_ROOT = Path(__file__).parent.parent
CLEANED_DIR = PROJECT_ROOT / 'assets/cleaned'
DIST_DIR = PROJECT_ROOT / 'assets/final/lite' # Use new lite as dist source if needed, or remove dist layer logic?
# Actually, dist layer logic in script used assets/dist which we deleted.
# But assets/final/lite contains k12.json etc.
# The script logic: cleaned -> dist -> raw.
# Now that we generated final, running it again using final as input is circular?
# No, we should probably comment out DIST_DIR logic or point it to nothing if we deleted the source.
# Wait, assets/dist was "Curated JSONs". We deleted them because assets/final/lite replaced them.
# BUT if we want to re-run the script from scratch, we need the source.
# Did we lose data by deleting assets/dist?
# assets/final/lite is the RESULT of processing assets/dist.
# So assets/final/lite IS the new source of truth for lite data?
# Yes.
# So for future runs, we might not need a "dist" layer, or we treat "lite" as "cleaned".
# Let's simplify: CLEANED_DIR points to assets/cleaned.
# DIST_DIR logic... we deleted the folder.
# So I should remove the DIST_DIR logic from script or update it.
# I will update CLEANED_DIR and empty DIST_DIR logic to avoid error.
RAW_DIR = PROJECT_ROOT / 'assets/raw'
OUTPUT_DIR = PROJECT_ROOT / 'assets/final'
STATS_FILE = OUTPUT_DIR / 'build_stats.json'

# === 工具函数 ===

def generate_id(title: str, author: str, content_sample: str = "") -> str:
    """生成确定性ID (加入内容指纹防止同题冲突)"""
    # 取内容前20个字作为指纹
    fingerprint = content_sample[:20] if content_sample else ""
    return hashlib.sha256(f"{title}|{author}|{fingerprint}".encode()).hexdigest()[:16]

def clean_author_field(raw_author: str, raw_dynasty: str) -> Tuple[str, str]:
    """清洗作者字段污染（如"先秦:左丘明"）"""
    if not raw_author:
        return "Unknown", raw_dynasty

    # 匹配模式：朝代:作者 或 朝代：作者
    match = re.match(r'^([^:：]+)[:：]\s*(.+?)\s*$', raw_author)
    
    if match:
        dynasty_prefix = match.group(1).strip()
        author_clean = match.group(2).strip()
        
        # 如果原 dynasty 无效（如"古文", "unknown", ""），使用前缀作为朝代
        # 否则保留原 dynasty（原 dynasty 通常更准确，除非是占位符）
        if not raw_dynasty or raw_dynasty in ['古文', 'unknown', 'None']:
            return author_clean, dynasty_prefix
        return author_clean, raw_dynasty
    
    return raw_author.strip(), raw_dynasty

def normalize_content(content) -> List[str]:
    """统一content为List[str]，并按标点拆分长句"""
    raw_lines = []
    if isinstance(content, list):
        raw_lines = [str(line).strip() for line in content if str(line).strip()]
    elif isinstance(content, str):
        raw_lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    final_lines = []
    for line in raw_lines:
        # 按常见标点拆分，确保每行是一句
        # 保留标点在句尾
        # 使用捕捉组 () 保留分隔符
        parts = re.split(r'([，。！？；])', line)
        current_sentence = ""
        
        for part in parts:
            if not part: continue
            if re.match(r'[，。！？；]', part):
                # 如果是标点，追加到当前句并提交
                if current_sentence:
                    final_lines.append(current_sentence + part)
                    current_sentence = ""
                elif final_lines:
                    # 如果当前句为空（连续标点），追加到上一句
                    final_lines[-1] += part
            else:
                # 如果是文本，开始新句
                current_sentence = part
        
        # 处理末尾剩余文本
        if current_sentence:
            final_lines.append(current_sentence)
            
    return final_lines

def infer_layout_strategy(lines: List[str], type_hint: str) -> str:
    """启发式推断布局策略"""
    if not lines:
        return "CENTER_ALIGNED"
    
    type_hint = str(type_hint).lower()

    # 强制规则：词/曲 -> 流式
    if "词" in type_hint or "曲" in type_hint or type_hint == "ci" or type_hint == "qu":
        return "FLOW_VARYING"
    
    # 强制规则：散文 -> 居中
    if "文" in type_hint or type_hint == "prose":
        return "CENTER_ALIGNED"

    # 计算纯汉字字数（过滤标点）
    def clean_len(s):
        return len(''.join(c for c in s if '\u4e00' <= c <= '\u9fff'))
    
    lengths = [clean_len(l) for l in lines]
    if not lengths:
        return "CENTER_ALIGNED"
        
    unique_lens = set(lengths)
    
    # 格律诗判断：每行字数一致，且为5或7言 (或4言诗经)
    if len(unique_lens) == 1 and list(unique_lens)[0] in [4, 5, 7]:
        # 绝句(4)、律诗(8)、排律(偶数行)
        # 允许稍微长一点的排律，但不允许太长以免是误判
        if len(lines) % 2 == 0 and len(lines) <= 64: 
            return "GRID_STANDARD"

    return "CENTER_ALIGNED"

def generate_content_json(lines: List[str]) -> str:
    """生成 content_json"""
    structure = {
        'paragraphs': [{
            'type': 'main',
            'lines': lines
        }]
    }
    return json.dumps(structure, ensure_ascii=False)

def generate_search_text(lines: List[str]) -> str:
    """生成无标点搜索文本"""
    full_text = ''.join(lines)
    # 只保留中文、字母、数字
    return re.sub(r'[^\w]', '', full_text, flags=re.UNICODE)

def generate_tags(entry: dict) -> List[str]:
    """从type和source生成tags"""
    tags = []
    if 'tags' in entry and isinstance(entry['tags'], list):
        tags = entry['tags'].copy()
    
    # 从 type 生成
    type_val = entry.get('type', '')
    if type_val and type_val != 'Unknown':
        tags.append(type_val)
    
    # 从 source 生成
    source = entry.get('source', '')
    if source == 'k12':
        tags.append('K12')
    elif source == 'tang_300':
        tags.append('唐诗三百首')
    elif source == 'song_300':
        tags.append('宋词三百首')
    
    # 移除空值和重复值
    return list(set([t for t in tags if t]))

def determine_category(entry: dict) -> Tuple[str, str]:
    """确定文件分类路径 (lite/xxx.json 或 full/xxx.json)"""
    source = entry.get('source', '')
    tags = entry.get('tags', [])
    
    # 1. Lite 精选集 (最高优先级)
    if source == 'k12' or 'K12' in tags:
        return 'lite', 'k12.json'
    if source == 'tang_300' or '唐诗三百首' in tags:
        return 'lite', 'tang_300.json'
    if source == 'song_300' or '宋词三百首' in tags:
        return 'lite', 'song_300.json'
        
    # 2. Full 全量集 (按朝代+体裁)
    dynasty = entry.get('dynasty', 'unknown')
    type_val = entry.get('tags', [])[0] if entry.get('tags') else 'poetry' # 粗略取第一个tag作为type
    
    filename = 'other.json'
    
    if dynasty == '唐':
        filename = 'tang_shi.json'
    elif dynasty == '宋':
        if '词' in tags or entry['layout_strategy'] == 'FLOW_VARYING':
            filename = 'song_ci.json'
        else:
            filename = 'song_shi.json'
    elif dynasty == '元':
        filename = 'yuan_qu.json'
    elif dynasty == '清':
        filename = 'qing.json'
    elif dynasty == '明':
        filename = 'ming.json'
    elif dynasty in ['汉', '秦', '先秦', '两汉', '魏晋', '南北朝', '隋']:
        filename = 'pre_tang.json'
    elif dynasty in ['现代', '当代', '近代']:
        filename = 'modern.json'
    
    return 'full', filename

# === 主处理流程 ===

def load_cleaned_layer() -> Dict[str, dict]:
    """Layer 1: 加载 data/cleaned (最高优先级)"""
    print("Loading Layer 1: data/cleaned...")
    dataset = {}
    
    if not CLEANED_DIR.exists():
        print(f"Warning: {CLEANED_DIR} does not exist. Skipping.")
        return dataset

    for file_path in CLEANED_DIR.rglob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            
            # 必须字段检查
            title = entry.get('title', '').strip()
            author = entry.get('author', '').strip()
            if not title or not author:
                continue

            # 补全 V8.0 必需字段
            # 解析 content_json 获取 lines 以生成指纹
            lines = []
            if 'content_json' in entry:
                try:
                    content_struct = json.loads(entry['content_json'])
                    if content_struct.get('paragraphs'):
                        lines = content_struct['paragraphs'][0]['lines']
                except:
                    pass
            if not lines and 'content' in entry:
                lines = normalize_content(entry['content'])

            if 'id' not in entry:
                content_sample = "".join(lines)
                entry['id'] = generate_id(title, author, content_sample)
            
            # 重新生成 layout_strategy (统一逻辑)
            # 解析 content_json 获取 lines
            lines = []
            if 'content_json' in entry:
                try:
                    content_struct = json.loads(entry['content_json'])
                    if content_struct.get('paragraphs'):
                        lines = content_struct['paragraphs'][0]['lines']
                except:
                    pass
            
            # 如果解析失败，尝试回退到 content 字段
            if not lines and 'content' in entry:
                lines = normalize_content(entry['content'])
            
            if not lines:
                continue # 无法获取内容，跳过

            key = f"{title}|{author}|{''.join(lines)[:20]}" # key也需要加入指纹
            entry['_source'] = 'cleaned'
            dataset[key] = entry
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    print(f"  Loaded {len(dataset)} entries from cleaned")
    return dataset

def load_dist_layer(dataset: Dict[str, dict]) -> Dict[str, dict]:
    """Layer 2: (已废弃) assets/dist 已移除"""
    print("Loading Layer 2: Skipped (assets/dist removed)...")
    return dataset

def load_raw_layer(dataset: Dict[str, dict]) -> Dict[str, dict]:
    """Layer 3: 处理 assets/raw (全量补全)"""
    print("Loading Layer 3: assets/raw...")
    added = 0
    skipped = 0
    
    # 遍历 raw 目录下的所有 json 文件
    for file_path in RAW_DIR.glob('*.json'):
        print(f"  Processing {file_path.name}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_entries = json.load(f)
            
            for raw_entry in raw_entries:
                # 1. 数据清洗
                author, dynasty = clean_author_field(
                    raw_entry.get('author', ''),
                    raw_entry.get('dynasty', '')
                )
                
                title = raw_entry.get('title', '').strip()
                
                # 跳过无标题或无作者的无效数据
                if not title or not author:
                    continue

                # 3. 规范化content (提前到这里以便生成ID)
                content_lines = normalize_content(raw_entry.get('content', []))
                if not content_lines:  # 跳过空内容
                    continue

                key = f"{title}|{author}|{''.join(content_lines)[:20]}" # key也需要加入指纹防止去重误杀
                
                # 2. 去重检查
                if key in dataset:
                    skipped += 1
                    continue
                
                # 4. 推断布局策略
                # 尝试从文件名推断 type_hint
                type_hint = raw_entry.get('type', '')
                if not type_hint:
                    if 'ci' in file_path.name: type_hint = 'ci'
                    elif 'shi' in file_path.name: type_hint = 'shi'
                    elif 'qu' in file_path.name: type_hint = 'qu'
                    elif 'wen' in file_path.name: type_hint = 'prose'

                layout_strategy = infer_layout_strategy(
                    content_lines,
                    type_hint
                )
                
                # 5. 构建 V8.0 条目
                v8_entry = {
                    'id': generate_id(title, author, "".join(content_lines)),
                    'title': title,
                    'author': author,
                    'dynasty': dynasty,
                    'layout_strategy': layout_strategy,
                    'content_json': generate_content_json(content_lines),
                    'search_text': generate_search_text(content_lines),
                    'tags': generate_tags(raw_entry),
                    'source': raw_entry.get('source', 'unknown'),
                    '_source': 'raw'
                }
                
                dataset[key] = v8_entry
                added += 1
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    print(f"  Added {added} new entries, skipped {skipped} duplicates")
    return dataset

def main():
    print("=== V8.0 全量数据整合与分包开始 ===")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / 'lite').mkdir(exist_ok=True)
    (OUTPUT_DIR / 'full').mkdir(exist_ok=True)

    # 三层加载
    dataset = {}
    dataset = load_cleaned_layer()
    dataset = load_dist_layer(dataset)
    dataset = load_raw_layer(dataset)
    
    # 统计与分包
    stats = {
        'total': len(dataset),
        'files': {},
        'layout_stats': {
            'GRID_STANDARD': 0, 'FLOW_VARYING': 0, 'CENTER_ALIGNED': 0
        }
    }
    
    file_buffers = {} # path -> list of entries

    print("Categorizing and writing files...")
    
    for entry in dataset.values():
        layout = entry['layout_strategy']
        stats['layout_stats'][layout] += 1
        
        # 移除临时字段
        entry_clean = entry.copy()
        entry_clean.pop('_source', None)
        
        folder, filename = determine_category(entry)
        path = f"{folder}/{filename}"
        
        if path not in file_buffers:
            file_buffers[path] = []
        file_buffers[path].append(entry_clean)

        # 关键修正：如果归类为 Lite，必须同时强制归入 Full，确保 Full 是全集
        if folder == 'lite':
            # 临时移除 source/tags 中的精选集标记，强制触发 Full 归类逻辑
            temp_entry = entry.copy()
            temp_entry['source'] = '' 
            # 注意：不能清空 tags，因为 Full 归类可能依赖 '词' 等 tag
            # 但要移除 'K12' 等精选集 tag 以免 determine_category 再次返回 lite
            temp_entry['tags'] = [t for t in entry.get('tags', []) if t not in ['K12', '唐诗三百首', '宋词三百首']]
            
            # 再次判定
            full_folder, full_filename = determine_category(temp_entry)
            
            # 只有当再次判定结果确实是 full 时才写入（理论上一定是）
            if full_folder == 'full':
                full_path = f"full/{full_filename}"
                if full_path not in file_buffers:
                    file_buffers[full_path] = []
                file_buffers[full_path].append(entry_clean)

    # 写入文件
    for path, entries in file_buffers.items():
        full_path = OUTPUT_DIR / path
        print(f"  Writing {path} ({len(entries)} entries)...")
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        stats['files'][path] = len(entries)
    
    # 保存统计
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 整合完成 ===")
    print(f"总计: {stats['total']} 条")
    print(f"\n布局分布 (验证 GRID 数量):")
    print(f"  - GRID_STANDARD:    {stats['layout_stats']['GRID_STANDARD']}")
    print(f"  - FLOW_VARYING:     {stats['layout_stats']['FLOW_VARYING']}")
    print(f"  - CENTER_ALIGNED:   {stats['layout_stats']['CENTER_ALIGNED']}")
    print(f"\n文件列表:")
    for f, c in stats['files'].items():
        print(f"  - {f}: {c}")

if __name__ == '__main__':
    main()
