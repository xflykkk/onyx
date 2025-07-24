#!/usr/bin/env python3
"""
分析generate_sub_answer的耗时组成
"""
import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Any

def parse_log_messages(log_messages: List[str]) -> List[Dict[str, Any]]:
    """解析日志消息，提取时间信息"""
    parsed_logs = []
    
    for msg in log_messages:
        # 提取时间信息
        time_pattern = r'Time taken: ([\d:\.]+)'
        time_match = re.search(time_pattern, msg)
        
        if time_match:
            time_str = time_match.group(1)
            # 解析时间
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds_parts = parts[2].split('.')
                    seconds = int(seconds_parts[0])
                    microseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                    total_seconds = hours * 3600 + minutes * 60 + seconds + microseconds / 1000000
                else:
                    total_seconds = float(time_str)
            else:
                total_seconds = float(time_str)
            
            # 提取步骤名称
            step_pattern = r'-- ([^-]+) --'
            step_matches = re.findall(step_pattern, msg)
            step_name = ' -> '.join(step_matches) if step_matches else "Unknown"
            
            # 提取结果
            result_pattern = r'Result: ([^"]*?)(?:""|$)'
            result_match = re.search(result_pattern, msg)
            result = result_match.group(1).strip() if result_match else ""
            
            parsed_logs.append({
                'step_name': step_name,
                'time_taken': total_seconds,
                'result': result,
                'full_message': msg
            })
    
    return parsed_logs

def analyze_generate_sub_answer():
    """分析generate_sub_answer的耗时组成"""
    # 设置CSV字段大小限制
    csv.field_size_limit(10000000)
    
    with open('LangGraph_trace_export_runs_20250715_215923.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # 查找特定的generate_sub_answer记录
            if (row['run_id'] == '4ad41248-6d01-4c28-97fe-7a15cf813dc8' and 
                row['name'] == 'generate_sub_answer'):
                
                print(f"=== 分析 generate_sub_answer 记录 ===")
                print(f"Run ID: {row['run_id']}")
                print(f"总耗时: {row['latency_seconds']} 秒")
                print(f"开始时间: {row['start_time']}")
                print(f"结束时间: {row['end_time']}")
                print(f"状态: {row['status']}")
                print()
                
                # 解析输入
                try:
                    inputs = json.loads(row['inputs'])
                    input_log_messages = inputs.get('log_messages', [])
                    
                    print("=== 输入中的日志消息 ===")
                    parsed_input_logs = parse_log_messages(input_log_messages)
                    
                    total_input_time = 0
                    for i, log_entry in enumerate(parsed_input_logs, 1):
                        print(f"{i}. {log_entry['step_name']}: {log_entry['time_taken']:.6f}s")
                        if log_entry['result']:
                            print(f"   结果: {log_entry['result']}")
                        total_input_time += log_entry['time_taken']
                    
                    print(f"\n输入日志中的总耗时: {total_input_time:.6f}s")
                    
                except json.JSONDecodeError as e:
                    print(f"解析输入JSON失败: {e}")
                
                # 解析输出
                try:
                    outputs = json.loads(row['outputs'])
                    output_log_messages = outputs.get('log_messages', [])
                    
                    print("\n=== 输出中的日志消息 ===")
                    parsed_output_logs = parse_log_messages(output_log_messages)
                    
                    total_output_time = 0
                    for i, log_entry in enumerate(parsed_output_logs, 1):
                        print(f"{i}. {log_entry['step_name']}: {log_entry['time_taken']:.6f}s")
                        if log_entry['result']:
                            print(f"   结果: {log_entry['result']}")
                        total_output_time += log_entry['time_taken']
                    
                    print(f"\n输出日志中的总耗时: {total_output_time:.6f}s")
                    
                    # 显示答案
                    answer = outputs.get('answer', '')
                    if answer:
                        print(f"\n最终答案: {answer}")
                    
                except json.JSONDecodeError as e:
                    print(f"解析输出JSON失败: {e}")
                
                # 分析耗时构成
                print("\n=== 耗时构成分析 ===")
                total_seconds = float(row['latency_seconds'])
                
                # 主要耗时应该是LLM调用
                if parsed_output_logs:
                    main_time = parsed_output_logs[0]['time_taken']
                    print(f"主要LLM调用耗时: {main_time:.6f}s ({main_time/total_seconds*100:.1f}%)")
                    overhead = total_seconds - main_time
                    print(f"其他开销: {overhead:.6f}s ({overhead/total_seconds*100:.1f}%)")
                
                print(f"总耗时: {total_seconds:.6f}s")
                break

if __name__ == "__main__":
    analyze_generate_sub_answer()