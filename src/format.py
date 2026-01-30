import json
import os

DATASETS = ["k12", "tang_300", "song_300"]
RAW_BASE = "data/curated"
CLEAN_BASE = "data/cleaned"

def determine_layout(lines, type_hint):
    if not lines: return "CENTER_ALIGNED"
    
    # 移除标点计算字数
    def clean_len(s):
        return len(''.join(c for c in s if '\u4e00' <= c <= '\u9fff'))
    
    lengths = [clean_len(l) for l in lines]
    unique_lens = set(lengths)
    
    # 强制规则
    if "词" in type_hint or "曲" in type_hint:
        return "FLOW_VARYING"
    
    # 绝句律诗判断
    if len(unique_lens) == 1 and list(unique_lens)[0] in [5, 7]:
        if len(lines) <= 16: # 绝句(4) 律诗(8) 稍微放宽
            return "GRID_STANDARD"
            
    # 杂言
    return "CENTER_ALIGNED"

def process_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_item = json.load(f)
        
    content_str = raw_item.get("content", "")
    # 处理可能的数组格式
    if isinstance(content_str, list):
        lines = [str(l).strip() for l in content_str if str(l).strip()]
        content_str = "\n".join(lines)
    else:
        lines = [l.strip() for l in str(content_str).split("\n") if l.strip()]
    
    layout = determine_layout(lines, raw_item.get("type", "Unknown"))
    
    # 构建 content_json
    content_structure = {
        "paragraphs": [
            {
                "type": "main",
                "lines": lines
            }
        ]
    }
    
    # 更新字段
    clean_item = raw_item.copy()
    clean_item["content"] = content_str # 规范化为字符串
    clean_item["layout_strategy"] = layout
    clean_item["content_json"] = json.dumps(content_structure, ensure_ascii=False)
    clean_item["display_content"] = content_str
    
    # 确保 tags
    if "tags" not in clean_item:
        clean_item["tags"] = []
    if raw_item.get("type") and raw_item["type"] != "Unknown":
        if raw_item["type"] not in clean_item["tags"]:
            clean_item["tags"].append(raw_item["type"])
            
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(clean_item, f, ensure_ascii=False, indent=2)

def main():
    print("开始启发式数据清洗...")
    total_processed = 0
    
    for ds in DATASETS:
        raw_dir = os.path.join(RAW_BASE, ds, "raw")
        clean_dir = os.path.join(CLEAN_BASE, ds)
        
        if not os.path.exists(raw_dir):
            continue
            
        os.makedirs(clean_dir, exist_ok=True)
        
        files = [f for f in os.listdir(raw_dir) if f.endswith(".json")]
        print(f"处理 {ds}: {len(files)} 个文件")
        
        for f in files:
            process_file(os.path.join(raw_dir, f), os.path.join(clean_dir, f))
            total_processed += 1
            
    print(f"清洗完成！共处理 {total_processed} 个文件。")

if __name__ == "__main__":
    main()
