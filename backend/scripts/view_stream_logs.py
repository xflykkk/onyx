#!/usr/bin/env python3
"""
流式日志查看器
用于分析 SSE 流式数据日志
"""
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any


def list_log_files(log_dir="/Users/zhuxiaofeng/Github/onyx/backend/example") -> List[str]:
    """列出所有日志文件"""
    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        return []
    
    files = [f for f in os.listdir(log_dir) if f.startswith("stream_") and f.endswith(".json")]
    files.sort(reverse=True)  # 最新的在前
    return [os.path.join(log_dir, f) for f in files]


def load_log_file(file_path: str) -> Dict[str, Any]:
    """加载日志文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载日志文件失败: {e}")
        return {}


def print_log_summary(log_data: Dict[str, Any]):
    """打印日志摘要"""
    print("=" * 80)
    print(f"📊 流式日志摘要")
    print("=" * 80)
    print(f"请求ID: {log_data.get('request_id', 'N/A')}")
    print(f"时间戳: {log_data.get('timestamp', 'N/A')}")
    print(f"开始时间: {log_data.get('start_time', 'N/A')}")
    print(f"结束时间: {log_data.get('end_time', 'N/A')}")
    print(f"总数据包: {log_data.get('total_packets', 0)}")
    print(f"总大小: {log_data.get('total_size', 0)} bytes")
    print(f"完成状态: {'✅' if log_data.get('complete') else '🔄'}")
    
    # 请求信息
    request_info = log_data.get('request_info', {})
    if request_info:
        print(f"\n📝 请求信息:")
        print(f"  用户: {request_info.get('user_email', 'N/A')}")
        print(f"  消息: {request_info.get('message', 'N/A')[:100]}...")
        print(f"  会话ID: {request_info.get('chat_session_id', 'N/A')}")
        print(f"  智能搜索: {request_info.get('use_agentic_search', 'N/A')}")
    
    # 数据包类型统计
    packet_types = log_data.get('packet_types', {})
    if packet_types:
        print(f"\n📦 数据包类型统计:")
        for ptype, count in packet_types.items():
            print(f"  {ptype}: {count}")


def print_packet_details(packets: List[Dict[str, Any]], packet_types: List[str] = None, limit: int = 10):
    """打印数据包详情"""
    print("\n" + "=" * 80)
    print(f"📦 数据包详情 (显示前 {limit} 个)")
    print("=" * 80)
    
    shown = 0
    for i, packet in enumerate(packets):
        if shown >= limit:
            break
            
        parsed = packet.get('parsed_data', {})
        
        # 过滤数据包类型
        if packet_types:
            packet_type = identify_packet_type(parsed)
            if packet_type not in packet_types:
                continue
        
        shown += 1
        print(f"\n#{packet.get('sequence', i+1)} [{packet.get('timestamp', 'N/A')}]")
        print(f"类型: {identify_packet_type(parsed)}")
        print(f"大小: {packet.get('data_size', 0)} bytes")
        
        # 显示关键字段
        if 'answer_piece' in parsed:
            print(f"答案片段: {parsed['answer_piece'][:100]}...")
        elif 'sub_question' in parsed:
            print(f"子问题: {parsed['sub_question']}")
            print(f"层级: {parsed.get('level', 'N/A')}.{parsed.get('level_question_num', 'N/A')}")
        elif 'sub_query' in parsed:
            print(f"子查询: {parsed['sub_query']}")
            print(f"层级: {parsed.get('level', 'N/A')}.{parsed.get('level_question_num', 'N/A')}")
        elif 'top_documents' in parsed:
            docs = parsed['top_documents']
            print(f"文档数量: {len(docs)}")
            if docs:
                print(f"第一个文档: {docs[0].get('semantic_identifier', 'N/A')}")
        elif 'message' in parsed and 'message_id' in parsed:
            print(f"消息ID: {parsed['message_id']}")
            print(f"消息长度: {len(parsed.get('message', ''))}")
            if 'sub_questions' in parsed:
                print(f"子问题数量: {len(parsed['sub_questions'])}")
        
        # 显示原始JSON (简化)
        if len(packet.get('raw_data', '')) < 200:
            print(f"原始数据: {packet.get('raw_data', '')}")
        else:
            print(f"原始数据: {packet.get('raw_data', '')[:200]}...")


def identify_packet_type(parsed_data: Dict[str, Any]) -> str:
    """识别数据包类型"""
    if "answer_piece" in parsed_data:
        return "answer_piece"
    elif "sub_question" in parsed_data:
        return "sub_question"  
    elif "sub_query" in parsed_data:
        return "sub_query"
    elif "top_documents" in parsed_data:
        return "documents"
    elif "context_docs" in parsed_data:
        return "context_docs"
    elif "thinking_content" in parsed_data:
        return "thinking"
    elif "error" in parsed_data:
        return "error"
    elif "message" in parsed_data and "message_id" in parsed_data:
        return "message_detail"
    else:
        return "other"


def analyze_sub_questions(packets: List[Dict[str, Any]]):
    """分析子问题数据包"""
    print("\n" + "=" * 80)
    print("🔍 子问题分析")
    print("=" * 80)
    
    sub_questions = []
    sub_queries = []
    answers = []
    
    for packet in packets:
        parsed = packet.get('parsed_data', {})
        if 'sub_question' in parsed:
            sub_questions.append({
                'question': parsed['sub_question'],
                'level': parsed.get('level', 'N/A'),
                'num': parsed.get('level_question_num', 'N/A'),
                'timestamp': packet.get('timestamp')
            })
        elif 'sub_query' in parsed:
            sub_queries.append({
                'query': parsed['sub_query'],
                'level': parsed.get('level', 'N/A'),
                'num': parsed.get('level_question_num', 'N/A'),
                'timestamp': packet.get('timestamp')
            })
        elif parsed.get('answer_type') == 'agent_sub_answer':
            answers.append({
                'answer_piece': parsed.get('answer_piece', ''),
                'level': parsed.get('level', 'N/A'),
                'num': parsed.get('level_question_num', 'N/A'),
                'timestamp': packet.get('timestamp')
            })
    
    print(f"📋 子问题 ({len(sub_questions)} 个):")
    for sq in sub_questions:
        print(f"  [{sq['level']}.{sq['num']}] {sq['question']}")
    
    print(f"\n🔍 子查询 ({len(sub_queries)} 个):")
    for sq in sub_queries:
        print(f"  [{sq['level']}.{sq['num']}] {sq['query']}")
    
    print(f"\n💬 子答案片段 ({len(answers)} 个):")
    for ans in answers[:5]:  # 只显示前5个
        print(f"  [{ans['level']}.{ans['num']}] {ans['answer_piece'][:50]}...")


def main():
    """主函数"""
    log_dir = "/Users/zhuxiaofeng/Github/onyx/backend/example"
    
    # 获取命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("用法:")
            print("  python view_stream_logs.py                    # 列出所有日志")
            print("  python view_stream_logs.py <文件名>           # 查看指定日志")
            print("  python view_stream_logs.py --latest          # 查看最新日志")
            print("  python view_stream_logs.py --latest --sub    # 查看最新日志的子问题")
            return
        elif sys.argv[1] == "--latest":
            # 查看最新日志
            files = list_log_files(log_dir)
            if not files:
                print("❌ 没有找到日志文件")
                return
            target_file = files[0]
        else:
            # 指定文件
            target_file = sys.argv[1] if os.path.isabs(sys.argv[1]) else os.path.join(log_dir, sys.argv[1])
            if not os.path.exists(target_file):
                print(f"❌ 文件不存在: {target_file}")
                return
    else:
        # 列出所有日志文件
        files = list_log_files(log_dir)
        if not files:
            print("❌ 没有找到日志文件")
            return
        
        print("📋 可用的流式日志文件:")
        for i, file_path in enumerate(files[:10]):  # 只显示最新10个
            file_name = os.path.basename(file_path)
            print(f"  {i+1}. {file_name}")
        
        print(f"\n使用方法:")
        print(f"  python {sys.argv[0]} --latest              # 查看最新日志")
        print(f"  python {sys.argv[0]} <文件名>              # 查看指定日志")
        return
    
    # 加载并分析日志
    log_data = load_log_file(target_file)
    if not log_data:
        return
    
    print(f"📁 日志文件: {target_file}")
    print_log_summary(log_data)
    
    packets = log_data.get('packets', [])
    if packets:
        # 检查是否只显示子问题
        if "--sub" in sys.argv:
            analyze_sub_questions(packets)
        else:
            print_packet_details(packets, limit=20)
            
            # 如果有子问题数据，也显示分析
            if any('sub_question' in p.get('parsed_data', {}) for p in packets):
                analyze_sub_questions(packets)


if __name__ == "__main__":
    main()