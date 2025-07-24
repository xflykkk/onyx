#!/usr/bin/env python3
"""
Stream Logs API
用于获取和分析 SSE 流式数据日志
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from onyx.configs.app_configs import STREAM_LOG_DIR


router = APIRouter(prefix="/stream-logs")


class StreamLogSummary(BaseModel):
    """流式日志摘要信息"""
    request_id: str
    timestamp: str
    start_time: str
    end_time: Optional[str]
    total_packets: int
    total_size: int
    complete: bool
    user_email: Optional[str]
    message: Optional[str]
    chat_session_id: Optional[str]
    use_agentic_search: Optional[bool]
    packet_types: Dict[str, int]


class StreamLogPacket(BaseModel):
    """单个数据包信息"""
    sequence: int
    timestamp: str
    packet_type: str
    data_size: int
    parsed_data: Dict[str, Any]
    raw_data: str


class StreamLogDetail(BaseModel):
    """完整的流式日志详情"""
    summary: StreamLogSummary
    packets: List[StreamLogPacket]
    sub_questions: List[Dict[str, Any]]
    sub_queries: List[Dict[str, Any]]
    documents_count: int
    answer_length: int


def list_log_files(log_dir: str = STREAM_LOG_DIR) -> List[str]:
    """列出所有日志文件"""
    if not os.path.exists(log_dir):
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
        raise HTTPException(status_code=500, detail=f"加载日志文件失败: {e}")


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


def analyze_log_data(log_data: Dict[str, Any]) -> StreamLogDetail:
    """分析日志数据并返回结构化信息"""
    # 基本摘要信息
    request_info = log_data.get('request_info', {})
    summary = StreamLogSummary(
        request_id=log_data.get('request_id', ''),
        timestamp=log_data.get('timestamp', ''),
        start_time=log_data.get('start_time', ''),
        end_time=log_data.get('end_time'),
        total_packets=log_data.get('total_packets', 0),
        total_size=log_data.get('total_size', 0),
        complete=log_data.get('complete', False),
        user_email=request_info.get('user_email'),
        message=request_info.get('message'),
        chat_session_id=request_info.get('chat_session_id'),
        use_agentic_search=request_info.get('use_agentic_search'),
        packet_types=log_data.get('packet_types', {})
    )
    
    # 处理数据包
    packets = []
    sub_questions = []
    sub_queries = []
    documents_count = 0
    answer_length = 0
    
    for i, packet in enumerate(log_data.get('packets', [])):
        parsed = packet.get('parsed_data', {})
        packet_type = identify_packet_type(parsed)
        
        # 创建数据包信息
        stream_packet = StreamLogPacket(
            sequence=packet.get('sequence', i + 1),
            timestamp=packet.get('timestamp', ''),
            packet_type=packet_type,
            data_size=packet.get('data_size', 0),
            parsed_data=parsed,
            raw_data=packet.get('raw_data', '')
        )
        packets.append(stream_packet)
        
        # 分析特定类型的数据包
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
        elif 'top_documents' in parsed:
            documents_count += len(parsed['top_documents'])
        elif 'answer_piece' in parsed and parsed.get('answer_type') != 'agent_sub_answer':
            answer_length += len(parsed.get('answer_piece', ''))
    
    return StreamLogDetail(
        summary=summary,
        packets=packets,
        sub_questions=sub_questions,
        sub_queries=sub_queries,
        documents_count=documents_count,
        answer_length=answer_length
    )


@router.get("/latest", response_model=StreamLogDetail)
async def get_latest_stream_log():
    """获取最新的流式日志详情"""
    files = list_log_files()
    
    if not files:
        raise HTTPException(status_code=404, detail="没有找到流式日志文件")
    
    # 获取最新的完整日志文件
    for file_path in files:
        try:
            log_data = load_log_file(file_path)
            if log_data.get('complete'):
                return analyze_log_data(log_data)
        except Exception:
            continue
    
    raise HTTPException(status_code=404, detail="没有找到完整的流式日志文件")


@router.get("/list")
async def list_stream_logs():
    """列出所有可用的流式日志文件"""
    files = list_log_files()
    
    log_files = []
    for file_path in files[:20]:  # 只返回最新的20个
        try:
            log_data = load_log_file(file_path)
            file_name = os.path.basename(file_path)
            log_files.append({
                'filename': file_name,
                'file_path': file_path,
                'timestamp': log_data.get('timestamp', ''),
                'start_time': log_data.get('start_time', ''),
                'complete': log_data.get('complete', False),
                'total_packets': log_data.get('total_packets', 0),
                'user_email': log_data.get('request_info', {}).get('user_email', ''),
                'message_preview': log_data.get('request_info', {}).get('message', '')[:50] + '...' if log_data.get('request_info', {}).get('message') else ''
            })
        except Exception:
            continue
    
    return {'log_files': log_files}


@router.get("/{filename}", response_model=StreamLogDetail)
async def get_stream_log_by_filename(filename: str):
    """根据文件名获取特定的流式日志"""
    if not filename.startswith("stream_") or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="无效的日志文件名格式")
    
    file_path = os.path.join(STREAM_LOG_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"日志文件不存在: {filename}")
    
    log_data = load_log_file(file_path)
    return analyze_log_data(log_data)


@router.get("/{filename}/raw")
async def get_stream_log_raw_content(filename: str):
    """获取原始日志文件内容"""
    if not filename.startswith("stream_") or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="无效的日志文件名格式")
    
    file_path = os.path.join(STREAM_LOG_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"日志文件不存在: {filename}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        return {"filename": filename, "raw_content": raw_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {e}")


@router.get("/summary/stats")
async def get_stream_logs_stats():
    """获取流式日志统计信息"""
    files = list_log_files()
    
    if not files:
        return {
            'total_logs': 0,
            'complete_logs': 0,
            'latest_log_time': None,
            'total_size': 0
        }
    
    complete_logs = 0
    total_size = 0
    latest_log_time = None
    
    for file_path in files:
        try:
            log_data = load_log_file(file_path)
            if log_data.get('complete'):
                complete_logs += 1
            total_size += log_data.get('total_size', 0)
            
            if not latest_log_time and log_data.get('start_time'):
                latest_log_time = log_data.get('start_time')
        except Exception:
            continue
    
    return {
        'total_logs': len(files),
        'complete_logs': complete_logs,
        'latest_log_time': latest_log_time,
        'total_size': total_size
    }