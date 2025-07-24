#!/usr/bin/env python3
"""
分析LangGraph跟踪CSV文件，找出耗时的操作
"""
import csv
import json
import re
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import os

class TraceAnalyzer:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.time_records = []
        
    def parse_time_string(self, time_str: str) -> float:
        """将时间字符串转换为秒数"""
        if not time_str:
            return 0.0
        
        # 处理 "0:00:02.482820" 格式
        pattern = r'(\d+):(\d+):(\d+)\.(\d+)'
        match = re.search(pattern, time_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            microseconds = int(match.group(4))
            return hours * 3600 + minutes * 60 + seconds + microseconds / 1000000
        
        # 处理纯数字格式
        try:
            return float(time_str)
        except ValueError:
            return 0.0
    
    def extract_log_messages(self, outputs_json: str) -> List[str]:
        """从outputs JSON中提取log_messages"""
        try:
            outputs = json.loads(outputs_json)
            return outputs.get('log_messages', [])
        except (json.JSONDecodeError, TypeError):
            return []
    
    def parse_log_message(self, log_msg: str) -> Optional[Dict[str, Any]]:
        """解析单条日志消息，提取时间信息"""
        if not log_msg or 'Time taken:' not in log_msg:
            return None
            
        # 提取时间信息
        time_pattern = r'Time taken: ([\d:\.]+)'
        time_match = re.search(time_pattern, log_msg)
        if not time_match:
            return None
            
        time_taken = self.parse_time_string(time_match.group(1))
        
        # 提取步骤名称（从 -- 到 -- 之间的内容）
        step_pattern = r'-- ([^-]+) --'
        step_matches = re.findall(step_pattern, log_msg)
        step_name = ' -> '.join(step_matches) if step_matches else "Unknown Step"
        
        # 提取结果信息
        result_pattern = r'Result: ([^"]*?)(?:""|$)'
        result_match = re.search(result_pattern, log_msg)
        result = result_match.group(1).strip() if result_match else ""
        
        return {
            'step_name': step_name,
            'time_taken': time_taken,
            'result': result,
            'full_message': log_msg
        }
    
    def analyze(self) -> List[Dict[str, Any]]:
        """分析CSV文件并返回耗时记录"""
        print(f"开始分析文件: {self.csv_file}")
        
        # 增加CSV字段大小限制
        csv.field_size_limit(10000000)  # 10MB
        
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                if row_num % 1000 == 0:
                    print(f"已处理 {row_num} 行...")
                
                # 直接使用latency_seconds字段
                if row.get('latency_seconds'):
                    latency = float(row['latency_seconds'])
                    if latency > 0:
                        self.time_records.append({
                            'step_name': row.get('name', 'Unknown'),
                            'time_taken': latency,
                            'result': row.get('status', ''),
                            'full_message': f"Run: {row.get('name', 'Unknown')} - Status: {row.get('status', '')}",
                            'run_type': row.get('run_type', ''),
                            'inputs': row.get('inputs', '')[:200] if row.get('inputs') else '',
                            'outputs': row.get('outputs', '')[:200] if row.get('outputs') else ''
                        })
                
                # 从log_messages中提取更详细的时间信息
                log_messages = self.extract_log_messages(row.get('outputs', ''))
                for log_msg in log_messages:
                    parsed = self.parse_log_message(log_msg)
                    if parsed and parsed['time_taken'] > 0:
                        # 添加输入信息的前200字符
                        inputs_preview = row.get('inputs', '')[:200] if row.get('inputs') else ''
                        parsed['inputs'] = inputs_preview
                        parsed['run_type'] = row.get('run_type', '')
                        self.time_records.append(parsed)
        
        print(f"分析完成，共找到 {len(self.time_records)} 条时间记录")
        
        # 按时间排序
        self.time_records.sort(key=lambda x: x['time_taken'], reverse=True)
        
        return self.time_records
    
    def print_top_records(self, top_n: int = 20):
        """打印耗时最多的前N条记录"""
        if not self.time_records:
            print("没有找到任何时间记录")
            return
            
        print(f"\n=== 耗时最多的前 {top_n} 条记录 ===\n")
        
        for i, record in enumerate(self.time_records[:top_n], 1):
            print(f"第 {i} 名:")
            print(f"  步骤名称: {record['step_name']}")
            print(f"  耗时: {record['time_taken']:.6f} 秒")
            print(f"  结果: {record['result']}")
            print(f"  运行类型: {record.get('run_type', 'N/A')}")
            
            # 打印输入的前200字符
            if record.get('inputs'):
                print(f"  输入 (前200字符): {record['inputs']}")
            
            # 打印输出的前200字符
            if record.get('outputs'):
                print(f"  输出 (前200字符): {record['outputs']}")
            
            print(f"  完整消息: {record['full_message'][:200]}...")
            print("-" * 80)
    
    def export_to_json(self, output_file: str, top_n: int = 100):
        """导出结果到JSON文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.time_records[:top_n], f, indent=2, ensure_ascii=False)
        print(f"结果已导出到: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="分析LangGraph跟踪CSV文件")
    parser.add_argument("csv_file", help="CSV文件路径")
    parser.add_argument("--top", type=int, default=20, help="显示前N条记录 (默认: 20)")
    parser.add_argument("--export", help="导出结果到JSON文件")
    parser.add_argument("--export-top", type=int, default=100, help="导出前N条记录到JSON (默认: 100)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"错误: 文件 {args.csv_file} 不存在")
        sys.exit(1)
    
    analyzer = TraceAnalyzer(args.csv_file)
    analyzer.analyze()
    analyzer.print_top_records(args.top)
    
    if args.export:
        analyzer.export_to_json(args.export, args.export_top)

if __name__ == "__main__":
    main()