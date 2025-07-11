#!/usr/bin/env python3
"""
Test script to simulate verify_documents LLM call and diagnose timeout issues.
"""

import os
import time
from datetime import datetime
from typing import Any

# Add project root to path
import sys
sys.path.insert(0, '/Users/zhuxiaofeng/Github/onyx/backend')

from langchain_core.messages import HumanMessage
from onyx.configs.agent_configs import (
    AGENT_TIMEOUT_LLM_DOCUMENT_VERIFICATION,
    AGENT_TIMEOUT_CONNECT_LLM_DOCUMENT_VERIFICATION,
    AGENT_MAX_TOKENS_VALIDATION,
)
from onyx.llm.factory import get_llms_for_persona
from onyx.utils.threadpool_concurrency import run_with_timeout
from onyx.utils.logger import setup_logger

# Simulate the same prompt used in verify_documents
DOCUMENT_VERIFICATION_PROMPT = """
/no_think.Determine whether the following document text contains data or information that is potentially relevant \
for a question. It does not have to be fully relevant, but check whether it has some information that \
would help - possibly in conjunction with other documents - to address the question.

Be careful that you do not use a document where you are not sure whether the text applies to the objects \
or entities that are relevant for the question. For example, a book about chess could have long passage \
discussing the psychology of chess without - within the passage - mentioning chess. If now a question \
is asked about the psychology of football, one could be tempted to use the document as it does discuss \
psychology in sports. However, it is NOT about football and should not be deemed relevant. Please \
consider this logic.

DOCUMENT TEXT:
-------
{document_content}
-------

Do you think that this document text is useful and relevant to answer the following question?

QUESTION:
-------
{question}
-------

Please answer with exactly and only a 'yes' or 'no'. Do NOT include any other text in your response:

Answer:
""".strip()

logger = setup_logger()

def test_llm_configuration():
    """Test basic LLM configuration"""
    logger.info("=== Testing LLM Configuration ===")
    
    try:
        # Get LLM instances similar to how verify_documents does it
        primary_llm, fast_llm = get_llms_for_persona()
        
        logger.info(f"Primary LLM: {primary_llm}")
        logger.info(f"Fast LLM: {fast_llm}")
        logger.info(f"Fast LLM config: {fast_llm.config}")
        
        return fast_llm
    except Exception as e:
        logger.error(f"Failed to get LLM instances: {e}")
        return None

def test_direct_llm_call(fast_llm):
    """Test direct LLM call without timeout"""
    logger.info("=== Testing Direct LLM Call ===")
    
    # Test data
    test_question = "What is the capital of France?"
    test_document = "Paris is the capital and largest city of France. It is known for its art, fashion, and culture."
    
    # Create message
    msg = [
        HumanMessage(
            content=DOCUMENT_VERIFICATION_PROMPT.format(
                question=test_question,
                document_content=test_document
            )
        )
    ]
    
    try:
        start_time = time.time()
        logger.info("Making direct LLM call...")
        
        response = fast_llm.invoke(
            prompt=msg,
            timeout_override=AGENT_TIMEOUT_CONNECT_LLM_DOCUMENT_VERIFICATION,
            max_tokens=AGENT_MAX_TOKENS_VALIDATION,
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Direct call successful! Duration: {duration:.3f} seconds")
        logger.info(f"Response: {response.content}")
        
        return True, duration
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Direct call failed after {duration:.3f} seconds: {e}")
        return False, duration

def test_timeout_call(fast_llm):
    """Test LLM call with timeout (same as verify_documents)"""
    logger.info("=== Testing LLM Call with Timeout ===")
    
    # Test data
    test_question = "What is the capital of France?"
    test_document = "Paris is the capital and largest city of France. It is known for its art, fashion, and culture."
    
    # Create message
    msg = [
        HumanMessage(
            content=DOCUMENT_VERIFICATION_PROMPT.format(
                question=test_question,
                document_content=test_document
            )
        )
    ]
    
    logger.info(f"Using timeout: {AGENT_TIMEOUT_LLM_DOCUMENT_VERIFICATION} seconds")
    logger.info(f"Connection timeout: {AGENT_TIMEOUT_CONNECT_LLM_DOCUMENT_VERIFICATION} seconds")
    logger.info(f"Max tokens: {AGENT_MAX_TOKENS_VALIDATION}")
    
    try:
        start_time = time.time()
        logger.info("Making timeout-wrapped LLM call...")
        
        response = run_with_timeout(
            AGENT_TIMEOUT_LLM_DOCUMENT_VERIFICATION,
            fast_llm.invoke,
            prompt=msg,
            timeout_override=AGENT_TIMEOUT_CONNECT_LLM_DOCUMENT_VERIFICATION,
            max_tokens=AGENT_MAX_TOKENS_VALIDATION,
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Timeout call successful! Duration: {duration:.3f} seconds")
        logger.info(f"Response: {response.content}")
        
        return True, duration
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Timeout call failed after {duration:.3f} seconds: {e}")
        logger.error(f"Exception type: {type(e)}")
        return False, duration

def test_llm_connection():
    """Test basic LLM connection"""
    logger.info("=== Testing LLM Connection ===")
    
    try:
        primary_llm, fast_llm = get_llms_for_persona()
        
        # Simple test message
        simple_msg = [HumanMessage(content="Hello, please respond with 'OK'")]
        
        start_time = time.time()
        response = fast_llm.invoke(
            prompt=simple_msg,
            max_tokens=10,
        )
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Simple connection test successful! Duration: {duration:.3f} seconds")
        logger.info(f"Response: {response.content}")
        
        return True, duration
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Simple connection test failed after {duration:.3f} seconds: {e}")
        return False, duration

def main():
    """Run all tests"""
    logger.info("=== Starting LLM Verification Tests ===")
    logger.info(f"Current timestamp: {datetime.now()}")
    
    # Show configuration
    logger.info(f"Timeout config: {AGENT_TIMEOUT_LLM_DOCUMENT_VERIFICATION}s")
    logger.info(f"Connection timeout: {AGENT_TIMEOUT_CONNECT_LLM_DOCUMENT_VERIFICATION}s")
    logger.info(f"Max tokens: {AGENT_MAX_TOKENS_VALIDATION}")
    
    # Test 1: Get LLM configuration
    fast_llm = test_llm_configuration()
    if not fast_llm:
        logger.error("Failed to get LLM configuration. Exiting.")
        return
    
    # Test 2: Simple connection test
    logger.info("\n" + "="*50)
    success, duration = test_llm_connection()
    if success:
        logger.info(f"✓ Connection test passed ({duration:.3f}s)")
    else:
        logger.error(f"✗ Connection test failed ({duration:.3f}s)")
    
    # Test 3: Direct LLM call
    logger.info("\n" + "="*50)
    success, duration = test_direct_llm_call(fast_llm)
    if success:
        logger.info(f"✓ Direct call test passed ({duration:.3f}s)")
    else:
        logger.error(f"✗ Direct call test failed ({duration:.3f}s)")
    
    # Test 4: Timeout-wrapped call
    logger.info("\n" + "="*50)
    success, duration = test_timeout_call(fast_llm)
    if success:
        logger.info(f"✓ Timeout call test passed ({duration:.3f}s)")
    else:
        logger.error(f"✗ Timeout call test failed ({duration:.3f}s)")
    
    logger.info("=== Test Complete ===")

if __name__ == "__main__":
    main()