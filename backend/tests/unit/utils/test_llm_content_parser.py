"""
LLM内容解析器的单元测试
"""

import pytest
from onyx.utils.llm_content_parser import LLMContentParser


class TestLLMContentParser:
    """LLM内容解析器测试类"""
    
    def test_parse_queries_with_valid_tags(self):
        """测试有效的query标签解析"""
        # 基本的标签格式
        response = """<query 1>what is the purpose of the Opik prompt library?</query 1>
<query 2>how does the Opik prompt library assist in language modeling tasks?</query 2>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = [
            "what is the purpose of the Opik prompt library?",
            "how does the Opik prompt library assist in language modeling tasks?"
        ]
        assert result == expected
    
    def test_parse_queries_with_extra_whitespace(self):
        """测试包含额外空白字符的标签解析"""
        response = """
        <query 1> what is the purpose of the Opik prompt library? </query 1>  
        <query 2> how does the Opik prompt library assist in language modeling tasks? </query 2>
        """
        
        result = LLMContentParser.parse_queries(response)
        expected = [
            "what is the purpose of the Opik prompt library?",
            "how does the Opik prompt library assist in language modeling tasks?"
        ]
        assert result == expected
    
    def test_parse_queries_with_newlines_in_content(self):
        """测试查询内容包含换行符的情况"""
        response = """<query 1>what is the purpose
of the Opik prompt library?</query 1>
<query 2>how does the Opik prompt library
assist in language modeling tasks?</query 2>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = [
            "what is the purpose\nof the Opik prompt library?",
            "how does the Opik prompt library\nassist in language modeling tasks?"
        ]
        assert result == expected
    
    def test_parse_queries_with_mixed_case_tags(self):
        """测试大小写混合的标签"""
        response = """<Query 1>first query</Query 1>
<QUERY 2>second query</QUERY 2>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = ["first query", "second query"]
        assert result == expected
    
    def test_parse_queries_with_irregular_spacing(self):
        """测试标签间距不规则的情况"""
        response = """<query   1>first query</query   1>
<query 2  >second query</query  2>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = ["first query", "second query"]
        assert result == expected
    
    def test_parse_queries_fallback_to_newline_split(self):
        """测试当没有标签时回退到换行分割"""
        response = """first query without tags
second query without tags
third query without tags"""
        
        result = LLMContentParser.parse_queries(response)
        expected = [
            "first query without tags",
            "second query without tags", 
            "third query without tags"
        ]
        assert result == expected
    
    def test_parse_queries_mixed_format(self):
        """测试混合格式（部分有标签，部分没有）- 优先使用标签格式"""
        response = """<query 1>tagged query</query 1>
untagged query
<query 2>another tagged query</query 2>"""
        
        result = LLMContentParser.parse_queries(response)
        # 应该只提取有标签的内容
        expected = ["tagged query", "another tagged query"]
        assert result == expected
    
    def test_parse_queries_empty_content(self):
        """测试空内容"""
        assert LLMContentParser.parse_queries("") == []
        assert LLMContentParser.parse_queries("   ") == []
        assert LLMContentParser.parse_queries(None) == []
    
    def test_parse_queries_only_empty_tags(self):
        """测试只有空标签的情况"""
        response = """<query 1></query 1>
<query 2>   </query 2>
<query 3>valid query</query 3>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = ["valid query"]  # 只返回非空内容
        assert result == expected
    
    def test_parse_queries_malformed_tags(self):
        """测试格式错误的标签"""
        response = """<query 1>incomplete tag
<query 2>complete query</query 2>
query 3>missing opening</query 3>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = ["complete query"]  # 只提取完整的标签
        assert result == expected
    
    def test_parse_queries_with_higher_numbers(self):
        """测试大编号的查询标签"""
        response = """<query 10>tenth query</query 10>
<query 99>ninety-ninth query</query 99>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = ["tenth query", "ninety-ninth query"]
        assert result == expected
    
    def test_parse_queries_real_world_example(self):
        """测试真实世界的例子"""
        response = """<query 1> what is the purpose of the Opik prompt library?</query 1>  
<query 2> how does the Opik prompt library assist in language modeling tasks? </query 2>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = [
            "what is the purpose of the Opik prompt library?",
            "how does the Opik prompt library assist in language modeling tasks?"
        ]
        assert result == expected
    
    def test_parse_numbered_queries_basic(self):
        """测试编号查询解析基本功能"""
        response = """1. first numbered query
2. second numbered query
3. third numbered query"""
        
        result = LLMContentParser.parse_numbered_queries(response)
        expected = [
            "first numbered query",
            "second numbered query", 
            "third numbered query"
        ]
        assert result == expected
    
    def test_parse_numbered_queries_with_extra_spacing(self):
        """测试编号查询带额外空白"""
        response = """   1.   first query with spacing   
  2.  second query  
3.third query without space"""
        
        result = LLMContentParser.parse_numbered_queries(response)
        expected = [
            "first query with spacing",
            "second query",
            "third query without space"
        ]
        assert result == expected
    
    def test_extract_content_between_tags_numbered(self):
        """测试通用标签提取功能（带编号）"""
        text = """<answer 1>first answer</answer 1>
<answer 2>second answer</answer 2>"""
        
        result = LLMContentParser.extract_content_between_tags(text, "answer", numbered=True)
        expected = ["first answer", "second answer"]
        assert result == expected
    
    def test_extract_content_between_tags_simple(self):
        """测试通用标签提取功能（简单格式）"""
        text = """<result>first result</result>
<result>second result</result>"""
        
        result = LLMContentParser.extract_content_between_tags(text, "result", numbered=False)
        expected = ["first result", "second result"]
        assert result == expected
    
    def test_parse_queries_performance_with_large_text(self):
        """测试大文本的性能"""
        # 创建包含100个查询的大文本
        large_response = "\n".join([
            f"<query {i}>query number {i}</query {i}>" 
            for i in range(1, 101)
        ])
        
        result = LLMContentParser.parse_queries(large_response)
        assert len(result) == 100
        assert result[0] == "query number 1"
        assert result[99] == "query number 100"
    
    def test_parse_queries_with_special_characters(self):
        """测试包含特殊字符的查询"""
        response = """<query 1>query with "quotes" and symbols: @#$%</query 1>
<query 2>query with unicode: café, naïve, résumé</query 2>"""
        
        result = LLMContentParser.parse_queries(response)
        expected = [
            'query with "quotes" and symbols: @#$%',
            "query with unicode: café, naïve, résumé"
        ]
        assert result == expected