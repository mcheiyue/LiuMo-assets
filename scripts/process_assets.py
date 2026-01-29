import argparse
import json
import os
import sys
import asyncio
import logging
import aiohttp
from typing import Set, Tuple, List, Dict

# Configuration
API_BASE = "http://127.0.0.1:8045/v1"
API_KEY = "sk-3da733f9cd824f1b9ad4137cf80cac39"
MODEL = "gemini-3-flash"
CONCURRENCY = 15
INPUT_DIRS = ["data/other", "data/modern"]
OUTPUT_DIR = "data/processed" # Changed from 'cleaned' to 'processed'
K12_INDEX_FILE = "data/k12_index.json"

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class AssetProcessor:
    def __init__(self, mode: str, dataset_filter: str = None):
        self.mode = mode
        self.dataset_filter = dataset_filter
        self.k12_set: Set[Tuple[str, str]] = set()
        self.semaphore = asyncio.Semaphore(CONCURRENCY)
        self.session = None
        
        self.load_k12_index()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def load_k12_index(self):
        if os.path.exists(K12_INDEX_FILE):
            try:
                with open(K12_INDEX_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        self.k12_set.add((item['title'], item['author']))
                logger.info(f"Loaded {len(self.k12_set)} K12 index items.")
            except Exception as e:
                logger.error(f"Failed to load K12 index: {e}")

    def preprocess(self, item: Dict) -> Dict:
        # 1. Fix Author
        raw_author = item.get("author", "")
        if "：" in raw_author:
            item["author"] = raw_author.split("：")[-1]
            
        # 2. Fix Content (Array -> String)
        raw_content = item.get("content", [])
        if isinstance(raw_content, list):
            item["content"] = "\n".join(raw_content)
            
        return item

    def categorize(self, item: Dict) -> Dict:
        tags = set(item.get("tags", []))
        
        # Check K12
        if (item.get("title"), item.get("author")) in self.k12_set:
            tags.add("K12")
            tags.add("必背")
            
        # Dataset specific tags
        source = item.get("source_dataset", "")
        if "tang" in source:
            tags.add("唐诗")
        elif "song" in source:
            tags.add("宋词")
        elif "meng_xue" in source:
            tags.add("蒙学")
            tags.add("K12") # Assume all MengXue is K12 base
            
        item["tags"] = list(tags)
        return item

    async def ai_clean(self, item: Dict) -> Dict:
        if self.mode != "ai-clean":
            return item

        # Construct prompt (Simplified for this script)
        user_prompt = f"Title: {item['title']}\nContent: {item['content']}"
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Return JSON with: layout_strategy, content_json, display_content, tags."},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        
        async with self.semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=60)
                async with self.session.post(f"{API_BASE}/chat/completions", json=payload, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=timeout) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        content = res['choices'][0]['message']['content']
                        # Simple parse logic (omitted for brevity, assume valid JSON)
                        # In production, use the robust parsing from ai_cleaner.py
                        # Here we just mock it for demonstration if needed, 
                        # or actually parse it if we had the robust logic.
                        # For now, let's assume we update the item with AI results.
                        pass
                    else:
                        logger.warning(f"AI Failed: {resp.status}")
            except Exception as e:
                logger.error(f"Network Error: {e}")
                
        return item

    async def process_one(self, item: Dict):
        item = self.preprocess(item)
        item = self.categorize(item)
        
        if self.mode == "ai-clean":
            item = await self.ai_clean(item)
        else:
            # For dry-run, fill schema defaults
            item["layout_strategy"] = "GRID_STANDARD"
            item["content_json"] = json.dumps({"body": item["content"].split("\n")}, ensure_ascii=False)
            item["display_content"] = item["content"]
            item["search_content"] = item["content"]

        # Save
        dataset = item.get("source_dataset", "unknown")
        out_dir = os.path.join(OUTPUT_DIR, dataset)
        os.makedirs(out_dir, exist_ok=True)
        
        with open(os.path.join(out_dir, f"{item['id']}.json"), 'w', encoding='utf-8') as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

    async def main(self):
        async with aiohttp.ClientSession() as session:
            self.session = session
            tasks = []
            
            count = 0
            for root_dir in INPUT_DIRS:
                if not os.path.exists(root_dir): continue
                for file in os.listdir(root_dir):
                    if not file.endswith('.json'): continue
                    
                    dataset_name = file.replace('.json', '')
                    if self.dataset_filter and self.dataset_filter != dataset_name:
                        continue
                        
                    filepath = os.path.join(root_dir, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        items = data if isinstance(data, list) else data.get('content', [])
                        
                        for item in items:
                            item['source_dataset'] = dataset_name
                            tasks.append(self.process_one(item))
                            count += 1
            
            logger.info(f"Processing {len(tasks)} items in mode: {self.mode}...")
            # Use gather for concurrency
            # Chunk tasks to avoid memory explosion if list is huge
            chunk_size = 1000
            for i in range(0, len(tasks), chunk_size):
                await asyncio.gather(*tasks[i:i+chunk_size])
                logger.info(f"Processed {min(i+chunk_size, len(tasks))}/{len(tasks)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dry-run", "ai-clean"], default="dry-run")
    parser.add_argument("--dataset", help="Filter dataset")
    args = parser.parse_args()
    
    processor = AssetProcessor(args.mode, args.dataset)
    asyncio.run(processor.main())
