import openai
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def make_single_request(client, request_id):
    """执行单个请求"""
    print(f"\n--- Request {request_id}/40 ---")
    
    request_start_time = time.time()
    response = client.chat.completions.create(
        model="openai/qwen3-0-6b",
        stream=True,
        messages=[
            {
                "role": "user",
                "content": "Hello, how are you today?"
            }
        ],
        extra_body={             # provider-specific param 向下游透传
            "enable_thinking": False,
        },
        max_tokens=256,
        temperature=0,
    )

    full_content = ""
    raw_response = None
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            full_content += chunk.choices[0].delta.content
        raw_response = chunk

    # 打印x-litellm-model-id header
    if raw_response and hasattr(raw_response, '_raw_response'):
        raw = raw_response._raw_response
        if hasattr(raw, 'headers') and "x-litellm-model-id" in raw.headers:
            print(raw.headers["x-litellm-model-id"])

    request_end_time = time.time()
    request_duration = request_end_time - request_start_time

    # 截取内容前200个字符
    truncated_content = full_content[:200] if len(full_content) > 200 else full_content
    
    # 打印原始JSON结构（模拟最后一个chunk的结构）
    print("Response JSON structure:")
    response_json = {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion.chunk",
        "created": 1234567890,
        "model": "openai/qwen3-30b",
        "choices": [
            {
                "index": 0,
                "delta": {
                    "content": truncated_content
                },
                "finish_reason": "stop"
            }
        ]
    }
    print(json.dumps(response_json, indent=2, ensure_ascii=False))
    print(f"Content (first 200 chars): {truncated_content}")
    print(f"Request {request_id} duration: {request_duration:.3f}s")
    
    return request_duration

def test_openai_client_simple():
    client = openai.OpenAI(
        api_key="sk-Zd7gzQGylVwOyUUMvOBhow",
        base_url="http://172.16.0.120:4000"
    )

    total_start_time = time.time()
    request_times = []

    # 使用线程池执行40个请求，最多5个并发
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交40个任务
        futures = [executor.submit(make_single_request, client, i+1) for i in range(40)]
        
        # 收集结果
        for future in as_completed(futures):
            try:
                duration = future.result()
                request_times.append(duration)
            except Exception as e:
                print(f"Request failed: {e}")

    # 计算并打印性能统计
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    #Total requests: 40
    #Concurrent workers: 5
    #Total time: 19.168s
    #Average time per request: 2.279s
    #Min request time: 0.822s
    #Max request time: 2.714s
    #Requests per second: 2.09

    #Total requests: 40
    #Concurrent workers: 5
    #Total time: 15.409s
    #Average time per request: 1.820s
    #Min request time: 0.701s
    #Max request time: 3.062s
    #Requests per second: 2.60

    print(f"\n{'='*50}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*50}")
    print(f"Total requests: 40")
    print(f"Concurrent workers: 5")
    print(f"Total time: {total_duration:.3f}s")
    print(f"Average time per request: {sum(request_times)/len(request_times):.3f}s")
    print(f"Min request time: {min(request_times):.3f}s")
    print(f"Max request time: {max(request_times):.3f}s")
    print(f"Requests per second: {40/total_duration:.2f}")

if __name__ == "__main__":
    test_openai_client_simple()