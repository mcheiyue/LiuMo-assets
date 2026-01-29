import asyncio
import json
import os
import sys
import time
import logging
import aiohttp
from typing import List, Dict, Set

# Configuration
API_BASE = "http://127.0.0.1:8045/v1"
API_KEY = "sk-3da733f9cd824f1b9ad4137cf80cac39"  # Local proxy doesn't verify key, but header required
MODEL = "gemini-3-flash"
CONCURRENCY = 15
INPUT_DIRS = ["data/other", "data/modern"]
OUTPUT_DIR = "data/cleaned"
PROGRESS_FILE = "data/progress.json"
BATCH_SIZE = 50

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("cleaner.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

class Cleaner:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(CONCURRENCY)
        self.completed_ids: Set[str] = set()
        self.buffer: List[Dict] = []
        self.total_processed = 0
        self.session = None

    def load_progress(self):
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.completed_ids = set(data.get("completed_ids", []))
                    self.total_processed = len(self.completed_ids)
                logger.info(f"Loaded progress: {self.total_processed} items completed.")
            except Exception as e:
                logger.error(f"Failed to load progress: {e}")

    def save_progress(self):
        try:
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "completed_ids": list(self.completed_ids),
                    "timestamp": time.time()
                }, f)
            logger.info(f"Progress saved. Total: {len(self.completed_ids)}")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    async def clean_item(self, item: Dict) -> Dict:
        item_id = item.get("id")
        title = item.get("title", "Untitled")
        
        # 1. Pre-processing
        # Fix Author: "先秦：左丘明" -> "左丘明"
        raw_author = item.get("author", "")
        author = raw_author.split("：")[-1] if "：" in raw_author else raw_author
        
        # Fix Content: Array to String
        raw_content = item.get("content", [])
        if isinstance(raw_content, list):
            content_text = "\n".join(raw_content)
        else:
            content_text = str(raw_content)

        # 2. Construct Prompt
        user_prompt = f"""
Title: {title}
Author: {author}
Content:
{content_text}

请分析并返回 JSON。
"""
        
        system_prompt = """你是一个精通中国古诗文、书法排版和历史文献的专家。
你的任务是将输入的诗词文本进行“纠错、定性、结构化”处理。
请返回如下 JSON 格式（不要包含 Markdown 代码块）：
{
  "layout_strategy": "GRID_STANDARD" (绝句/律诗) | "FLOW_VIRTUAL" (词/曲/文),
  "content_json": "{\"title\":\"...\",\"body\":[...]}", 
  "display_content": "排版后的纯文本",
  "tags": ["标签1", "标签2"],
  "search_content": "用于搜索的文本"
}"""

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }

        # 3. Call API with Retry
        async with self.semaphore:
            retries = 3
            for attempt in range(retries):
                try:
                    async with self.session.post(f"{API_BASE}/chat/completions", json=payload, headers={"Authorization": f"Bearer {API_KEY}"}) as resp:
                        if resp.status != 200:
                            logger.warning(f"API Error {resp.status} for {item_id}, retrying...")
                            await asyncio.sleep(5)
                            continue
                        
                        result = await resp.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Parse JSON from LLM response
                        try:
                            # Strip markdown blocks if present
                            if "```json" in content:
                                content = content.split("```json")[1].split("```")[0].strip()
                            elif "```" in content:
                                content = content.split("```")[1].split("```")[0].strip()
                                
                            cleaned_data = json.loads(content)
                            
                            # Merge back to item
                            item.update({
                                "layout_strategy": cleaned_data.get("layout_strategy"),
                                "content_json": cleaned_data.get("content_json"),
                                "display_content": cleaned_data.get("display_content"),
                                "tags": json.dumps(cleaned_data.get("tags", [])), # Store as string
                                "search_content": cleaned_data.get("search_content"),
                                # Update pre-processed fields
                                "author": author 
                            })
                            return item
                            
                        except json.JSONDecodeError:
                            logger.error(f"JSON Parse Error for {item_id}: {content[:50]}...")
                            return None

                except Exception as e:
                    logger.error(f"Network Error for {item_id}: {e}")
                    await asyncio.sleep(5)
            
            return None

    async def worker(self, queue):
        while True:
            item = await queue.get()
            try:
                if item['id'] in self.completed_ids:
                    queue.task_done()
                    continue

                cleaned_item = await self.clean_item(item)
                
                if cleaned_item:
                    # Save individual file
                    dataset = item.get('source_dataset', 'unknown')
                    out_dir = os.path.join(OUTPUT_DIR, dataset)
                    os.makedirs(out_dir, exist_ok=True)
                    
                    with open(os.path.join(out_dir, f"{item['id']}.json"), 'w', encoding='utf-8') as f:
                        json.dump(cleaned_item, f, ensure_ascii=False, indent=2)
                    
                    self.completed_ids.add(item['id'])
                    
                    # Periodic save
                    if len(self.completed_ids) % BATCH_SIZE == 0:
                        self.save_progress()

            except Exception as e:
                logger.error(f"Worker Error: {e}")
            finally:
                queue.task_done()

    async def main(self):
        self.load_progress()
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            queue = asyncio.Queue()

            # Load Tasks
            logger.info("Loading datasets...")
            count = 0
            for root_dir in INPUT_DIRS:
                if not os.path.exists(root_dir): continue
                for file in os.listdir(root_dir):
                    if not file.endswith('.json'): continue
                    
                    dataset_name = file.replace('.json', '')
                    filepath = os.path.join(root_dir, file)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Handle different structures (list or dict wrapper)
                            items = data if isinstance(data, list) else data.get('content', [])
                            
                            for item in items:
                                if item['id'] not in self.completed_ids:
                                    item['source_dataset'] = dataset_name
                                    queue.put_nowait(item)
                                    count += 1
                    except Exception as e:
                        logger.error(f"Error loading {file}: {e}")
            
            logger.info(f"Loaded {count} items to process.")

            # Start Workers
            workers = [asyncio.create_task(self.worker(queue)) for _ in range(CONCURRENCY)]
            
            # Wait for queue to empty
            await queue.join()
            
            # Cancel workers
            for w in workers: w.cancel()
            
            self.save_progress()
            logger.info("All tasks completed.")

if __name__ == "__main__":
    cleaner = Cleaner()
    asyncio.run(cleaner.main())
