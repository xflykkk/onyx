"""
Utility for removing <think>...</think> tags from streaming text.
"""
import re


class ThinkTagStripper:
    """Stateful processor for removing <think>...</think> tags from streaming text."""
    
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

    @staticmethod
    def clean_think_tags(text: str) -> str:
        """
        Remove <think>...</think> tags from complete text using regex.
        
        This method is designed for non-streaming scenarios where the complete
        text is available. It uses regex to efficiently remove all think tags
        while preserving other XML-like tags.
        
        Args:
            text: Complete text that may contain think tags
            
        Returns:
            Text with all think tags removed
        """
        if not text:
            return text
            
        # Use regex to remove <think>...</think> tags, including content inside
        # The pattern matches:
        # - <think> (opening tag)
        # - .*? (any content, non-greedy)
        # - </think> (closing tag)
        # DOTALL flag allows . to match newlines
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        return cleaned_text


def main():
    """Test ThinkTagStripper with comprehensive streaming simulation."""
    test_cases = [
        ("Basic think tag", "Hello <think>internal thought</think> world!"),
        ("Think tag with newlines", "Before\n<think>\nSome internal thought\nwith multiple lines\n</think>\nAfter"),
        ("Multiple think tags", "Start <think>thought1</think> middle <think>thought2</think> end"),
        ("Consecutive think tags", "Start <think>first</think><think>second</think> End"),
        ("Query tags (should be preserved)", "<think>\n\n</think>\n\n<query 1>\nWhat are the key factors that influence business success?  \n<query 2>  \nHow can a company effectively manage its resources to achieve growth?"),
        ("Only query tag", "<query 1>"),
        ("Mixed tags", "Text <think>thinking</think> more text <query>query content</query> end"),
        ("Empty think tag", "Before <think></think> after"),
        ("Long content", f"Start <think>{'Very long thought content ' * 20}</think> End"),
        ("Special characters", "Before <think>思考内容 with unicode 中文 and symbols !@#$%^&*()</think> after"),
        ("Realistic LLM response", """Looking at this question, <think>I need to consider multiple aspects here. 
        First, let me think about the technical requirements...
        
        Actually, let me approach this differently...</think>I can help you with that.

        Based on the documentation, <think>Let me check what the key points are:
        1. Prompt management
        2. Version control
        3. SDK usage</think>here are the main features:

        1. Prompt Library for centralized management
        2. Version control capabilities
        3. Integration with code through SDK

        <think>Should I provide more details about each point?</think>Would you like me to elaborate on any of these points?"""),
    ]
    
    def test_case(test_name, test_text, chunk_sizes=[1, 3, 5, 10, 20], verbose=False):
        print(f"\n{'='*60}")
        print(f"Testing: {test_name}")
        print(f"{'='*60}")
        if verbose:
            print("Original text:")
            print(repr(test_text))
            print("\nOriginal text (formatted):")
            print(test_text)
        
        # Test with different chunk sizes to simulate streaming
        for chunk_size in chunk_sizes:
            if verbose:
                print(f"\n=== Testing with chunk size: {chunk_size} ===")
            
            stripper = ThinkTagStripper()
            result = []
            
            # Simulate streaming by breaking text into chunks
            for i in range(0, len(test_text), chunk_size):
                chunk = test_text[i:i+chunk_size]
                if verbose:
                    print(f"Processing chunk: {repr(chunk)}")
                
                cleaned = stripper.process_chunk(chunk)
                if verbose:
                    print(f"Cleaned output: {repr(cleaned)}")
                
                result.append(cleaned)
            
            final_result = "".join(result)
            
            # Validate results
            has_think_tags = "<think>" in final_result or "</think>" in final_result
            has_query_tags_in_input = "<query" in test_text
            has_query_tags_in_output = "<query" in final_result
            
            if has_think_tags:
                print(f"❌ FAILED (chunk {chunk_size}): Think tags still present!")
                if verbose:
                    print(f"Result: {repr(final_result)}")
                return False
            elif has_query_tags_in_input and not has_query_tags_in_output:
                print(f"❌ FAILED (chunk {chunk_size}): Query tags were incorrectly removed!")
                if verbose:
                    print(f"Result: {repr(final_result)}")
                return False
            elif verbose:
                print(f"✅ SUCCESS (chunk {chunk_size}): Think tags properly removed, other tags preserved!")
                print(f"Final result: {repr(final_result)}")
        
        print(f"✅ ALL CHUNK SIZES PASSED for: {test_name}")
        return True
    
    # Run all test cases
    passed = 0
    total = len(test_cases)
    
    for test_name, test_text in test_cases:
        if test_case(test_name, test_text, verbose=False):
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{total} test cases passed")
    print(f"{'='*60}")
    
    # Run a detailed test for the problematic cases
    print("\n" + "="*60)
    print("DETAILED TESTING OF KEY CASES")
    print("="*60)
    
    key_cases = [
        ("Query tags preservation", "<think>\n\n</think>\n\n<query 1>\nWhat are the key factors?"),
        ("Realistic streaming", "Looking <think>hmm</think> at this, I can help you."),
    ]
    
    for test_name, test_text in key_cases:
        test_case(test_name, test_text, chunk_sizes=[1, 5], verbose=True)

    # Test the static clean_think_tags method
    print("\n" + "="*60)
    print("TESTING STATIC clean_think_tags METHOD")
    print("="*60)
    
    static_test_cases = [
        ("Simple think tag", "Hello <think>internal thought</think> world!", "Hello  world!"),
        ("Multiple think tags", "Start <think>thought1</think> middle <think>thought2</think> end", "Start  middle  end"),
        ("Think tag with newlines", "Before\n<think>\nSome thought\nwith newlines\n</think>\nAfter", "Before\n\nAfter"),
        ("No think tags", "Just normal text", "Just normal text"),
        ("Empty text", "", ""),
        ("Empty think tag", "Before <think></think> after", "Before  after"),
        ("Query tags preserved", "<query>preserve this</query> <think>remove this</think> text", "<query>preserve this</query>  text"),
        ("Real LLM response", "I can help <think>Let me think about this...</think> you with that.", "I can help  you with that."),
        ("Consecutive think tags", "<think>first</think><think>second</think>", ""),
        ("Think tags with special chars", "Text <think>思考内容 with unicode 中文</think> more text", "Text  more text"),
    ]
    
    static_passed = 0
    static_total = len(static_test_cases)
    
    for test_name, input_text, expected_output in static_test_cases:
        result = ThinkTagStripper.clean_think_tags(input_text)
        if result == expected_output:
            print(f"✅ {test_name}: PASSED")
            static_passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
            print(f"   Input: {repr(input_text)}")
            print(f"   Expected: {repr(expected_output)}")
            print(f"   Got: {repr(result)}")
    
    print(f"\n{'='*60}")
    print(f"STATIC METHOD SUMMARY: {static_passed}/{static_total} test cases passed")
    print(f"{'='*60}")
    
    # Compare streaming vs static results for consistency
    print("\n" + "="*60)
    print("COMPARING STREAMING VS STATIC RESULTS")
    print("="*60)
    
    consistency_test_cases = [
        ("Basic think tag", "Hello <think>internal thought</think> world!"),
        ("Multiple think tags", "Start <think>thought1</think> middle <think>thought2</think> end"),
        ("Query preservation", "<query>preserve</query> <think>remove</think> text"),
    ]
    
    consistency_passed = 0
    consistency_total = len(consistency_test_cases)
    
    for test_name, test_text in consistency_test_cases:
        # Test streaming result
        stripper = ThinkTagStripper()
        streaming_result = stripper.process_chunk(test_text)
        
        # Test static result
        static_result = ThinkTagStripper.clean_think_tags(test_text)
        
        if streaming_result == static_result:
            print(f"✅ {test_name}: Streaming and static results match")
            consistency_passed += 1
        else:
            print(f"❌ {test_name}: Results differ!")
            print(f"   Streaming: {repr(streaming_result)}")
            print(f"   Static: {repr(static_result)}")
    
    print(f"\n{'='*60}")
    print(f"CONSISTENCY SUMMARY: {consistency_passed}/{consistency_total} test cases consistent")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()