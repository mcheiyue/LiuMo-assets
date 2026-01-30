import json
import os
import re

DATA_DIRS = [
    "data/cleaned/tang_300",
    "data/cleaned/k12"
]
# Song300 默认为词，不参与此规则（或者单独处理）

def clean_text(text):
    """移除标点符号，只保留汉字"""
    return re.sub(r'[^\u4e00-\u9fa5]', '', text)

def classify_poem(content, default_type="shi"):
    if not content:
        return default_type
        
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    if not lines:
        return default_type
        
    # 计算每行字数（去标点）
    lengths = [len(clean_text(l)) for l in lines]
    if not lengths:
        return default_type
        
    unique_lens = set(lengths)
    line_count = len(lines)
    
    # 绝句与律诗判断
    if len(unique_lens) == 1:
        char_per_line = list(unique_lens)[0]
        
        if char_per_line == 5:
            if line_count == 4: return "五言绝句"
            if line_count == 8: return "五言律诗"
            return "五言古诗" # 包括排律
            
        if char_per_line == 7:
            if line_count == 4: return "七言绝句"
            if line_count == 8: return "七言律诗"
            return "七言古诗" # 包括排律
            
    # 如果不是标准格式，统称为乐府/古风
    # 简单起见，如果这里是Tang300，可以标为"乐府"或"古风"
    # 为了保险，检查标题是否含"歌"、"行"、"引"、"曲"、"吟"
    return "乐府" # 泛指非格律诗

def get_broad_type(chinese_type):
    if "绝句" in chinese_type or "律诗" in chinese_type or "古诗" in chinese_type or "乐府" in chinese_type:
        return "shi"
    if "词" in chinese_type: return "ci"
    if "曲" in chinese_type: return "qu"
    if "文" in chinese_type: return "wen"
    return "shi" # 默认

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        item = json.load(f)
        
    # 如果是宋词，跳过或强制为词
    if "song_300" in filepath:
        new_type = "词"
    else:
        # 基于内容自动分类
        new_type = classify_poem(item.get("display_content", item.get("content", "")))
    
    item["type"] = new_type
    
    # 更新 tags
    if "tags" not in item:
        item["tags"] = []
    
    # 添加新的中文类型标签
    if new_type not in item["tags"]:
        item["tags"].append(new_type)
        
    # 额外：如果标题包含"歌行"，添加标签
    if any(x in item["title"] for x in ["歌", "行", "引", "曲", "吟"]):
        if "乐府" not in item["tags"]:
            item["tags"].append("乐府")
            
    # 【关键修复】确保添加英文大类标签，以便前端筛选
    broad_type = get_broad_type(new_type)
    if broad_type not in item["tags"]:
        item["tags"].append(broad_type)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(item, f, ensure_ascii=False, indent=2)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(item, f, ensure_ascii=False, indent=2)

def main():
    print("开始智能分类与标准化...")
    count = 0
    
    # 处理唐诗和K12
    for d in DATA_DIRS:
        if not os.path.exists(d): continue
        for f in os.listdir(d):
            if f.endswith(".json"):
                process_file(os.path.join(d, f))
                count += 1
                
    # 单独处理宋词（全部设为词）
    song_dir = "data/cleaned/song_300"
    if os.path.exists(song_dir):
        for f in os.listdir(song_dir):
            if f.endswith(".json"):
                process_file(os.path.join(song_dir, f))
                count += 1
                
    print(f"完成！已重新分类 {count} 首诗词。")
    print("分类标准：")
    print("- 5言x4句 -> 五言绝句")
    print("- 7言x4句 -> 七言绝句")
    print("- 5言x8句 -> 五言律诗")
    print("- 7言x8句 -> 七言律诗")
    print("- 其他 -> 乐府/古诗/词")

if __name__ == "__main__":
    main()
