import json
import os

SOURCE_DIR = "data/cleaned"
OUTPUT_DIR = "data/dist"
DATASETS = ["k12", "tang_300", "song_300"]

def consolidate(dataset):
    src_path = os.path.join(SOURCE_DIR, dataset)
    if not os.path.exists(src_path):
        print(f"Skipping {dataset}, path not found.")
        return

    all_items = []
    files = [f for f in os.listdir(src_path) if f.endswith(".json")]
    print(f"Consolidating {dataset}: {len(files)} files...")

    for f in files:
        with open(os.path.join(src_path, f), 'r', encoding='utf-8') as file:
            item = json.load(file)
            all_items.append(item)
    
    # Sort by ID or Title
    all_items.sort(key=lambda x: x.get("id", x.get("title", "")))

    output_file = os.path.join(OUTPUT_DIR, f"{dataset}.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    
    print(f"Saved to {output_file} ({len(all_items)} records)")

def main():
    for ds in DATASETS:
        consolidate(ds)

if __name__ == "__main__":
    main()
