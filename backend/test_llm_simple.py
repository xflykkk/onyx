#!/usr/bin/env python3
"""
Simple test script to diagnose LLM timeout issues without complex dependencies.
"""

import os
import time
import asyncio
from datetime import datetime
import threading
from typing import Any

# Test the timeout mechanism directly
class TimeoutError(Exception):
    pass

def run_with_timeout(timeout_seconds, func, *args, **kwargs):
    """Simple timeout wrapper similar to the one in onyx"""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        # Thread is still running, timeout occurred
        raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]

def simulate_fast_llm_call(delay_seconds=5):
    """Simulate an LLM call that takes a certain amount of time"""
    print(f"Simulating LLM call with {delay_seconds} second delay...")
    time.sleep(delay_seconds)
    return f"Response after {delay_seconds} seconds"

def test_openai_connection():
    """Test actual OpenAI connection if API key is available"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("No OPENAI_API_KEY found, skipping OpenAI test")
        return False
    
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        print("Testing OpenAI connection...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Please respond with exactly 'OK'"}
            ],
            max_tokens=10,
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"OpenAI call successful! Duration: {duration:.3f} seconds")
        print(f"Response: {response.choices[0].message.content}")
        
        return True, duration
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"OpenAI call failed after {duration:.3f} seconds: {e}")
        return False, duration

def test_document_verification_call():
    """Test a document verification call with realistic content"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("No OPENAI_API_KEY found, skipping document verification test")
        return False
    
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        # Use the same prompt as verify_documents
        prompt = """
/no_think.Determine whether the following document text contains data or information that is potentially relevant for a question. It does not have to be fully relevant, but check whether it has some information that would help - possibly in conjunction with other documents - to address the question.

Be careful that you do not use a document where you are not sure whether the text applies to the objects or entities that are relevant for the question. For example, a book about chess could have long passage discussing the psychology of chess without - within the passage - mentioning chess. If now a question is asked about the psychology of football, one could be tempted to use the document as it does discuss psychology in sports. However, it is NOT about football and should not be deemed relevant. Please consider this logic.

DOCUMENT TEXT:
-------
Paris is the capital and largest city of France. It is situated on the Seine River, in northern France, at the heart of the Île-de-France region. The city is known for its art, fashion, gastronomy, and culture. Paris is home to many world-famous landmarks including the Eiffel Tower, Louvre Museum, Notre-Dame Cathedral, and the Arc de Triomphe.
-------

Do you think that this document text is useful and relevant to answer the following question?

QUESTION:
-------
What is the capital of France?
-------

Please answer with exactly and only a 'yes' or 'no'. Do NOT include any other text in your response:

Answer:
"""
        
        print("Testing document verification call...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Document verification call successful! Duration: {duration:.3f} seconds")
        print(f"Response: {response.choices[0].message.content}")
        
        return True, duration
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"Document verification call failed after {duration:.3f} seconds: {e}")
        return False, duration

def test_timeout_scenarios():
    """Test various timeout scenarios"""
    
    # Test 1: Function that completes within timeout
    print("\n=== Test 1: Function completes within timeout ===")
    try:
        start_time = time.time()
        result = run_with_timeout(10, simulate_fast_llm_call, 3)
        end_time = time.time()
        duration = end_time - start_time
        print(f"✓ Success: {result} (Duration: {duration:.3f}s)")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 2: Function that times out
    print("\n=== Test 2: Function times out ===")
    try:
        start_time = time.time()
        result = run_with_timeout(5, simulate_fast_llm_call, 8)
        end_time = time.time()
        duration = end_time - start_time
        print(f"✓ Unexpected success: {result} (Duration: {duration:.3f}s)")
    except TimeoutError as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"✓ Expected timeout: {e} (Duration: {duration:.3f}s)")
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"✗ Unexpected error: {e} (Duration: {duration:.3f}s)")
    
    # Test 3: Test with 8-second timeout (same as verify_documents)
    print("\n=== Test 3: 8-second timeout (same as verify_documents) ===")
    try:
        start_time = time.time()
        result = run_with_timeout(8, simulate_fast_llm_call, 10)
        end_time = time.time()
        duration = end_time - start_time
        print(f"✓ Unexpected success: {result} (Duration: {duration:.3f}s)")
    except TimeoutError as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"✓ Expected timeout: {e} (Duration: {duration:.3f}s)")
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"✗ Unexpected error: {e} (Duration: {duration:.3f}s)")

def main():
    """Run all tests"""
    print("=== Starting Simple LLM Timeout Tests ===")
    print(f"Current timestamp: {datetime.now()}")
    
    # Test timeout mechanism
    print("\n" + "="*50)
    test_timeout_scenarios()
    
    # Test OpenAI connection
    print("\n" + "="*50)
    print("=== Testing OpenAI Connection ===")
    success, duration = test_openai_connection()
    if success:
        print(f"✓ OpenAI connection test passed ({duration:.3f}s)")
    else:
        print(f"✗ OpenAI connection test failed")
    
    # Test document verification
    print("\n" + "="*50)
    print("=== Testing Document Verification Call ===")
    success, duration = test_document_verification_call()
    if success:
        print(f"✓ Document verification test passed ({duration:.3f}s)")
    else:
        print(f"✗ Document verification test failed")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()