#!/usr/bin/env python3

"""
Test script to analyze Chinese text chunking behavior in Onyx.

This script tests:
1. Tokenizer behavior with Chinese text
2. Chunking strategy with Chinese sentence boundaries
3. Comparison of different tokenizers for Chinese text processing
"""

import sys
import os
import time
import asyncio
from typing import List, Dict

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from onyx.natural_language_processing.utils import (
    HuggingFaceTokenizer, 
    TiktokenTokenizer, 
    get_tokenizer
)
from onyx.configs.model_configs import DOCUMENT_ENCODER_MODEL
from onyx.indexing.chunker import Chunker
from onyx.connectors.models import Document, TextSection
from onyx.configs.constants import DocumentSource
from onyx.indexing.indexing_pipeline import process_image_sections
from shared_configs.enums import EmbeddingProvider


def test_chinese_tokenization():
    """Test how different tokenizers handle Chinese text."""
    
    chinese_texts = [
        "这是一个简单的中文句子。",
        "人工智能技术在现代社会中发挥着越来越重要的作用。机器学习和深度学习已经广泛应用于各个领域。",
        "自然语言处理（NLP）是人工智能的一个重要分支。它帮助计算机理解和生成人类语言。",
        "今天天气很好，我们去公园散步吧！明天是周末，可以安排一些有趣的活动。",
        "中文文本的分词和句子边界检测比英文更加复杂，因为中文没有明显的词汇边界标记。"
    ]
    
    english_texts = [
        "This is a simple English sentence.",
        "Artificial intelligence technology plays an increasingly important role in modern society. Machine learning and deep learning have been widely applied in various fields.",
        "Natural Language Processing (NLP) is an important branch of artificial intelligence. It helps computers understand and generate human language.",
        "The weather is very nice today, let's go for a walk in the park! Tomorrow is the weekend, we can arrange some interesting activities.",
        "Chinese text segmentation and sentence boundary detection are more complex than English because Chinese lacks obvious word boundary markers."
    ]
    
    print("=== Testing Chinese Tokenization ===\n")
    
    # Test HuggingFace tokenizer (default)
    print(f"Using default embedding model: {DOCUMENT_ENCODER_MODEL}")
    hf_tokenizer = HuggingFaceTokenizer(DOCUMENT_ENCODER_MODEL)
    
    # Test TikToken tokenizer (if available)
    try:
        tiktoken_tokenizer = TiktokenTokenizer("gpt-3.5-turbo")
        print("TikToken tokenizer available")
    except Exception as e:
        print(f"TikToken tokenizer unavailable: {e}")
        tiktoken_tokenizer = None
    
    for i, (chinese_text, english_text) in enumerate(zip(chinese_texts, english_texts)):
        print(f"--- Test Case {i+1} ---")
        print(f"Chinese: {chinese_text}")
        print(f"English: {english_text}")
        print()
        
        # HuggingFace tokenizer
        zh_tokens_hf = hf_tokenizer.tokenize(chinese_text)
        en_tokens_hf = hf_tokenizer.tokenize(english_text)
        zh_token_count_hf = len(hf_tokenizer.encode(chinese_text))
        en_token_count_hf = len(hf_tokenizer.encode(english_text))
        
        print(f"HuggingFace Tokenizer:")
        print(f"  Chinese: {zh_token_count_hf} tokens")
        print(f"  English: {en_token_count_hf} tokens")
        print(f"  Chinese tokens sample: {zh_tokens_hf[:10]}...")
        print(f"  English tokens sample: {en_tokens_hf[:10]}...")
        print()
        
        # TikToken tokenizer (if available)
        if tiktoken_tokenizer:
            zh_tokens_tk = tiktoken_tokenizer.tokenize(chinese_text)
            en_tokens_tk = tiktoken_tokenizer.tokenize(english_text)
            zh_token_count_tk = len(tiktoken_tokenizer.encode(chinese_text))
            en_token_count_tk = len(tiktoken_tokenizer.encode(english_text))
            
            print(f"TikToken Tokenizer:")
            print(f"  Chinese: {zh_token_count_tk} tokens")
            print(f"  English: {en_token_count_tk} tokens")
            print(f"  Chinese tokens sample: {zh_tokens_tk[:10]}...")
            print(f"  English tokens sample: {en_tokens_tk[:10]}...")
            print()
        
        print("-" * 80)
        print()


def test_chinese_chunking():
    """Test how the chunker handles Chinese text."""
    
    print("=== Testing Chinese Text Chunking ===\n")
    
    # Create a long Chinese document
    chinese_content = """
人工智能的发展历程可以追溯到20世纪50年代。当时，科学家们开始思考如何让机器模仿人类的智能行为。

机器学习是人工智能的核心技术之一。它让计算机能够从数据中学习模式，而不需要明确的编程指令。深度学习是机器学习的一个子集，它使用多层神经网络来解决复杂问题。

自然语言处理技术使得计算机能够理解和生成人类语言。这包括文本分类、情感分析、机器翻译、问答系统等多个应用领域。现代的大型语言模型如GPT、BERT等在这些任务上表现出色。

计算机视觉是另一个重要的人工智能分支。它让机器能够"看"和"理解"图像和视频。应用包括图像识别、目标检测、人脸识别、自动驾驶等。

强化学习是一种让智能体通过与环境交互来学习最优策略的方法。它在游戏、机器人控制、推荐系统等领域有广泛应用。

人工智能的伦理问题也越来越受到关注。包括算法偏见、隐私保护、工作替代、安全风险等。我们需要在技术发展的同时，考虑其对社会的影响。

未来，人工智能将继续快速发展。量子计算、神经形态计算等新技术可能带来突破性进展。同时，人工智能与其他领域的融合也将创造新的机会。
    """.strip()
    
    # Create corresponding English content for comparison
    english_content = """
The development of artificial intelligence can be traced back to the 1950s. At that time, scientists began to think about how to make machines imitate human intelligent behavior.

Machine learning is one of the core technologies of artificial intelligence. It allows computers to learn patterns from data without explicit programming instructions. Deep learning is a subset of machine learning that uses multi-layer neural networks to solve complex problems.

Natural language processing technology enables computers to understand and generate human language. This includes text classification, sentiment analysis, machine translation, question answering systems and other application fields. Modern large language models such as GPT and BERT perform excellently in these tasks.

Computer vision is another important branch of artificial intelligence. It allows machines to "see" and "understand" images and videos. Applications include image recognition, object detection, face recognition, autonomous driving, etc.

Reinforcement learning is a method that allows intelligent agents to learn optimal strategies through interaction with the environment. It has widespread applications in games, robot control, recommendation systems and other fields.

The ethical issues of artificial intelligence are also receiving increasing attention. Including algorithmic bias, privacy protection, job replacement, safety risks, etc. We need to consider its impact on society while developing technology.

In the future, artificial intelligence will continue to develop rapidly. New technologies such as quantum computing and neuromorphic computing may bring breakthrough progress. At the same time, the integration of artificial intelligence with other fields will also create new opportunities.
    """.strip()
    
    # Get tokenizer
    tokenizer = get_tokenizer(DOCUMENT_ENCODER_MODEL, None)
    
    # Create chunker
    chunker = Chunker(
        tokenizer=tokenizer,
        enable_multipass=False,
        enable_large_chunks=False,
        enable_contextual_rag=False,
        chunk_token_limit=512,  # Standard chunk size
    )
    
    # Test Chinese document
    chinese_doc = Document(
        id="chinese_test_doc",
        source=DocumentSource.WEB,
        semantic_identifier="Chinese AI Document",
        metadata={"language": "Chinese", "topic": "Artificial Intelligence"},
        doc_updated_at=None,
        sections=[TextSection(text=chinese_content, link="")]
    )
    
    # Test English document
    english_doc = Document(
        id="english_test_doc",
        source=DocumentSource.WEB,
        semantic_identifier="English AI Document", 
        metadata={"language": "English", "topic": "Artificial Intelligence"},
        doc_updated_at=None,
        sections=[TextSection(text=english_content, link="")]
    )
    
    # Process documents
    chinese_indexing_docs = process_image_sections([chinese_doc])
    english_indexing_docs = process_image_sections([english_doc])
    
    # Chunk documents
    chinese_chunks = chunker.chunk(chinese_indexing_docs)
    english_chunks = chunker.chunk(english_indexing_docs)
    
    print(f"Chinese document chunks: {len(chinese_chunks)}")
    print(f"English document chunks: {len(english_chunks)}")
    print()
    
    # Analyze Chinese chunks
    print("=== Chinese Chunks Analysis ===")
    for i, chunk in enumerate(chinese_chunks):
        token_count = len(tokenizer.encode(chunk.content))
        print(f"Chunk {i+1}:")
        print(f"  Token count: {token_count}")
        print(f"  Character count: {len(chunk.content)}")
        print(f"  Content preview: {chunk.content[:100]}...")
        if i < 2:  # Show first 2 chunks in detail
            print(f"  Full content: {chunk.content}")
        print()
    
    # Analyze English chunks  
    print("=== English Chunks Analysis ===")
    for i, chunk in enumerate(english_chunks):
        token_count = len(tokenizer.encode(chunk.content))
        print(f"Chunk {i+1}:")
        print(f"  Token count: {token_count}")
        print(f"  Character count: {len(chunk.content)}")
        print(f"  Content preview: {chunk.content[:100]}...")
        if i < 2:  # Show first 2 chunks in detail
            print(f"  Full content: {chunk.content}")
        print()


def test_sentence_boundary_detection():
    """Test sentence boundary detection for Chinese text."""
    
    print("=== Testing Chinese Sentence Boundary Detection ===\n")
    
    # Test various Chinese sentence patterns
    test_texts = [
        # Standard punctuation
        "这是第一句话。这是第二句话！这是第三句话？",
        
        # Mixed punctuation and length
        "人工智能技术发展迅速。机器学习、深度学习等技术已经广泛应用于各个领域，包括图像识别、语音处理、自然语言理解等。未来还有更大的发展空间！",
        
        # Quotations and special punctuation
        "他说：\"今天天气很好。\"然后就出门了。天气确实不错，阳光明媚。",
        
        # Numbers and mixed content
        "2023年，中国GDP增长了5.2%。这个数字反映了经济的稳定发展。预计2024年会有更好的表现。",
        
        # Technical content
        "自然语言处理（NLP）是AI的重要分支。它包含分词、词性标注、句法分析等技术。应用领域包括机器翻译、问答系统等。"
    ]
    
    tokenizer = get_tokenizer(DOCUMENT_ENCODER_MODEL, None)
    
    # Initialize chunker with small chunk size to see sentence splitting
    chunker = Chunker(
        tokenizer=tokenizer,
        chunk_token_limit=100,  # Small chunk size to force splitting
        blurb_size=50
    )
    
    for i, text in enumerate(test_texts):
        print(f"--- Test Text {i+1} ---")
        print(f"Original: {text}")
        print()
        
        # Create a simple document
        doc = Document(
            id=f"test_doc_{i}",
            source=DocumentSource.WEB,
            semantic_identifier=f"Test Document {i+1}",
            metadata={},
            doc_updated_at=None,
            sections=[TextSection(text=text, link="")]
        )
        
        indexing_docs = process_image_sections([doc])
        chunks = chunker.chunk(indexing_docs)
        
        print(f"Number of chunks: {len(chunks)}")
        for j, chunk in enumerate(chunks):
            token_count = len(tokenizer.encode(chunk.content))
            print(f"  Chunk {j+1} ({token_count} tokens): {chunk.content}")
        
        print("-" * 80)
        print()


def main():
    """Run all Chinese text processing tests."""
    print("Starting Chinese Text Processing Analysis for Onyx\n")
    print("=" * 80)
    print()
    
    try:
        # Test tokenization
        test_chinese_tokenization()
        
        # Test chunking
        test_chinese_chunking()
        
        # Test sentence boundary detection
        test_sentence_boundary_detection()
        
        print("=" * 80)
        print("Analysis complete!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()