import pytest
from typing import List


class ThinkTagStripper:
    """
    Optimized implementation of ThinkTagStripper based on ThinkTagExtractor pattern.
    Uses buffer-based processing for better handling of streaming text.
    """
    
    def __init__(self):
        self.buffer = ""
        self.in_think_tag = False
        self.OPEN_TAG = "<think>"
        self.CLOSE_TAG = "</think>"
    
    def process_chunk(self, text: str) -> str:
        """Process a single chunk of text, returning cleaned output."""
        if not text:
            return ""
            
        self.buffer += text
        output = []
        
        while self.buffer:
            # Store buffer state to detect progress and avoid infinite loops
            buffer_at_start = self.buffer
            
            if not self.in_think_tag:
                # Look for opening tag
                open_pos = self.buffer.find(self.OPEN_TAG)
                if open_pos != -1:
                    # Add text before the opening tag to output
                    output.append(self.buffer[:open_pos])
                    # Remove processed part including the opening tag
                    self.buffer = self.buffer[open_pos + len(self.OPEN_TAG):]
                    self.in_think_tag = True
                    # Continue processing in case there's more content or immediate closing tag
                else:
                    # No opening tag found
                    # Check if buffer ends with partial opening tag
                    partial_match_len = 0
                    for i in range(1, min(len(self.OPEN_TAG), len(self.buffer) + 1)):
                        if self.buffer.endswith(self.OPEN_TAG[:i]):
                            partial_match_len = i
                    
                    if partial_match_len > 0:
                        # Keep potential partial tag in buffer for next chunk
                        output.append(self.buffer[:-partial_match_len])
                        self.buffer = self.buffer[-partial_match_len:]
                        return "".join(output)
                    else:
                        # No partial tag, output everything and clear buffer
                        output.append(self.buffer)
                        self.buffer = ""
                        return "".join(output)
            else:
                # Inside think tag, look for closing tag
                close_pos = self.buffer.find(self.CLOSE_TAG)
                if close_pos != -1:
                    # Found closing tag, skip everything up to and including the closing tag
                    self.buffer = self.buffer[close_pos + len(self.CLOSE_TAG):]
                    self.in_think_tag = False
                    # Continue processing in case there's more content after closing tag
                else:
                    # No closing tag found
                    # Check if buffer ends with partial closing tag
                    partial_match_len = 0
                    for i in range(1, min(len(self.CLOSE_TAG), len(self.buffer) + 1)):
                        if self.buffer.endswith(self.CLOSE_TAG[:i]):
                            partial_match_len = i
                    
                    if partial_match_len > 0:
                        # Keep potential partial closing tag in buffer for next chunk
                        self.buffer = self.buffer[-partial_match_len:]
                        return "".join(output)
                    else:
                        # No partial tag, all content is inside think tag, clear buffer
                        self.buffer = ""
                        return "".join(output)
            
            # Avoid infinite loop - if buffer hasn't changed, break
            if self.buffer == buffer_at_start:
                break
        
        return "".join(output)


class TestThinkTagStripper:
    """Test ThinkTagStripper under streaming conditions."""
    
    def simulate_streaming(self, text: str, chunk_sizes: List[int]) -> str:
        """Simulate streaming by breaking text into chunks."""
        stripper = ThinkTagStripper()
        result = []
        
        pos = 0
        for chunk_size in chunk_sizes:
            if pos >= len(text):
                break
            chunk = text[pos:pos + chunk_size]
            cleaned = stripper.process_chunk(chunk)
            result.append(cleaned)
            pos += chunk_size
        
        return "".join(result)
    
    def test_basic_think_tag_removal(self):
        """Test basic think tag removal in streaming mode."""
        text = "Hello <think>internal thought</think> world!"
        
        # Test with various chunk sizes
        for chunk_size in [1, 3, 5, 10, 50]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == "Hello  world!", f"Failed with chunk size {chunk_size}: {result}"
    
    def test_multiple_think_tags(self):
        """Test multiple think tags in one stream."""
        text = "Start <think>thought1</think> middle <think>thought2</think> end"
        expected = "Start  middle  end"
        
        for chunk_size in [1, 3, 7, 12]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_partial_opening_tag(self):
        """Test when opening tag is split across chunks."""
        text = "Before <think>content</think> after"
        
        # Split at various positions in the opening tag
        test_cases = [
            ([6, 1, 100], "Before  after"),  # Split at "<"
            ([7, 1, 100], "Before  after"),  # Split at "<t"
            ([8, 1, 100], "Before  after"),  # Split at "<th"
            ([9, 1, 100], "Before  after"),  # Split at "<thi"
            ([10, 1, 100], "Before  after"), # Split at "<thin"
            ([11, 1, 100], "Before  after"), # Split at "<think"
            ([12, 1, 100], "Before  after"), # Split at "<think>"
        ]
        
        for chunks, expected in test_cases:
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunks {chunks}: {result}"
    
    def test_partial_closing_tag(self):
        """Test when closing tag is split across chunks."""
        text = "Before <think>content</think> after"
        
        # Split at various positions in the closing tag
        test_cases = [
            ([19, 1, 100], "Before  after"),  # Split at "<"
            ([20, 1, 100], "Before  after"),  # Split at "</"
            ([21, 1, 100], "Before  after"),  # Split at "</t"
            ([22, 1, 100], "Before  after"),  # Split at "</th"
            ([23, 1, 100], "Before  after"),  # Split at "</thi"
            ([24, 1, 100], "Before  after"),  # Split at "</thin"
            ([25, 1, 100], "Before  after"),  # Split at "</think"
        ]
        
        for chunks, expected in test_cases:
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunks {chunks}: {result}"
    
    def test_think_tag_with_newlines(self):
        """Test think tags containing newlines."""
        text = "Before <think>\nSome internal thought\nwith multiple lines\n</think> after"
        expected = "Before  after"
        
        for chunk_size in [1, 5, 10, 20]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_incomplete_think_tag(self):
        """Test incomplete think tags at end of stream."""
        text = "Hello <think"
        
        for chunk_size in [1, 3, 5, 10]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == "Hello ", f"Failed with chunk size {chunk_size}: {result}"
    
    def test_no_think_tags(self):
        """Test text without think tags."""
        text = "This is normal text without any special tags."
        
        for chunk_size in [1, 5, 10, 20]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == text, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_empty_think_tag(self):
        """Test empty think tag."""
        text = "Before <think></think> after"
        expected = "Before  after"
        
        for chunk_size in [1, 3, 7, 15]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_single_character_chunks(self):
        """Test extreme case with single character chunks."""
        text = "A<think>B</think>C<think>D</think>E"
        expected = "ACE"
        
        chunks = [1] * len(text)
        result = self.simulate_streaming(text, chunks)
        assert result == expected, f"Failed with single character chunks: {result}"
    
    def test_complex_streaming_scenario(self):
        """Test complex real-world streaming scenario."""
        text = """This is a response <think>I need to think about this carefully</think> that contains multiple <think>another thought here</think> think tags spread across <think>final thought</think> the content."""
        expected = "This is a response  that contains multiple  think tags spread across  the content."
        
        # Various chunk patterns
        chunk_patterns = [
            [1] * len(text),  # Single character
            [5] * (len(text) // 5 + 1),  # Small chunks
            [15] * (len(text) // 15 + 1),  # Medium chunks
            [3, 7, 11, 2, 20, 1, 8] * 10,  # Random pattern
        ]
        
        for chunks in chunk_patterns:
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk pattern: {result}"
    
    def test_stateful_processing(self):
        """Test that multiple stripper instances maintain separate state."""
        text = "Text1 <think>thought1</think> end1"
        
        stripper1 = ThinkTagStripper()
        stripper2 = ThinkTagStripper()
        
        # Process different chunks with different strippers
        result1 = stripper1.process_chunk("Text1 <think>tho")
        result2 = stripper2.process_chunk("Text2 <think>tho")
        
        # Continue processing
        result1 += stripper1.process_chunk("ught1</think> end1")
        result2 += stripper2.process_chunk("ught2</think> end2")
        
        assert result1 == "Text1  end1"
        assert result2 == "Text2  end2"
    
    def test_think_tag_with_leading_newlines(self):
        """Test think tag starting with newlines."""
        text = "Start\n<think>\nthought content\n</think>\nEnd"
        expected = "Start\n\nEnd"
        
        for chunk_size in [1, 3, 8, 15]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_think_tag_with_trailing_newlines(self):
        """Test think tag ending with newlines."""
        text = "Start <think>thought content\n\n</think> End"
        expected = "Start  End"
        
        for chunk_size in [1, 5, 12, 25]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_think_tag_surrounded_by_newlines(self):
        """Test think tag completely surrounded by newlines."""
        text = "Text before\n\n<think>\nInternal thinking\nwith multiple\nlines\n</think>\n\nText after"
        expected = "Text before\n\n\n\nText after"
        
        for chunk_size in [1, 7, 15, 30]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_multiple_think_tags_with_newlines(self):
        """Test multiple think tags each with different newline patterns."""
        text = "First\n<think>\nthought 1\n</think>\nMiddle\n\n<think>\n\nthought 2\n\n</think>\n\nLast"
        expected = "First\n\nMiddle\n\n\n\nLast"
        
        for chunk_size in [1, 5, 12, 20]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_think_tag_with_special_characters(self):
        """Test think tag containing special characters."""
        text = "Before <think>思考内容 with unicode 中文 and symbols !@#$%^&*()</think> after"
        expected = "Before  after"
        
        for chunk_size in [1, 8, 20, 40]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_think_tag_with_long_content(self):
        """Test think tag with very long content."""
        long_content = "This is a very long thought " * 50  # 1400+ chars
        text = f"Start <think>{long_content}</think> End"
        expected = "Start  End"
        
        for chunk_size in [1, 10, 50, 100]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_think_tag_split_across_many_small_chunks(self):
        """Test think tag split across many very small chunks."""
        text = "Before <think>content here</think> after"
        expected = "Before  after"
        
        # Split into single character chunks
        chunks = [1] * len(text)
        result = self.simulate_streaming(text, chunks)
        assert result == expected, f"Failed with single char chunks: {result}"
    
    def test_consecutive_think_tags(self):
        """Test consecutive think tags without content between them."""
        text = "Start <think>first</think><think>second</think> End"
        expected = "Start  End"
        
        for chunk_size in [1, 5, 10, 20]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_think_tag_with_mixed_whitespace(self):
        """Test think tag with tabs, spaces, and newlines."""
        text = "Before <think>\t\n  Mixed whitespace\t\n  content\n\t</think> After"
        expected = "Before  After"
        
        for chunk_size in [1, 8, 15, 30]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result}"
    
    def test_malformed_think_tag(self):
        """Test malformed think tag with newlines - should NOT be stripped."""
        text = "think>\n\n</think>\n\n<query 1>How can prompts be created and managed in Opik platform?</query 1>  \n<query 2>What are best practices for managing prompts in code and Opik platform?</query 2>"
        expected = text  # Should remain unchanged because "think>" is not a valid opening tag
        
        # Test with various chunk sizes
        for chunk_size in [1, 5, 10, 20, 50]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result!r}"
    
    def test_incomplete_opening_tag(self):
        """Test incomplete opening tag that's not properly formed."""
        text = "Some text <think and more text"
        expected = "Some text <think and more text"
        
        # Test with various chunk sizes
        for chunk_size in [1, 3, 7, 15]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result!r}"
    
    def test_realistic_llm_response_pattern(self):
        """Test realistic LLM response with think tags interspersed."""
        text = """Looking at this question, <think>I need to consider multiple aspects here. 
        First, let me think about the technical requirements...
        
        Actually, let me approach this differently...</think>I can help you with that.

        Based on the documentation, <think>Let me check what the key points are:
        1. Prompt management
        2. Version control
        3. SDK usage</think>here are the main features:

        1. Prompt Library for centralized management
        2. Version control capabilities
        3. Integration with code through SDK

        <think>Should I provide more details about each point?</think>Would you like me to elaborate on any of these points?"""
        
        expected = """Looking at this question, I can help you with that.

        Based on the documentation, here are the main features:

        1. Prompt Library for centralized management
        2. Version control capabilities
        3. Integration with code through SDK

        Would you like me to elaborate on any of these points?"""
        
        for chunk_size in [10, 25, 50, 100]:
            chunks = [chunk_size] * (len(text) // chunk_size + 1)
            result = self.simulate_streaming(text, chunks)
            assert result == expected, f"Failed with chunk size {chunk_size}: {result!r}"