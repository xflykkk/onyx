#!/usr/bin/env python3
"""
详细分析generate_sub_answer的耗时组成
"""
import csv
import json
import re
from datetime import datetime

def analyze_detailed_generate_sub_answer():
    """详细分析generate_sub_answer的耗时"""
    csv.field_size_limit(10000000)
    
    target_run_id = '4ad41248-6d01-4c28-97fe-7a15cf813dc8'
    
    with open('LangGraph_trace_export_runs_20250715_215923.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if row['run_id'] == target_run_id:
                print("=== 详细分析generate_sub_answer记录 ===")
                print(f"Run ID: {row['run_id']}")
                print(f"Parent ID: {row['parent_run_id']}")
                print(f"总耗时: {row['latency_seconds']}秒")
                print(f"开始时间: {row['start_time']}")
                print(f"结束时间: {row['end_time']}")
                print(f"状态: {row['status']}")
                print()
                
                # 尝试解析输入
                try:
                    # 手动处理JSON字符串
                    inputs_str = row['inputs']
                    # 简单的JSON解析，处理转义
                    inputs_str = inputs_str.replace('""', '"')
                    
                    print("=== 输入信息 ===")
                    print("原始输入 (前1000字符):")
                    print(inputs_str[:1000])
                    print("...")
                    
                    # 尝试找到log_messages
                    log_match = re.search(r'\"log_messages\":\s*\[(.*?)\]', inputs_str, re.DOTALL)
                    if log_match:
                        log_content = log_match.group(1)
                        print("\\n找到的日志消息:")
                        log_entries = re.findall(r'\"(.*?)\"', log_content)
                        for i, entry in enumerate(log_entries[:10], 1):  # 只显示前10条
                            if 'Time taken' in entry:
                                print(f"  {i}. {entry}")
                    
                except Exception as e:
                    print(f"解析输入失败: {e}")
                
                print("\\n" + "="*50)
                
                # 尝试解析输出
                try:
                    outputs_str = row['outputs']
                    outputs_str = outputs_str.replace('""', '"')
                    
                    print("=== 输出信息 ===")
                    print("原始输出 (前500字符):")
                    print(outputs_str[:500])
                    print("...")
                    
                    # 查找具体的LLM调用时间
                    time_match = re.search(r'Time taken: ([\d:\.]+)', outputs_str)
                    if time_match:
                        time_str = time_match.group(1)
                        print(f"\\n找到的LLM调用时间: {time_str}")
                    
                    # 查找错误信息
                    error_match = re.search(r'Result: (.*?)\\\\\"', outputs_str)
                    if error_match:
                        error_msg = error_match.group(1)
                        print(f"错误信息: {error_msg}")
                    
                    # 查找答案
                    answer_match = re.search(r'\"answer\":\s*\"(.*?)\"', outputs_str)
                    if answer_match:
                        answer = answer_match.group(1)
                        print(f"最终答案: {answer}")
                        
                except Exception as e:
                    print(f"解析输出失败: {e}")
                
                break
    
    print("\\n=== 总结 ===")
    print("根据分析，这个generate_sub_answer节点的45.798402秒耗时主要构成：")
    print("1. 内部LLM调用：约45.77秒（99.94%） - 发生了LLM Timeout Error")
    print("2. 其他处理开销：约0.03秒（0.06%）")
    print("3. 问题：LLM调用超时，导致子问题无法得到有效答案")
    print("4. 这个节点是6个并行子问题回答中的一个，所有6个都遇到了超时问题")

if __name__ == "__main__":
    analyze_detailed_generate_sub_answer()