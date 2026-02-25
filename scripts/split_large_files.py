import json
import os
import math

def split_json(file_path, chunk_size_mb=45):
    """Split a JSON array file into chunks smaller than chunk_size_mb"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Calculate approximate chunk size in items based on file size
    file_size = os.path.getsize(file_path)
    total_items = len(data)
    # Estimate size per item to verify chunking
    avg_item_size = file_size / total_items if total_items > 0 else 0
    
    # Target size per chunk (bytes)
    target_bytes = chunk_size_mb * 1024 * 1024
    
    num_chunks = math.ceil(file_size / target_bytes)
    # Recalculate based on item count to ensure even distribution
    items_per_chunk = math.ceil(total_items / num_chunks)
    
    base_name, ext = os.path.splitext(file_path)
    
    print(f"Splitting {file_path} ({file_size/1024/1024:.1f}MB) into {num_chunks} parts...")
    
    for i in range(num_chunks):
        start = i * items_per_chunk
        end = min((i + 1) * items_per_chunk, total_items)
        chunk = data[start:end]
        
        output_path = f"{base_name}_part{i+1:03d}{ext}"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        print(f"  Created {output_path} ({len(chunk)} items)")
    
    print("Split complete. Original file kept (add to .gitignore).")

if __name__ == "__main__":
    split_json("liumo-assets-prep/assets/final/full/tang_shi.json")
