import json
import os
import re
from collections import defaultdict, Counter

RAW_DIR = "assets/raw"
OUTPUT_REPORT = "assets/patches/dynasty_audit_report.json"

# 权威白名单 (由 Librarian 提供)
POET_MAP = {
    "宋": [
        "苏轼", "陆游", "辛弃疾", "李清照", "文天祥", "杨万里", "范成大", "朱熹", "黄庭坚", "秦观",
        "柳永", "晏殊", "欧阳修", "王安石", "晏几道", "周邦彦", "贺铸", "姜夔", "吴文英", "张元干",
        "张孝祥", "叶梦得", "蒋捷", "史达祖", "岳飞", "曾几", "吕本中", "陈与义", "汪元量", "郑思肖",
        "林逋", "邵雍", "司马光", "范仲淹", "梅尧臣", "苏舜钦", "魏夫人", "朱淑真", "王禹偁", "苏辙",
        "苏洵", "晁补之", "张耒", "戴复古", "刘克庄", "谢枋得", "刘辰翁", "陈师道", "张先", "王沂孙",
        "张炎", "高观国", "卢梅坡", "严羽", "郑清之", "林景熙", "王十朋", "刘过", "严濑", "谢逸",
        "宋徽宗", "赵佶" # 补充皇帝
    ],
    "元": [
        "马致远", "关汉卿", "白朴", "郑光祖", "张养浩", "萨都剌", "元好问", "赵孟頫", "王冕", "杨载",
        "虞集", "揭傒斯", "范梈", "张可久", "乔吉", "贯云石", "鲜于枢", "姚燧", "卢挚", "睢景臣",
        "冯子振", "倪瓒", "杨维桢", "王实甫", "张鸣善", "徐再思", "汪元亨", "薛昂夫", "戴表元"
    ]
}

# 扁平化映射: Author -> Correct Dynasty
AUTHOR_FIX_MAP = {}
for dyn, poets in POET_MAP.items():
    for p in poets:
        AUTHOR_FIX_MAP[p] = dyn

def clean_author_name(name):
    # 移除 "唐·", "宋：", "【宋】" 等前缀
    return re.sub(r'^.*?[：·【】]', '', name).strip()

def audit_files():
    print("开始全量数据朝代审计...")
    files = [f for f in os.listdir(RAW_DIR) if f.startswith("tang_part") and f.endswith(".json")]
    
    report = {
        "summary": {
            "total_scanned": 0,
            "dynasty_mismatches": 0,
            "fragments_found": 0,
            "author_format_issues": 0
        },
        "details": {
            "song_poets_found": Counter(),
            "yuan_poets_found": Counter(),
            "fragments_sample": [],
            "author_format_sample": []
        }
    }
    
    for f in files:
        path = os.path.join(RAW_DIR, f)
        print(f"Scanning {f}...")
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            continue
            
        items = data if isinstance(data, list) else data.get('content', [])
        
        for idx, item in enumerate(items):
            report["summary"]["total_scanned"] += 1
            
            raw_author = item.get("author", "")
            title = item.get("title", "")
            current_dynasty = item.get("dynasty", "唐") # 默认为唐，因为文件叫 tang_part
            
            # 1. 检查作者格式
            clean_author = clean_author_name(raw_author)
            if clean_author != raw_author:
                report["summary"]["author_format_issues"] += 1
                if len(report["details"]["author_format_sample"]) < 10:
                    report["details"]["author_format_sample"].append(raw_author)
            
            # 2. 检查残卷
            if title == "句" or title == "无题" and len(item.get("paragraphs", [])) < 2:
                report["summary"]["fragments_found"] += 1
                # 不记录 sample 了，太多了
                
            # 3. 检查朝代错乱
            if clean_author in AUTHOR_FIX_MAP:
                correct = AUTHOR_FIX_MAP[clean_author]
                if current_dynasty != correct and current_dynasty != f"【{correct}】":
                    report["summary"]["dynasty_mismatches"] += 1
                    
                    if correct == "宋":
                        report["details"]["song_poets_found"][clean_author] += 1
                    elif correct == "元":
                        report["details"]["yuan_poets_found"][clean_author] += 1

    # 打印结果
    print("\n审计完成。结果摘要：")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    
    print("\n发现最多的误标宋代诗人：")
    print(report["details"]["song_poets_found"].most_common(10))
    
    print("\n发现最多的误标元代诗人：")
    print(report["details"]["yuan_poets_found"].most_common(10))
    
    # 保存报告
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n完整报告已保存至 {OUTPUT_REPORT}")

if __name__ == "__main__":
    audit_files()
