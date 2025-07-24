"""
LangSmith 特定 Trace 深度数据导出工具

专门用于导出指定 trace 名称的最新一条数据及其所有子运行的详细信息
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from langsmith import Client


class LangSmithTraceExporter:
    """LangSmith Trace 深度导出工具类"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 LangSmith 客户端
        
        Args:
            api_key: LangSmith API 密钥
        """
        self.client = Client(api_key=api_key)
    
    def _truncate_field(self, value: Any, max_length: int = 400) -> str:
        """
        截断字段内容到指定长度
        
        Args:
            value: 要截断的值
            max_length: 最大长度
            
        Returns:
            截断后的字符串
        """
        if value is None:
            return None
        
        str_value = str(value)
        if len(str_value) <= max_length:
            return str_value
        
        # 截断并添加省略号标记
        return str_value[:max_length - 3] + "..."
    
    def export_latest_trace_with_details(self,
                                       project_name: str,
                                       trace_name: str,
                                       days_back: int = 7) -> Dict[str, pd.DataFrame]:
        """
        导出指定名称的最新 trace 及其所有子运行的详细数据
        
        Args:
            project_name: 项目名称
            trace_name: Trace 名称（如 "LangGraph"）
            days_back: 查询过去多少天的数据
            
        Returns:
            包含多个 DataFrame 的字典：
            - trace_info: 主 trace 信息
            - all_runs: 该 trace 下的所有运行（包括嵌套）
            - run_hierarchy: 运行层级关系
            - run_details: 每个运行的详细信息
        """
        print(f"正在查找项目 '{project_name}' 中名为 '{trace_name}' 的最新 trace...")
        
        # 1. 查找最新的指定名称的 trace
        traces = list(self.client.list_runs(
            project_name=project_name,
            start_time=datetime.now() - timedelta(days=days_back),
            is_root=True,
            filter=f'eq(name, "{trace_name}")',
            limit=1  # 只获取最新的一条
        ))
        
        if not traces:
            print(f"未找到名为 '{trace_name}' 的 trace")
            return {}
        
        latest_trace = traces[0]
        trace_id = latest_trace.id
        print(f"找到最新 trace: {trace_id}")
        print(f"创建时间: {latest_trace.start_time}")
        
        result = {}
        
        # 2. 收集 trace 基本信息
        trace_info = {
            "trace_id": trace_id,
            "name": latest_trace.name,
            "start_time": latest_trace.start_time,
            "end_time": latest_trace.end_time,
            "latency_seconds": (latest_trace.end_time - latest_trace.start_time).total_seconds() if latest_trace.end_time and latest_trace.start_time else None,
            "status": latest_trace.status,
            "error": self._truncate_field(latest_trace.error, 400) if latest_trace.error else None,
            "inputs": self._truncate_field(json.dumps(latest_trace.inputs, ensure_ascii=False), 400) if latest_trace.inputs else None,
            "outputs": self._truncate_field(json.dumps(latest_trace.outputs, ensure_ascii=False), 400) if latest_trace.outputs else None,
            "metadata": self._truncate_field(json.dumps(latest_trace.extra.get('metadata', {}), ensure_ascii=False), 400) if latest_trace.extra else None,
            "tags": latest_trace.extra.get('tags', []) if latest_trace.extra else [],
            "total_tokens": getattr(latest_trace, 'total_tokens', None),
            "total_cost": getattr(latest_trace, 'total_cost', None)
        }
        result['trace_info'] = pd.DataFrame([trace_info])
        
        # 3. 获取该 trace 下的所有运行
        print(f"正在获取 trace {trace_id} 下的所有运行...")
        all_runs = list(self.client.list_runs(
            project_name=project_name,
            filter=f'eq(trace_id, "{trace_id}")'
        ))
        
        print(f"找到 {len(all_runs)} 个相关运行")
        
        # 4. 构建运行数据
        runs_data = []
        hierarchy_data = []
        
        # 创建运行映射以构建层级关系
        run_map = {run.id: run for run in all_runs}
        
        for run in all_runs:
            # 基本运行信息
            run_data = {
                "run_id": run.id,
                "parent_run_id": run.parent_run_id,
                "trace_id": run.trace_id,
                "name": run.name,
                "run_type": run.run_type,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "latency_seconds": (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else None,
                "status": run.status,
                "error": self._truncate_field(run.error, 400) if run.error else None,
                "inputs": self._truncate_field(json.dumps(run.inputs, ensure_ascii=False), 400) if run.inputs else None,
                "outputs": self._truncate_field(json.dumps(run.outputs, ensure_ascii=False), 400) if run.outputs else None,
                "metadata": self._truncate_field(json.dumps(run.extra.get('metadata', {}), ensure_ascii=False), 200) if run.extra else None,
                "tags": str(run.extra.get('tags', []))[:100] if run.extra else "[]",
                "token_count": getattr(run, 'total_tokens', None),
                "prompt_tokens": getattr(run, 'prompt_tokens', None),
                "completion_tokens": getattr(run, 'completion_tokens', None),
                "cost": getattr(run, 'cost', None)
            }
            runs_data.append(run_data)
            
            # 构建层级关系
            level = 0
            current_parent_id = run.parent_run_id
            parent_chain = []
            
            # 追溯到根节点
            while current_parent_id and current_parent_id in run_map:
                level += 1
                parent_run = run_map[current_parent_id]
                parent_chain.insert(0, parent_run.name)
                current_parent_id = parent_run.parent_run_id
            
            hierarchy_data.append({
                "run_id": run.id,
                "name": run.name,
                "run_type": run.run_type,
                "level": level,
                "parent_run_id": run.parent_run_id,
                "parent_chain": " > ".join(parent_chain) if parent_chain else "ROOT",
                "full_path": " > ".join(parent_chain + [run.name]) if parent_chain else run.name,
                "is_root": run.id == trace_id
            })
        
        # 5. 创建 DataFrames
        result['all_runs'] = pd.DataFrame(runs_data)
        result['run_hierarchy'] = pd.DataFrame(hierarchy_data)
        
        # 按层级和开始时间排序
        result['run_hierarchy'] = result['run_hierarchy'].sort_values(['level', 'name'])
        result['all_runs'] = result['all_runs'].sort_values('start_time')
        
        # 6. 生成统计摘要
        summary_data = {
            "trace_id": trace_id,
            "trace_name": trace_name,
            "total_runs": len(all_runs),
            "run_types": result['all_runs']['run_type'].value_counts().to_dict(),
            "total_latency_seconds": trace_info['latency_seconds'],
            "successful_runs": len(result['all_runs'][result['all_runs']['error'].isna()]),
            "failed_runs": len(result['all_runs'][result['all_runs']['error'].notna()]),
            "total_tokens": result['all_runs']['token_count'].sum(),
            "total_cost": result['all_runs']['cost'].sum() if 'cost' in result['all_runs'].columns else None,
            "max_depth": result['run_hierarchy']['level'].max(),
            "unique_run_names": result['all_runs']['name'].nunique()
        }
        result['summary'] = pd.DataFrame([summary_data])
        
        # 7. 创建运行类型详细统计
        run_type_stats = []
        for run_type in result['all_runs']['run_type'].unique():
            type_runs = result['all_runs'][result['all_runs']['run_type'] == run_type]
            run_type_stats.append({
                "run_type": run_type,
                "count": len(type_runs),
                "avg_latency_seconds": type_runs['latency_seconds'].mean(),
                "total_tokens": type_runs['token_count'].sum(),
                "unique_names": type_runs['name'].nunique(),
                "names": list(type_runs['name'].unique())
            })
        result['run_type_stats'] = pd.DataFrame(run_type_stats)
        
        print("\n导出完成！")
        print(f"- Trace ID: {trace_id}")
        print(f"- 总运行数: {len(all_runs)}")
        print(f"- 运行类型: {', '.join(result['all_runs']['run_type'].unique())}")
        print(f"- 最大嵌套深度: {result['run_hierarchy']['level'].max()}")
        
        return result
    
    def save_to_excel(self, data: Dict[str, pd.DataFrame], filename: str):
        """
        将所有数据保存到一个 Excel 文件的不同工作表中
        
        Args:
            data: 包含多个 DataFrame 的字典
            filename: 输出文件名（不包含扩展名）
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"{filename}_{timestamp}.xlsx"
        
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            for sheet_name, df in data.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                    
                    # 调整列宽
                    worksheet = writer.sheets[sheet_name[:31]]
                    for idx, col in enumerate(df.columns):
                        # 设置合理的列宽，最大不超过 50
                        max_len = max(
                            len(str(col)),  # 列名长度
                            df[col].astype(str).str.len().max() if not df[col].empty else 10  # 内容最大长度
                        )
                        worksheet.column_dimensions[chr(65 + idx % 26)].width = min(50, max(12, max_len * 0.15 + 5))
        
        print(f"\n数据已保存到: {excel_filename}")
        return excel_filename
    
    def save_full_data(self, data: Dict[str, pd.DataFrame], runs_df: pd.DataFrame, filename_prefix: str):
        """
        保存完整数据到单独的 JSON 文件（针对需要查看完整内容的情况）
        
        Args:
            data: 原始数据字典
            runs_df: 包含所有运行的 DataFrame
            filename_prefix: 文件名前缀
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存特定运行的完整输入输出
        print("\n是否需要保存某些运行的完整输入输出数据？(y/n): ", end="")
        if input().lower() == 'y':
            print("请输入要保存完整数据的运行名称（用逗号分隔，如: ChatOpenAI,LangGraph）: ", end="")
            run_names = [name.strip() for name in input().split(',')]
            
            for run_name in run_names:
                matching_runs = runs_df[runs_df['name'] == run_name]
                if not matching_runs.empty:
                    for idx, run in matching_runs.iterrows():
                        run_id = run['run_id']
                        # 获取原始完整数据
                        full_run = self.client.read_run(run_id)
                        
                        full_data = {
                            "run_id": str(run_id),
                            "name": run_name,
                            "inputs": full_run.inputs,
                            "outputs": full_run.outputs,
                            "metadata": full_run.extra.get('metadata', {}) if full_run.extra else {}
                        }
                        
                        json_filename = f"{filename_prefix}_{run_name}_{run_id[:8]}_{timestamp}.json"
                        with open(json_filename, 'w', encoding='utf-8') as f:
                            json.dump(full_data, f, ensure_ascii=False, indent=2)
                        print(f"完整数据已保存到: {json_filename}")
    
    def print_hierarchy_tree(self, hierarchy_df: pd.DataFrame):
        """
        以树形结构打印运行层级
        
        Args:
            hierarchy_df: 包含层级信息的 DataFrame
        """
        print("\n运行层级结构:")
        print("-" * 80)
        
        for _, row in hierarchy_df.iterrows():
            indent = "  " * row['level']
            prefix = "└─ " if row['level'] > 0 else ""
            print(f"{indent}{prefix}{row['name']} ({row['run_type']})")


# 使用示例
if __name__ == "__main__":
    # 配置
    API_KEY = "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"  # 替换为你的 API key
    PROJECT_NAME = "ai_corp_dev"  # 替换为你的项目名
    TRACE_NAME = "LangGraph"  # 要查找的 trace 名称
    
    # 初始化导出器
    exporter = LangSmithTraceExporter(api_key=API_KEY)
    
    # 导出最新的 LangGraph trace 的所有数据
    trace_data = exporter.export_latest_trace_with_details(
        project_name=PROJECT_NAME,
        trace_name=TRACE_NAME,
        days_back=7  # 查找过去 7 天的数据
    )
    
    if trace_data:
        # 打印层级结构
        if 'run_hierarchy' in trace_data:
            exporter.print_hierarchy_tree(trace_data['run_hierarchy'])
        
        # 打印统计信息
        if 'summary' in trace_data:
            print("\n统计摘要:")
            print("-" * 80)
            summary = trace_data['summary'].iloc[0]
            print(f"总运行数: {summary['total_runs']}")
            print(f"成功运行: {summary['successful_runs']}")
            print(f"失败运行: {summary['failed_runs']}")
            print(f"总耗时: {summary['total_latency_seconds']:.2f} 秒")
            print(f"最大嵌套深度: {summary['max_depth']}")
            
        # 打印运行类型统计
        if 'run_type_stats' in trace_data:
            print("\n运行类型统计:")
            print("-" * 80)
            print(trace_data['run_type_stats'][['run_type', 'count', 'avg_latency_seconds']])
        
        # 保存到 Excel
        output_filename = f"{TRACE_NAME}_trace_export"
        exporter.save_to_excel(trace_data, output_filename)
        
        # 也可以单独保存某些数据为 CSV
        if 'all_runs' in trace_data:
            csv_filename = f"{output_filename}_runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            trace_data['all_runs'].to_csv(csv_filename, index=False)
            print(f"运行详情已额外保存到: {csv_filename}")
    else:
        print(f"\n未找到名为 '{TRACE_NAME}' 的 trace")