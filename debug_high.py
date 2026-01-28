#!/usr/bin/env python3
"""调试 High 模式 API 响应"""
import json
import httpx
import yaml

# 加载配置
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
    'input': '生成一个日历应用的代码示例，使用 Python 和 Tkinter 库。',
    'stream': True,
    'reasoning': {'effort': 'high'},
    'store': False
}

print('=== 请求体 ===')
print(json.dumps(body, indent=2, ensure_ascii=False))
print()
print('=== SSE 事件流 ===')

event_types = {}
content_events = []

with httpx.Client(timeout=3600) as client:
    with client.stream('POST', endpoint, headers=headers, json=body) as response:
        print(f'HTTP Status: {response.status_code}')
        print()
        
        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith('data: '):
                data_str = line[6:]
                if data_str.strip() == '[DONE]':
                    print('>>> [DONE]')
                    break
                try:
                    chunk = json.loads(data_str)
                    event_type = chunk.get('type', 'unknown')
                    event_types[event_type] = event_types.get(event_type, 0) + 1
                    
                    # 打印关键事件
                    if event_type == 'response.output_text.delta':
                        delta = chunk.get('delta', '')
                        content_events.append(delta)
                        if len(content_events) <= 3:
                            print(f'[{event_type}] delta: {repr(delta[:50])}...')
                    elif event_type == 'response.completed':
                        resp = chunk.get('response', {})
                        output = resp.get('output', [])
                        usage = resp.get('usage', {})
                        print(f'[{event_type}]')
                        print(f'  usage: {usage}')
                        print(f'  output items: {len(output)}')
                        for i, item in enumerate(output[:5]):
                            item_type = item.get('type')
                            content = item.get('content', [])
                            print(f'  output[{i}]: type={item_type}, content_len={len(content)}')
                            if item_type == 'reasoning' and 'summary' in item:
                                print(f'    reasoning summary: {item.get("summary", [])[:2]}...')
                    elif sum(event_types.values()) <= 15:
                        print(f'[{event_type}] {json.dumps(chunk, ensure_ascii=False)[:120]}...')
                except json.JSONDecodeError as e:
                    print(f'JSON Error: {e}')

print()
print('=== 事件统计 ===')
for k, v in sorted(event_types.items()):
    print(f'{k}: {v}')
print()
print(f'content_events 总数: {len(content_events)}')
print(f'总内容长度: {sum(len(c) for c in content_events)} 字符')
