import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

# Import the cleaner script (assuming it's in scripts/ai_cleaner.py)
# We need to add the parent directory to sys.path to import it
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

# Mocking modules before import if necessary, but here we can just import
from ai_cleaner import Cleaner

class TestCleaner(unittest.TestCase):
    def test_preprocessing(self):
        cleaner = Cleaner()
        
        # Test case
        item = {
            "id": "test_001",
            "title": "Test Poem",
            "author": "先秦：左丘明",
            "content": ["第一行", "第二行"]
        }
        
        # We want to verify the prompt construction logic inside clean_item
        # Since clean_item is async and calls API, we'll patch the API call part
        
        # But wait, logic is inside clean_item. Let's extract preprocessing if possible, 
        # or just mock the session.post to capture the payload.
        
        pass

# Since refactoring the script is better, let's just write a small script that
# imports specific functions if they were separated. 
# As they are monolithic, I will create a test that mocks aiohttp.ClientSession.

async def run_test():
    cleaner = Cleaner()
    
    # Mock item
    item = {
        "id": "test_001",
        "title": "Test Poem",
        "author": "先秦：左丘明", 
        "content": ["Line 1", "Line 2"]
    }
    
    # Mock response
    mock_response_data = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "layout_strategy": "FLOW_VIRTUAL",
                    "content_json": "{}",
                    "display_content": "Processed Content",
                    "tags": ["Tag1"],
                    "search_content": "Searchable"
                })
            }
        }]
    }
    
    # Mock Context Manager for session.post
    mock_resp = MagicMock()
    mock_resp.status = 200
    
    async def mock_json():
        return mock_response_data
    
    mock_resp.json = mock_json
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.__aexit__.return_value = None
    
    mock_post = MagicMock()
    mock_post.return_value = mock_resp
    
    cleaner.session = MagicMock()
    cleaner.session.post = mock_post
    
    # Run
    result = await cleaner.clean_item(item)
    
    # Verify
    print("Result:", json.dumps(result, ensure_ascii=False, indent=2))
    
    # Assertions
    assert result['author'] == "左丘明"
    assert result['layout_strategy'] == "FLOW_VIRTUAL"
    assert result['tags'] == '["Tag1"]'
    
    # Verify Payload sent to API
    call_args = mock_post.call_args
    sent_json = call_args[1]['json']
    user_content = sent_json['messages'][1]['content']
    
    print("\nSent Prompt Content:\n", user_content)
    assert "Author: 左丘明" in user_content
    assert "Line 1\nLine 2" in user_content

if __name__ == "__main__":
    asyncio.run(run_test())
