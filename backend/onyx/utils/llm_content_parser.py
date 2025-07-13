"""
LLM内容解析工具类

提供通用的LLM响应内容解析方法，包括标签解析、查询提取等功能。
"""

import re
from typing import List


class LLMContentParser:
    """LLM响应内容解析器"""
    
    @staticmethod
    def parse_queries(llm_response: str) -> List[str]:
        """
        解析LLM响应中的查询内容，只返回纯文本内容
        
        首先尝试解析 <query X>content</query X> 格式的标签，提取标签内的文本内容，
        如果解析失败则回退到简单的换行分割。
        
        Args:
            llm_response: LLM的原始响应文本
            
        Returns:
            解析出的查询文本列表（不包含标签），自动去除前后空白和换行
            
        Examples:
            >>> parser = LLMContentParser()
            >>> response = '''<query 1>what is the purpose?</query 1>
            ... <query 2>how does it work?</query 2>'''
            >>> parser.parse_queries(response)
            ['what is the purpose?', 'how does it work?']
        """
        if not llm_response or not llm_response.strip():
            return []
            
        # 使用统一的方法处理所有情况
        queries = []
        
        # 1. 首先提取所有完整标签的内容（严格匹配）
        strict_pattern = r'<query\s+(\d+)\s*>(.*?)</query\s+\1\s*>'
        strict_matches = re.findall(strict_pattern, llm_response, re.DOTALL | re.IGNORECASE)
        
        # 2. 然后尝试宽松匹配
        loose_pattern = r'<query\s+\d+\s*>(.*?)</query\s*(?:\d+)?\s*>'
        loose_matches = re.findall(loose_pattern, llm_response, re.DOTALL | re.IGNORECASE)
        
        # 从完整标签中提取内容
        if strict_matches:
            for number, content in strict_matches:
                cleaned_query = content.strip()
                if cleaned_query:
                    queries.append(cleaned_query)
        elif loose_matches:
            for content in loose_matches:
                cleaned_query = content.strip()
                if cleaned_query:
                    queries.append(cleaned_query)
        
        # 3. 寻找不完整的查询（有开始标签但没有匹配的结束标签）
        # 分割文本按照 <query X> 标签
        query_sections = re.split(r'(<query\s+\d+\s*>)', llm_response, flags=re.IGNORECASE)
        
        i = 1
        while i < len(query_sections):
            if re.match(r'<query\s+\d+\s*>', query_sections[i], re.IGNORECASE):
                # 找到查询开始标签，获取后面的内容
                if i + 1 < len(query_sections):
                    content = query_sections[i + 1]
                    
                    # 检查这个内容是否已经包含在完整标签中
                    already_extracted = False
                    combined_content = query_sections[i] + content
                    
                    # 如果内容包含结束标签，可能已经被完整提取了
                    if re.search(r'</query\s*(?:\d+)?\s*>', content, re.IGNORECASE):
                        already_extracted = True
                    
                    if not already_extracted:
                        # 清理内容：移除结束标签、其他query开始标签等
                        cleaned_content = re.sub(r'</query\s*(?:\d+)?\s*>.*$', '', content, flags=re.DOTALL | re.IGNORECASE)
                        cleaned_content = re.sub(r'<query\s+\d+\s*>.*$', '', cleaned_content, flags=re.DOTALL | re.IGNORECASE)
                        
                        final_content = cleaned_content.strip()
                        if final_content and len(final_content) > 3:
                            # 避免重复添加
                            if final_content not in queries:
                                queries.append(final_content)
                i += 2
            else:
                i += 1
        
        # 如果还是没有找到任何查询，使用回退逻辑
        if not queries:
            lines = llm_response.split("\n")
            for line in lines:
                cleaned_line = line.strip()
                # 过滤掉不完整的query标签（只有开始标签，没有结束标签）
                if (cleaned_line and 
                    not re.match(r'^<query\s+\d+>\s*$', cleaned_line) and
                    not re.match(r'^</query\s*(?:\d+)?\s*>.*$', cleaned_line)):
                    queries.append(cleaned_line)
        
        return queries
    
    @staticmethod
    def parse_numbered_queries(llm_response: str) -> List[str]:
        """
        解析带编号的查询格式（如 1. query, 2. query 等）
        
        Args:
            llm_response: LLM的原始响应文本
            
        Returns:
            解析出的查询列表
        """
        if not llm_response or not llm_response.strip():
            return []
            
        # 匹配编号格式：1. query, 2. query 等
        numbered_pattern = r'^\s*\d+\.\s*(.+)$'
        queries = []
        
        for line in llm_response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            match = re.match(numbered_pattern, line)
            if match:
                query = match.group(1).strip()
                if query:
                    queries.append(query)
            else:
                # 如果不是编号格式但有内容，也包含进去
                if line:
                    queries.append(line)
                    
        return queries
    
    @staticmethod
    def extract_content_between_tags(
        text: str, 
        tag_name: str, 
        numbered: bool = False
    ) -> List[str]:
        """
        通用的标签内容提取方法
        
        Args:
            text: 要解析的文本
            tag_name: 标签名称（如 'query', 'answer'）
            numbered: 是否包含编号（如 <query 1>, <query 2>）
            
        Returns:
            提取的内容列表
        """
        if not text or not text.strip():
            return []
            
        if numbered:
            # 匹配带编号的标签：<tag_name X>content</tag_name X>
            pattern = f'<{tag_name}\\s+\\d+>(.*?)</{tag_name}\\s+\\d+>'
        else:
            # 匹配简单标签：<tag_name>content</tag_name>
            pattern = f'<{tag_name}>(.*?)</{tag_name}>'
            
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        # 清理并返回非空内容
        results = []
        for match in matches:
            cleaned = match.strip()
            if cleaned:
                results.append(cleaned)
                
        return results