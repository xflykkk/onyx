"""
流式响应内容监听器
用于调试和分析 SSE 流式数据
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List
from collections.abc import Generator

from onyx.configs.app_configs import ENABLE_STREAM_LOGGING, STREAM_LOG_DIR


class StreamLogger:
    """流式内容监听器，记录所有 SSE 数据包到文件"""
    
    def __init__(self, request_info: Dict[str, Any] = None):
        self.request_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.request_info = request_info or {}
        
        # 创建日志目录
        self.log_dir = STREAM_LOG_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 生成日志文件路径
        self.log_file = os.path.join(
            self.log_dir, 
            f"stream_{self.timestamp}_{self.request_id}.json"
        )
        
        # 存储所有数据包
        self.packets: List[Dict[str, Any]] = []
        self.packet_count = 0
        
        # 初始化日志文件
        self._init_log_file()
    
    def _init_log_file(self):
        """初始化日志文件，写入元数据"""
        metadata = {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "start_time": datetime.now().isoformat(),
            "request_info": self._serialize_request_info(self.request_info),
            "packets": []
        }
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"📝 Stream log initialized: {self.log_file}")
    
    def _serialize_request_info(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """序列化请求信息，处理不能 JSON 序列化的对象"""
        serialized = {}
        for key, value in request_info.items():
            try:
                # 尝试序列化值
                json.dumps(value)
                serialized[key] = value
            except TypeError:
                # 如果不能序列化，转换为字符串
                serialized[key] = str(value)
        return serialized
    
    def log_packet(self, packet_data: str, packet_type: str = "sse"):
        """记录单个数据包"""
        self.packet_count += 1
        
        # 解析 JSON 数据包
        try:
            parsed_data = json.loads(packet_data) if packet_data.strip() else {}
        except json.JSONDecodeError:
            parsed_data = {"raw_content": packet_data}
        
        packet_entry = {
            "sequence": self.packet_count,
            "timestamp": datetime.now().isoformat(),
            "type": packet_type,
            "raw_data": packet_data,
            "parsed_data": parsed_data,
            "data_size": len(packet_data)
        }
        
        self.packets.append(packet_entry)
        
        # 实时写入文件（追加模式）
        self._append_packet_to_file(packet_entry)
        
        # 控制台输出（仅在启用流日志时）
        if ENABLE_STREAM_LOGGING:
            print(f"📦 #{self.packet_count} {packet_type}: {packet_data[:100]}...")
    
    def _append_packet_to_file(self, packet_entry: Dict[str, Any]):
        """追加数据包到文件"""
        try:
            # 读取现有内容
            with open(self.log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 添加新数据包
            data["packets"].append(packet_entry)
            data["packet_count"] = self.packet_count
            data["last_update"] = datetime.now().isoformat()
            
            # 写回文件
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ Error writing to stream log: {e}")
    
    def finalize(self):
        """完成日志记录，写入汇总信息"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 添加汇总信息
            data.update({
                "end_time": datetime.now().isoformat(),
                "total_packets": self.packet_count,
                "total_size": sum(len(p.get("raw_data", "")) for p in self.packets),
                "packet_types": self._get_packet_type_stats(),
                "complete": True
            })
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Stream log finalized: {self.log_file}")
            print(f"📊 Total packets: {self.packet_count}, Types: {data['packet_types']}")
            
        except Exception as e:
            print(f"❌ Error finalizing stream log: {e}")
    
    def _get_packet_type_stats(self) -> Dict[str, int]:
        """统计不同类型数据包的数量"""
        stats = {}
        for packet in self.packets:
            parsed = packet.get("parsed_data", {})
            
            # 识别数据包类型
            if "answer_piece" in parsed:
                packet_type = "answer_piece"
            elif "sub_question" in parsed:
                packet_type = "sub_question"
            elif "sub_query" in parsed:
                packet_type = "sub_query"
            elif "top_documents" in parsed:
                packet_type = "documents"
            elif "context_docs" in parsed:
                packet_type = "context_docs"
            elif "thinking_content" in parsed:
                packet_type = "thinking"
            elif "error" in parsed:
                packet_type = "error"
            elif "message" in parsed and "message_id" in parsed:
                packet_type = "message_detail"
            else:
                packet_type = "other"
            
            stats[packet_type] = stats.get(packet_type, 0) + 1
        
        return stats


def create_stream_logger_wrapper(original_generator: Generator[str, None, None], 
                                request_info: Dict[str, Any] = None) -> Generator[str, None, None]:
    """
    包装原始流生成器，添加日志记录功能
    
    Args:
        original_generator: 原始的流生成器
        request_info: 请求信息（可选）
    
    Returns:
        包装后的流生成器
    """
    # 检查是否启用流日志
    if not ENABLE_STREAM_LOGGING:
        # 如果未启用，直接返回原始生成器
        yield from original_generator
        return
    
    logger = StreamLogger(request_info)
    
    try:
        for packet in original_generator:
            # 记录数据包
            logger.log_packet(packet, "sse")
            
            # 继续传递数据包给客户端
            yield packet
            
    except Exception as e:
        # 记录错误
        error_packet = json.dumps({"error": str(e), "error_type": "stream_wrapper_error"})
        logger.log_packet(error_packet, "error")
        
        # 重新抛出异常
        raise
        
    finally:
        # 完成日志记录
        logger.finalize()


# 便捷函数：创建请求信息字典
def create_request_info(chat_message_req=None, user=None, **kwargs) -> Dict[str, Any]:
    """创建请求信息字典"""
    info = {
        "timestamp": datetime.now().isoformat(),
        **kwargs
    }
    
    if chat_message_req:
        info.update({
            "message": getattr(chat_message_req, "message", None),
            "chat_session_id": getattr(chat_message_req, "chat_session_id", None),
            "persona_id": getattr(chat_message_req, "persona_id", None),
            "use_agentic_search": getattr(chat_message_req, "use_agentic_search", None),
        })
    
    if user:
        info.update({
            "user_id": getattr(user, "id", None),
            "user_email": getattr(user, "email", None),
        })
    
    return info