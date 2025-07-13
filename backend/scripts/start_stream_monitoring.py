#!/usr/bin/env python3
"""
启动流式监控
自动监控和分析新的流式日志
"""
import os
import time
import json
from datetime import datetime
from pathlib import Path


def monitor_stream_logs(log_dir="/tmp/onyx_stream_logs", watch_interval=2):
    """监控流式日志目录，自动分析新文件"""
    
    # 确保日志目录存在
    Path(log_dir).mkdir(exist_ok=True)
    
    print(f"🔍 开始监控流式日志目录: {log_dir}")
    print(f"⏱️  检查间隔: {watch_interval} 秒")
    print("按 Ctrl+C 停止监控\n")
    
    processed_files = set()
    
    try:
        while True:
            # 扫描日志文件
            current_files = set()
            if os.path.exists(log_dir):
                current_files = {
                    os.path.join(log_dir, f) 
                    for f in os.listdir(log_dir) 
                    if f.startswith("stream_") and f.endswith(".json")
                }
            
            # 检查新文件
            new_files = current_files - processed_files
            for file_path in new_files:
                try:
                    # 检查文件是否完整（包含 "complete": true）
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get('complete'):
                        print(f"📝 发现新的完整日志: {os.path.basename(file_path)}")
                        analyze_log_file_quickly(file_path, data)
                        processed_files.add(file_path)
                        print("-" * 60)
                    
                except Exception as e:
                    # 文件可能还在写入中
                    pass
            
            time.sleep(watch_interval)
            
    except KeyboardInterrupt:
        print("\n🛑 监控已停止")


def analyze_log_file_quickly(file_path: str, log_data: dict):
    """快速分析日志文件"""
    print(f"🕐 时间: {log_data.get('start_time', 'N/A')}")
    print(f"👤 用户: {log_data.get('request_info', {}).get('user_email', 'N/A')}")
    print(f"💬 消息: {log_data.get('request_info', {}).get('message', 'N/A')[:50]}...")
    print(f"📦 总包数: {log_data.get('total_packets', 0)}")
    
    # 统计关键数据包
    packets = log_data.get('packets', [])
    sub_questions = []
    documents_count = 0
    answer_length = 0
    
    for packet in packets:
        parsed = packet.get('parsed_data', {})
        if 'sub_question' in parsed:
            sub_questions.append(f"[{parsed.get('level', '?')}.{parsed.get('level_question_num', '?')}] {parsed['sub_question']}")
        elif 'top_documents' in parsed:
            documents_count += len(parsed['top_documents'])
        elif 'answer_piece' in parsed and parsed.get('answer_type') != 'agent_sub_answer':
            answer_length += len(parsed.get('answer_piece', ''))
    
    if sub_questions:
        print(f"❓ 子问题 ({len(sub_questions)} 个):")
        for sq in sub_questions[:3]:  # 只显示前3个
            print(f"   {sq}")
        if len(sub_questions) > 3:
            print(f"   ... 还有 {len(sub_questions) - 3} 个")
    
    print(f"📄 文档数: {documents_count}")
    print(f"📝 答案长度: {answer_length} 字符")


def print_usage():
    """打印使用说明"""
    print("🔧 Onyx 流式监控工具")
    print("=" * 50)
    print("功能:")
    print("  1. 自动监控新的流式日志文件")
    print("  2. 实时分析和展示关键信息")
    print("  3. 统计子问题、文档、答案等数据")
    print()
    print("使用方法:")
    print("  python start_stream_monitoring.py      # 开始监控")
    print("  python view_stream_logs.py --latest    # 查看最新日志详情")
    print("  python view_stream_logs.py --help      # 查看详细帮助")
    print()
    print("日志位置: /tmp/onyx_stream_logs/")
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print_usage()
    else:
        monitor_stream_logs()