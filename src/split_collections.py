import json
import os
import re

RAW_DIR = "assets/raw"
OUTPUT_DIR = "assets/raw" # Output back to raw, but different files

# Reuse the map from audit script
POET_MAP = {
    "宋": [
        "苏轼", "陆游", "辛弃疾", "李清照", "文天祥", "杨万里", "范成大", "朱熹", "黄庭坚", "秦观",
        "柳永", "晏殊", "欧阳修", "王安石", "晏几道", "周邦彦", "贺铸", "姜夔", "吴文英", "张元干",
        "张孝祥", "叶梦得", "蒋捷", "史达祖", "岳飞", "曾几", "吕本中", "陈与义", "汪元量", "郑思肖",
        "林逋", "邵雍", "司马光", "范仲淹", "梅尧臣", "苏舜钦", "魏夫人", "朱淑真", "王禹偁", "苏辙",
        "苏洵", "晁补之", "张耒", "戴复古", "刘克庄", "谢枋得", "刘辰翁", "陈师道", "张先", "王沂孙",
        "张炎", "高观国", "卢梅坡", "严羽", "郑清之", "林景熙", "王十朋", "刘过", "严濑", "谢逸",
        "宋徽宗", "赵佶", "赵匡胤", "李煜", "李璟" # 包含部分五代/宋初
    ],
    "元": [
        "马致远", "关汉卿", "白朴", "郑光祖", "张养浩", "萨都剌", "元好问", "赵孟頫", "王冕", "杨载",
        "虞集", "揭傒斯", "范梈", "张可久", "乔吉", "贯云石", "鲜于枢", "姚燧", "卢挚", "睢景臣",
        "冯子振", "倪瓒", "杨维桢", "王实甫", "张鸣善", "徐再思", "汪元亨", "薛昂夫", "戴表元"
    ]
}

AUTHOR_FIX_MAP = {}
for dyn, poets in POET_MAP.items():
    for p in poets:
        AUTHOR_FIX_MAP[p] = dyn

def clean_author_name(name):
    return re.sub(r'^.*?[：·【】]', '', name).strip()

def split_collections():
    print("开始拆分数据集...")
    
    # Buckets
    buckets = {
        "tang": [],
        "song_shi": [],
        "yuan_shi": [],
        "fragments": [],
        "other": []
    }
    
    files = [f for f in os.listdir(RAW_DIR) if f.startswith("tang_part") and f.endswith(".json")]
    total_processed = 0
    
    for f in files:
        path = os.path.join(RAW_DIR, f)
        print(f"Processing {f}...")
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            continue
            
        items = data if isinstance(data, list) else data.get('content', [])
        
        for item in items:
            total_processed += 1
            author = clean_author_name(item.get("author", ""))
            title = item.get("title", "")
            
            # 1. Fragments
            if title == "句" or (title == "无题" and len(item.get("paragraphs", [])) < 2):
                item["tags"] = ["fragment"]
                buckets["fragments"].append(item)
                continue
            
            # 2. Dynasty Check
            dynasty = "tang" # default
            if author in AUTHOR_FIX_MAP:
                target = AUTHOR_FIX_MAP[author]
                if target == "宋":
                    dynasty = "song_shi"
                    item["dynasty"] = "宋"
                elif target == "元":
                    dynasty = "yuan_shi"
                    item["dynasty"] = "元"
            
            # 3. Add to bucket
            buckets[dynasty].append(item)
            
    # Save buckets
    print(f"\n拆分完成。总处理: {total_processed}")
    for key, items in buckets.items():
        if not items: continue
        
        # 对于 tang，我们覆盖原来的 tang_part*.json 吗？
        # 为了安全，我们生成新的 consolidated 文件。
        # tang_shi.json, song_shi.json ...
        
        filename = f"{key}.json"
        if key == "tang": filename = "tang_shi.json"
        
        out_path = os.path.join(OUTPUT_DIR, filename)
        print(f"Saving {len(items)} items to {filename}...")
        
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            
    print("\n注意：原始的 tang_part*.json 文件仍然存在，建议手动删除或归档，以免重复构建。")

if __name__ == "__main__":
    split_collections()
