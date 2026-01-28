#!/usr/bin/env python3
"""测试 token 计数问题"""
import json
import httpx
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

endpoint = config['endpoint']
api_key = config['api_key']
model = config['model']

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}',
    'api-key': api_key
}

body = {
    'model': model,
    'input': 'Say hello in 5 words',
    'stream': True,
    'reasoning': {'effort': 'high'},
    'store': False
}

completion_tokens = 0
content_chunks = []

print("Testing token extraction from streaming response...")

with httpx.Client(timeout=3600) as client:
    with client.stream('POST', endpoint, headers=headers, json=body) as response:
        for line in response.iter_lines():
            if not line or not line.startswith('data: '):
                continue
            data_str = line[6:]
            if data_str.strip() == '[DONE]':
                break
            try:
                chunk = json.loads(data_str)
                chunk_type = chunk.get('type', '')
                
                if chunk_type == 'response.output_text.delta':
                    delta = chunk.get('delta', '')
                    if delta:
                        content_chunks.append(delta)
                        
                elif chunk_type == 'response.completed':
                    print(f"\n=== response.completed event ===")
                    resp = chunk.get('response', {})
                    usage = resp.get('usage', {})
                    
                    print(f"chunk.keys(): {list(chunk.keys())}")
                    print(f"chunk.get('response') exists: {'response' in chunk}")
                    print(f"resp.keys(): {list(resp.keys())}")
                    print(f"usage: {usage}")
                    
                    if usage:
                        completion_tokens = usage.get('output_tokens', 0)
                        print(f"Extracted output_tokens: {completion_tokens}")
                    else:
                        print("WARNING: usage is empty!")
                        
            except Exception as e:
                print(f"Error: {e}")

full_content = "".join(content_chunks)
print(f"\n=== Final Results ===")
print(f"completion_tokens: {completion_tokens}")
print(f"content length: {len(full_content)} chars")
print(f"content preview: {full_content[:100]}...")
