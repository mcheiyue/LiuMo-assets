import os
import json
from collections import Counter, defaultdict

INPUT_DIRS = ["data/other", "data/modern"]

def analyze():
    stats = {
        "files": 0,
        "total_poems": 0,
        "datasets": Counter(),
        "authors": Counter(),
        "dynasties": Counter(),
        "tags_distribution": Counter(),
        "k12_candidates": 0
    }
    
    k12_keywords = ["小学", "初中", "高中", "必背", "课本", "教材"]
    
    for root_dir in INPUT_DIRS:
        if not os.path.exists(root_dir): continue
        
        for file in os.listdir(root_dir):
            if not file.endswith('.json'): continue
            
            filepath = os.path.join(root_dir, file)
            dataset = file.replace('.json', '')
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Handle structure variations
                    items = data if isinstance(data, list) else data.get('content', [])
                    
                    stats["files"] += 1
                    stats["datasets"][dataset] = len(items)
                    
                    for item in items:
                        stats["total_poems"] += 1
                        
                        # Author stats
                        author = item.get("author", "Unknown")
                        stats["authors"][author] += 1
                        
                        # Dynasty stats
                        dynasty = item.get("dynasty", "Unknown")
                        stats["dynasties"][dynasty] += 1
                        
                        # Tags stats
                        tags = item.get("tags", [])
                        if isinstance(tags, list):
                            for tag in tags:
                                stats["tags_distribution"][tag] += 1
                                if any(k in tag for k in k12_keywords):
                                    stats["k12_candidates"] += 1
                                    
                        # Content check (K12 keyword in abstract/notes?)
                        # This is a heuristic check
                        
            except Exception as e:
                print(f"Error reading {file}: {e}")

    print("=== Data Analysis Report ===")
    print(f"Total Files: {stats['files']}")
    print(f"Total Poems: {stats['total_poems']}")
    print(f"\nDataset Distribution:")
    for ds, count in stats["datasets"].most_common():
        print(f"  - {ds}: {count}")
        
    print(f"\nK12 Candidates (based on tags): {stats['k12_candidates']}")
    
    print(f"\nTop Tags:")
    for tag, count in stats["tags_distribution"].most_common(10):
        print(f"  - {tag}: {count}")

    print(f"\nTop Dynasties:")
    for dyn, count in stats["dynasties"].most_common(10):
        print(f"  - {dyn}: {count}")

if __name__ == "__main__":
    analyze()
