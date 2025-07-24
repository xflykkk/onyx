#!/usr/bin/env python3
"""
并发 Embedding 性能测试工具

测试场景：
- 并发 3 个请求
- 每个请求包含多个文本块（模拟 indexing 过程中的批量处理）
- 单条文本约 1000 tokens
- 记录详细的耗时统计
"""

import asyncio
import aiohttp
import time
import json
import random
import string
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
import requests


@dataclass
class EmbeddingRequest:
    """Embedding 请求数据"""
    request_id: str
    texts: List[str]
    model: str = "openai/qwen3-embedding-0.6b"


@dataclass
class EmbeddingResult:
    """Embedding 结果数据"""
    request_id: str
    success: bool
    start_time: float
    end_time: float
    duration: float
    text_count: int
    total_chars: int
    embedding_dimensions: List[int] = None  # 每个文本的向量维度
    error_message: str = ""


class ConcurrentEmbeddingTester:
    """并发 Embedding 测试器"""
    
    def __init__(self, 
                 api_url: str = "http://172.16.0.120:1234/v1/embeddings",
                 api_key: str = "sk-Zd7gzQGylVwOyUUMvOBhow"):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.results: List[EmbeddingResult] = []
        self.lock = threading.Lock()
    
    def generate_test_text(self, target_tokens: int = 1000) -> str:
        """生成指定 token 数量的测试文本"""
        # 估算：平均 1 token ≈ 4 个字符（对于中英文混合）
        target_chars = target_tokens * 4
        
        # 生成技术文档风格的文本
        base_texts = [
            "人工智能技术在现代社会中发挥着越来越重要的作用。机器学习算法通过大量数据的训练，能够识别复杂的模式并做出预测。",
            "深度学习是机器学习的一个分支，它使用多层神经网络来模拟人脑的工作方式。卷积神经网络（CNN）特别适用于图像识别任务。",
            "自然语言处理（NLP）技术使计算机能够理解和生成人类语言。Transformer架构的出现极大地推进了这一领域的发展。",
            "云计算平台提供了弹性的计算资源，使得大规模的AI模型训练成为可能。容器化技术如Docker简化了应用部署流程。",
            "数据科学结合了统计学、计算机科学和领域专业知识，帮助从数据中提取有价值的洞察。数据可视化是传达发现的重要工具。",
            "The rapid advancement of artificial intelligence has transformed various industries including healthcare, finance, and transportation.",
            "Machine learning algorithms require careful feature engineering and hyperparameter tuning to achieve optimal performance on specific tasks.",
            "Computer vision systems can now perform tasks such as object detection, facial recognition, and medical image analysis with high accuracy.",
            "Big data technologies like Hadoop and Spark enable processing of massive datasets that were previously impossible to handle efficiently.",
            "Cybersecurity has become increasingly important as organizations digitize their operations and store sensitive information in cloud environments."
        ]
        
        # 随机组合文本直到达到目标长度
        result = ""
        while len(result) < target_chars:
            result += random.choice(base_texts) + " "
            
            # 添加一些随机的技术术语
            tech_terms = ["API", "REST", "GraphQL", "microservices", "containers", "Kubernetes", 
                         "DevOps", "CI/CD", "monitoring", "scalability", "performance", "optimization"]
            result += f"The implementation uses {random.choice(tech_terms)} technology for better {random.choice(tech_terms)}. "
        
        return result[:target_chars]
    
    def generate_test_requests(self, num_requests: int = 3) -> List[EmbeddingRequest]:
        """生成测试请求"""
        requests = []
        
        # 模拟不同的文档大小场景
        scenarios = [
            {"name": "small_doc", "text_count": 7, "tokens_per_text": 800},   # 小文档：7个块
            {"name": "medium_doc", "text_count": 15, "tokens_per_text": 1000}, # 中等文档：15个块  
            {"name": "large_doc", "text_count": 27, "tokens_per_text": 1200},  # 大文档：27个块
        ]
        
        for i in range(num_requests):
            scenario = scenarios[i % len(scenarios)]
            texts = []
            
            # 生成该请求的所有文本块
            for j in range(scenario["text_count"]):
                text = self.generate_test_text(scenario["tokens_per_text"])
                texts.append(text)
            
            request = EmbeddingRequest(
                request_id=f"req_{i+1}_{scenario['name']}",
                texts=texts
            )
            requests.append(request)
        
        return requests
    
    async def send_async_request(self, session: aiohttp.ClientSession, request: EmbeddingRequest) -> EmbeddingResult:
        """发送异步 embedding 请求"""
        start_time = time.time()
        
        payload = {
            "input": request.texts,
            "model": request.model
        }
        
        try:
            print(f"[{request.request_id}] 开始请求 - {len(request.texts)} 个文本")
            
            async with session.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=120)  # 2分钟超时
            ) as response:
                end_time = time.time()
                duration = end_time - start_time
                
                if response.status == 200:
                    result_data = await response.json()
                    embeddings = result_data.get("data", [])
                    
                    # 获取每个向量的维度
                    embedding_dimensions = []
                    for embedding in embeddings:
                        if "embedding" in embedding:
                            dim = len(embedding["embedding"])
                            embedding_dimensions.append(dim)
                    
                    total_chars = sum(len(text) for text in request.texts)
                    
                    result = EmbeddingResult(
                        request_id=request.request_id,
                        success=True,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        text_count=len(request.texts),
                        total_chars=total_chars,
                        embedding_dimensions=embedding_dimensions
                    )
                    
                    # 打印向量维度信息
                    if embedding_dimensions:
                        dim_info = f", 向量维度: {embedding_dimensions[0]}" if embedding_dimensions else ""
                        if len(set(embedding_dimensions)) > 1:
                            dim_info += f" (维度不一致: {set(embedding_dimensions)})"
                    else:
                        dim_info = ""
                    
                    print(f"[{request.request_id}] ✅ 成功 - 耗时: {duration:.2f}s, "
                          f"文本数: {len(request.texts)}, 字符数: {total_chars}{dim_info}")
                    
                    return result
                else:
                    error_text = await response.text()
                    print(f"[{request.request_id}] ❌ 失败 - 状态码: {response.status}, 错误: {error_text}")
                    
                    return EmbeddingResult(
                        request_id=request.request_id,
                        success=False,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        text_count=len(request.texts),
                        total_chars=sum(len(text) for text in request.texts),
                        embedding_dimensions=None,
                        error_message=f"HTTP {response.status}: {error_text}"
                    )
                    
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"[{request.request_id}] ❌ 异常 - 耗时: {duration:.2f}s, 错误: {str(e)}")
            
            return EmbeddingResult(
                request_id=request.request_id,
                success=False,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                text_count=len(request.texts),
                total_chars=sum(len(text) for text in request.texts),
                embedding_dimensions=None,
                error_message=str(e)
            )
    
    def send_sync_request(self, request: EmbeddingRequest) -> EmbeddingResult:
        """发送同步 embedding 请求（用于对比测试）"""
        start_time = time.time()
        
        payload = {
            "input": request.texts,
            "model": request.model
        }
        
        try:
            print(f"[{request.request_id}] 开始同步请求 - {len(request.texts)} 个文本")
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=120  # 2分钟超时
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                embeddings = result_data.get("data", [])
                
                # 获取每个向量的维度
                embedding_dimensions = []
                for embedding in embeddings:
                    if "embedding" in embedding:
                        dim = len(embedding["embedding"])
                        embedding_dimensions.append(dim)
                
                total_chars = sum(len(text) for text in request.texts)
                
                result = EmbeddingResult(
                    request_id=request.request_id,
                    success=True,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    text_count=len(request.texts),
                    total_chars=total_chars,
                    embedding_dimensions=embedding_dimensions
                )
                
                # 打印向量维度信息
                if embedding_dimensions:
                    dim_info = f", 向量维度: {embedding_dimensions[0]}" if embedding_dimensions else ""
                    if len(set(embedding_dimensions)) > 1:
                        dim_info += f" (维度不一致: {set(embedding_dimensions)})"
                else:
                    dim_info = ""
                
                print(f"[{request.request_id}] ✅ 同步成功 - 耗时: {duration:.2f}s, "
                      f"文本数: {len(request.texts)}, 字符数: {total_chars}{dim_info}")
                
                return result
            else:
                print(f"[{request.request_id}] ❌ 同步失败 - 状态码: {response.status_code}, 错误: {response.text}")
                
                return EmbeddingResult(
                    request_id=request.request_id,
                    success=False,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    text_count=len(request.texts),
                    total_chars=sum(len(text) for text in request.texts),
                    embedding_dimensions=None,
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"[{request.request_id}] ❌ 同步异常 - 耗时: {duration:.2f}s, 错误: {str(e)}")
            
            return EmbeddingResult(
                request_id=request.request_id,
                success=False,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                text_count=len(request.texts),
                total_chars=sum(len(text) for text in request.texts),
                embedding_dimensions=None,
                error_message=str(e)
            )
    
    async def run_concurrent_test(self, requests: List[EmbeddingRequest]) -> List[EmbeddingResult]:
        """运行并发测试"""
        print(f"\n🚀 开始并发测试 - {len(requests)} 个并发请求")
        print("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            # 创建并发任务
            tasks = [
                self.send_async_request(session, request) 
                for request in requests
            ]
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks)
            
        return results
    
    def run_sequential_test(self, requests: List[EmbeddingRequest]) -> List[EmbeddingResult]:
        """运行顺序测试（用于对比）"""
        print(f"\n📋 开始顺序测试 - {len(requests)} 个顺序请求")
        print("=" * 60)
        
        results = []
        for request in requests:
            result = self.send_sync_request(request)
            results.append(result)
        
        return results
    
    def print_results(self, results: List[EmbeddingResult], test_type: str = "并发"):
        """打印测试结果"""
        print(f"\n📊 {test_type}测试结果统计")
        print("=" * 60)
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        # 基本统计
        print(f"总请求数: {len(results)}")
        print(f"成功请求: {len(successful_results)}")
        print(f"失败请求: {len(failed_results)}")
        
        if successful_results:
            # 耗时统计
            durations = [r.duration for r in successful_results]
            total_duration = max(r.end_time for r in successful_results) - min(r.start_time for r in successful_results)
            
            print(f"\n⏱️ 耗时统计:")
            print(f"  总体耗时: {total_duration:.2f}s")
            print(f"  平均耗时: {sum(durations)/len(durations):.2f}s")
            print(f"  最快请求: {min(durations):.2f}s")
            print(f"  最慢请求: {max(durations):.2f}s")
            
            # 吞吐量统计
            total_texts = sum(r.text_count for r in successful_results)
            total_chars = sum(r.total_chars for r in successful_results)
            
            # 向量维度统计
            all_dimensions = []
            for r in successful_results:
                if r.embedding_dimensions:
                    all_dimensions.extend(r.embedding_dimensions)
            
            print(f"\n📈 吞吐量统计:")
            print(f"  总文本数: {total_texts}")
            print(f"  总字符数: {total_chars:,}")
            print(f"  文本处理速度: {total_texts/total_duration:.1f} texts/s")
            print(f"  字符处理速度: {total_chars/total_duration:,.0f} chars/s")
            
            if all_dimensions:
                unique_dims = set(all_dimensions)
                print(f"  向量维度: {list(unique_dims)} (共 {len(all_dimensions)} 个向量)")
                if len(unique_dims) > 1:
                    print(f"  ⚠️ 警告: 检测到不同的向量维度，可能存在问题")
            
            # 详细结果
            print(f"\n📋 详细结果:")
            for result in results:
                status = "✅" if result.success else "❌"
                
                # 向量维度信息
                dim_info = ""
                if result.success and result.embedding_dimensions:
                    unique_dims = set(result.embedding_dimensions)
                    if len(unique_dims) == 1:
                        dim_info = f", 向量维度: {list(unique_dims)[0]}"
                    else:
                        dim_info = f", 向量维度不一致: {unique_dims}"
                
                print(f"  {status} {result.request_id}: {result.duration:.2f}s, "
                      f"{result.text_count} texts, {result.total_chars:,} chars{dim_info}")
                if not result.success:
                    print(f"      错误: {result.error_message}")
        
        if failed_results:
            print(f"\n❌ 失败请求详情:")
            for result in failed_results:
                print(f"  {result.request_id}: {result.error_message}")
    
    def run_comparison_test(self) -> Dict[str, Any]:
        """运行对比测试（并发 vs 顺序）"""
        print("🔬 开始 Embedding 性能对比测试")
        print("=" * 80)
        
        # 生成测试请求
        test_requests = self.generate_test_requests(3)
        
        print(f"\n📝 测试场景:")
        for i, req in enumerate(test_requests, 1):
            total_chars = sum(len(text) for text in req.texts)
            avg_chars = total_chars // len(req.texts)
            print(f"  请求 {i} ({req.request_id}): {len(req.texts)} 个文本, "
                  f"平均 {avg_chars} 字符/文本 (~{avg_chars//4} tokens)")
        
        # 1. 运行并发测试
        start_time = time.time()
        concurrent_results = asyncio.run(self.run_concurrent_test(test_requests.copy()))
        concurrent_total_time = time.time() - start_time
        
        self.print_results(concurrent_results, "并发")
        
        # 2. 运行顺序测试
        print("\n" + "="*80)
        start_time = time.time()
        sequential_results = self.run_sequential_test(test_requests.copy())
        sequential_total_time = time.time() - start_time
        
        self.print_results(sequential_results, "顺序")
        
        # 3. 对比分析
        print(f"\n🔍 性能对比分析")
        print("=" * 60)
        
        concurrent_success = [r for r in concurrent_results if r.success]
        sequential_success = [r for r in sequential_results if r.success]
        
        if concurrent_success and sequential_success:
            concurrent_avg = sum(r.duration for r in concurrent_success) / len(concurrent_success)
            sequential_avg = sum(r.duration for r in sequential_success) / len(sequential_success)
            
            print(f"并发测试:")
            print(f"  总体完成时间: {concurrent_total_time:.2f}s")
            print(f"  平均单请求耗时: {concurrent_avg:.2f}s")
            
            print(f"\n顺序测试:")
            print(f"  总体完成时间: {sequential_total_time:.2f}s") 
            print(f"  平均单请求耗时: {sequential_avg:.2f}s")
            
            speedup = sequential_total_time / concurrent_total_time
            print(f"\n📊 性能提升:")
            print(f"  并发加速比: {speedup:.2f}x")
            print(f"  时间节省: {((sequential_total_time - concurrent_total_time) / sequential_total_time * 100):.1f}%")
            
            # 分析瓶颈
            if speedup < 2.5:  # 理论上3个并发应该接近3倍速度
                print(f"\n⚠️ 性能分析:")
                print(f"  预期加速比: ~3.0x (理想并发)")
                print(f"  实际加速比: {speedup:.2f}x")
                if speedup < 1.5:
                    print(f"  💡 建议: API服务可能存在并发瓶颈，考虑优化服务端性能")
                elif speedup < 2.0:
                    print(f"  💡 建议: 存在一定的并发开销，但整体性能良好")
                else:
                    print(f"  💡 建议: 并发性能良好，接近理想效果")
        
        return {
            "concurrent_results": concurrent_results,
            "sequential_results": sequential_results,
            "concurrent_total_time": concurrent_total_time,
            "sequential_total_time": sequential_total_time,
            "speedup": speedup if concurrent_success and sequential_success else 0
        }


def run_embedding_stress_test(duration_minutes: int = 5):
    """运行 embedding 压力测试"""
    print(f"🔥 开始 {duration_minutes} 分钟压力测试")
    print("=" * 60)
    
    tester = ConcurrentEmbeddingTester()
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    all_results = []
    round_count = 0
    
    while time.time() < end_time:
        round_count += 1
        remaining_time = end_time - time.time()
        
        print(f"\n🔄 第 {round_count} 轮测试 (剩余时间: {remaining_time/60:.1f} 分钟)")
        
        # 生成测试请求
        test_requests = tester.generate_test_requests(3)
        
        # 运行并发测试
        try:
            results = asyncio.run(tester.run_concurrent_test(test_requests))
            all_results.extend(results)
            
            # 简要统计
            success_count = len([r for r in results if r.success])
            avg_duration = sum(r.duration for r in results if r.success) / max(success_count, 1)
            
            print(f"  本轮结果: {success_count}/{len(results)} 成功, 平均耗时: {avg_duration:.2f}s")
            
        except Exception as e:
            print(f"  本轮测试失败: {e}")
        
        # 短暂休息，避免过度压力
        if time.time() < end_time:
            time.sleep(2)
    
    # 总结统计
    total_time = time.time() - start_time
    print(f"\n🏁 压力测试完成")
    print("=" * 60)
    print(f"测试时长: {total_time/60:.1f} 分钟")
    print(f"测试轮数: {round_count}")
    print(f"总请求数: {len(all_results)}")
    
    tester.print_results(all_results, "压力")


if __name__ == "__main__":
    print("🧪 Embedding 并发性能测试工具")
    print("=" * 80)
    
    # 检查测试模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stress":
        # 压力测试模式
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        run_embedding_stress_test(duration)
    else:
        # 标准对比测试模式
        tester = ConcurrentEmbeddingTester()
        results = tester.run_comparison_test()
        
        print(f"\n🎯 测试完成！")
        print(f"建议: 根据测试结果调整 Onyx 的 embedding 配置以获得最佳性能。")