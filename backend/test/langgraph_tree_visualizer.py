#!/usr/bin/env python3
"""
LangGraph跟踪树状图可视化工具
分析LangGraph执行的节点层次关系，并生成树状图
"""
import csv
import json
import re
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import sys
import os
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TreeNode:
    """树节点类"""
    run_id: str
    parent_run_id: Optional[str]
    trace_id: str
    name: str
    run_type: str
    start_time: str
    end_time: str
    latency_seconds: float
    status: str
    level: int = 0
    children: List['TreeNode'] = field(default_factory=list)
    inputs: str = ""
    outputs: str = ""
    

class LangGraphTreeVisualizer:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.nodes: Dict[str, TreeNode] = {}
        self.roots: List[TreeNode] = []
        self.tree_structure = []
        
    def parse_csv_data(self) -> None:
        """解析CSV数据构建节点树"""
        print(f"开始解析文件: {self.csv_file}")
        
        # 增加CSV字段大小限制
        csv.field_size_limit(10000000)  # 10MB
        
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                if row_num % 100 == 0:
                    print(f"已处理 {row_num} 行...")
                
                # 创建节点
                node = TreeNode(
                    run_id=row['run_id'],
                    parent_run_id=row['parent_run_id'] if row['parent_run_id'] else None,
                    trace_id=row['trace_id'],
                    name=row['name'],
                    run_type=row['run_type'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    latency_seconds=float(row['latency_seconds']) if row['latency_seconds'] else 0.0,
                    status=row['status'],
                    inputs=row['inputs'][:100] if row['inputs'] else "",
                    outputs=row['outputs'][:100] if row['outputs'] else ""
                )
                
                self.nodes[node.run_id] = node
        
        print(f"解析完成，共 {len(self.nodes)} 个节点")
        
    def build_tree_structure(self) -> None:
        """构建树结构"""
        print("构建树结构...")
        
        # 找出所有根节点（没有parent_run_id的节点）
        for node in self.nodes.values():
            if node.parent_run_id is None:
                self.roots.append(node)
                node.level = 0
            else:
                # 将节点添加到其父节点的children列表中
                if node.parent_run_id in self.nodes:
                    parent = self.nodes[node.parent_run_id]
                    parent.children.append(node)
                    node.level = parent.level + 1
                else:
                    # 如果找不到父节点，将其视为根节点
                    self.roots.append(node)
                    node.level = 0
        
        # 按开始时间排序children
        def sort_children(node: TreeNode):
            node.children.sort(key=lambda x: x.start_time)
            for child in node.children:
                sort_children(child)
        
        for root in self.roots:
            sort_children(root)
        
        print(f"构建完成，共 {len(self.roots)} 个根节点")
    
    def detect_parallel_execution(self, node: TreeNode) -> List[List[TreeNode]]:
        """检测并行执行的节点组"""
        if not node.children:
            return []
        
        # 按开始时间排序
        children = sorted(node.children, key=lambda x: x.start_time)
        parallel_groups = []
        current_group = [children[0]]
        
        for i in range(1, len(children)):
            current_child = children[i]
            prev_child = children[i-1]
            
            # 解析时间字符串
            current_start = datetime.fromisoformat(current_child.start_time.replace('Z', '+00:00'))
            prev_end = datetime.fromisoformat(prev_child.end_time.replace('Z', '+00:00'))
            
            # 如果当前节点的开始时间在前一个节点结束前，认为是并行执行
            if current_start <= prev_end:
                current_group.append(current_child)
            else:
                if len(current_group) > 1:
                    parallel_groups.append(current_group)
                current_group = [current_child]
        
        # 添加最后一组
        if len(current_group) > 1:
            parallel_groups.append(current_group)
        
        return parallel_groups
    
    def generate_tree_text(self, node: TreeNode, prefix: str = "", is_last: bool = True, 
                          parallel_groups: List[List[TreeNode]] = None) -> List[str]:
        """生成树状文本表示"""
        lines = []
        
        # 确定当前节点的符号
        if node.level == 0:
            connector = ""
        else:
            connector = "└── " if is_last else "├── "
        
        # 检查是否在并行组中
        parallel_marker = ""
        if parallel_groups:
            for group in parallel_groups:
                if node in group:
                    parallel_marker = f" [并行组{len(group)}个]"
                    break
        
        # 格式化节点信息
        node_info = f"{prefix}{connector}{node.name} ({node.run_type})"
        timing_info = f" - {node.latency_seconds:.6f}s"
        status_info = f" [{node.status}]"
        
        line = f"{node_info}{timing_info}{status_info}{parallel_marker}"
        lines.append(line)
        
        # 如果有输入输出信息，添加到下一行
        if node.inputs or node.outputs:
            detail_prefix = prefix + ("    " if is_last else "│   ")
            if node.inputs:
                lines.append(f"{detail_prefix}📥 输入: {node.inputs}...")
            if node.outputs:
                lines.append(f"{detail_prefix}📤 输出: {node.outputs}...")
        
        # 递归处理子节点
        if node.children:
            # 检测并行执行
            parallel_groups = self.detect_parallel_execution(node)
            
            # 为子节点生成新的前缀
            child_prefix = prefix + ("    " if is_last else "│   ")
            
            for i, child in enumerate(node.children):
                is_last_child = (i == len(node.children) - 1)
                child_lines = self.generate_tree_text(child, child_prefix, is_last_child, parallel_groups)
                lines.extend(child_lines)
        
        return lines
    
    def print_tree_structure(self) -> None:
        """打印树结构"""
        print("\n=== LangGraph 执行树状图 ===\n")
        
        for root in self.roots:
            tree_lines = self.generate_tree_text(root)
            for line in tree_lines:
                print(line)
            print()  # 根节点之间空一行
    
    def generate_statistics(self) -> Dict[str, Any]:
        """生成执行统计信息"""
        stats = {
            "total_nodes": len(self.nodes),
            "total_roots": len(self.roots),
            "run_types": defaultdict(int),
            "status_count": defaultdict(int),
            "top_slowest_nodes": [],
            "parallel_execution_count": 0
        }
        
        # 统计运行类型和状态
        slowest_nodes = []
        for node in self.nodes.values():
            stats["run_types"][node.run_type] += 1
            stats["status_count"][node.status] += 1
            slowest_nodes.append((node.name, node.latency_seconds, node.run_type))
        
        # 最慢的20个节点
        slowest_nodes.sort(key=lambda x: x[1], reverse=True)
        stats["top_slowest_nodes"] = slowest_nodes[:20]
        
        # 统计并行执行
        def count_parallel_executions(node: TreeNode):
            count = 0
            if node.children:
                parallel_groups = self.detect_parallel_execution(node)
                count += len(parallel_groups)
                for child in node.children:
                    count += count_parallel_executions(child)
            return count
        
        for root in self.roots:
            stats["parallel_execution_count"] += count_parallel_executions(root)
        
        return stats
    
    def print_statistics(self) -> None:
        """打印统计信息"""
        stats = self.generate_statistics()
        
        print("\n=== 执行统计信息 ===")
        print(f"总节点数: {stats['total_nodes']}")
        print(f"根节点数: {stats['total_roots']}")
        print(f"并行执行组数: {stats['parallel_execution_count']}")
        
        print("\n运行类型分布:")
        for run_type, count in stats["run_types"].items():
            print(f"  {run_type}: {count}")
        
        print("\n状态分布:")
        for status, count in stats["status_count"].items():
            print(f"  {status}: {count}")
        
        print("\n耗时最多的20个节点:")
        for i, (name, latency, run_type) in enumerate(stats["top_slowest_nodes"], 1):
            print(f"  {i:2d}. {name} ({run_type}): {latency:.6f}s")
    
    def export_to_json(self, output_file: str) -> None:
        """导出到JSON文件"""
        def node_to_dict(node: TreeNode) -> Dict[str, Any]:
            return {
                "run_id": node.run_id,
                "parent_run_id": node.parent_run_id,
                "trace_id": node.trace_id,
                "name": node.name,
                "run_type": node.run_type,
                "start_time": node.start_time,
                "end_time": node.end_time,
                "latency_seconds": node.latency_seconds,
                "status": node.status,
                "level": node.level,
                "inputs": node.inputs,
                "outputs": node.outputs,
                "children": [node_to_dict(child) for child in node.children]
            }
        
        export_data = {
            "roots": [node_to_dict(root) for root in self.roots],
            "statistics": self.generate_statistics()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"树结构已导出到: {output_file}")
    
    def analyze(self) -> None:
        """执行完整分析"""
        self.parse_csv_data()
        self.build_tree_structure()
        self.print_tree_structure()
        self.print_statistics()


def main():
    parser = argparse.ArgumentParser(description="LangGraph跟踪树状图可视化工具")
    parser.add_argument("csv_file", help="CSV文件路径")
    parser.add_argument("--export", help="导出结果到JSON文件")
    parser.add_argument("--stats-only", action="store_true", help="只显示统计信息")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"错误: 文件 {args.csv_file} 不存在")
        sys.exit(1)
    
    visualizer = LangGraphTreeVisualizer(args.csv_file)
    visualizer.parse_csv_data()
    visualizer.build_tree_structure()
    
    if args.stats_only:
        visualizer.print_statistics()
    else:
        visualizer.print_tree_structure()
        visualizer.print_statistics()
    
    if args.export:
        visualizer.export_to_json(args.export)


if __name__ == "__main__":
    main()