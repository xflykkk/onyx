#!/usr/bin/env python3
"""
Script to test the streaming fix for sub-questions.
This script helps verify that sub-questions are properly handled in the streaming response.
"""

import json
from datetime import datetime
from pathlib import Path

def analyze_stream_log(log_file_path):
    """Analyze a stream log file to check sub-question handling."""
    print(f"Analyzing stream log: {log_file_path}")
    print("=" * 80)
    
    with open(log_file_path, 'r') as f:
        data = json.load(f)
    
    # Analyze sub-questions
    sub_questions = {}
    sub_question_packets = 0
    sub_queries = {}
    sub_query_packets = 0
    
    for packet in data.get('packets', []):
        raw_data = packet.get('raw_data', {})
        
        # Check for sub_question packets
        if 'sub_question' in raw_data:
            sub_question_packets += 1
            level = raw_data.get('level', 0)
            level_question_num = raw_data.get('level_question_num', 0)
            key = (level, level_question_num)
            
            if key not in sub_questions:
                sub_questions[key] = {
                    'question': '',
                    'packets': 0,
                    'is_complete': False
                }
            
            sub_questions[key]['question'] += raw_data['sub_question']
            sub_questions[key]['packets'] += 1
            
            # Check for completion
            if raw_data.get('stop_reason') == 'FINISHED':
                sub_questions[key]['is_complete'] = True
        
        # Check for sub_query packets
        if 'sub_query' in raw_data:
            sub_query_packets += 1
            level = raw_data.get('level', 0)
            level_question_num = raw_data.get('level_question_num', 0)
            query_id = raw_data.get('query_id', 0)
            key = (level, level_question_num, query_id)
            
            if key not in sub_queries:
                sub_queries[key] = {
                    'query': '',
                    'packets': 0
                }
            
            sub_queries[key]['query'] += raw_data['sub_query']
            sub_queries[key]['packets'] += 1
    
    # Print analysis results
    print(f"\n📊 SUMMARY:")
    print(f"Total packets: {len(data.get('packets', []))}")
    print(f"Sub-question packets: {sub_question_packets}")
    print(f"Sub-query packets: {sub_query_packets}")
    
    print(f"\n❓ SUB-QUESTIONS ({len(sub_questions)} total):")
    for (level, level_num), info in sorted(sub_questions.items()):
        cleaned_question = info['question'].replace('<sub-question>', '').replace('</sub-question>', '').strip()
        print(f"  [{level}.{level_num}] {cleaned_question}")
        print(f"        Packets: {info['packets']}, Complete: {info['is_complete']}")
    
    print(f"\n🔍 SUB-QUERIES ({len(sub_queries)} total):")
    for (level, level_num, query_id), info in sorted(sub_queries.items()):
        cleaned_query = info['query'].replace('<query', '').replace('</query', '').replace('>', '').strip()
        # Remove query numbers like "1", "2" from the beginning
        cleaned_query = ' '.join(cleaned_query.split()[1:]) if cleaned_query.split() else cleaned_query
        print(f"  [{level}.{level_num}.{query_id}] {cleaned_query}")
        print(f"        Packets: {info['packets']}")
    
    # Check for issues
    print(f"\n⚠️  POTENTIAL ISSUES:")
    issues_found = False
    
    # Check for incomplete sub-questions
    incomplete_questions = [(k, v) for k, v in sub_questions.items() if not v['is_complete']]
    if incomplete_questions:
        issues_found = True
        print(f"  - Found {len(incomplete_questions)} incomplete sub-questions")
    
    # Check for sub-questions with HTML tags
    tagged_questions = [(k, v) for k, v in sub_questions.items() if '<sub-question>' in v['question']]
    if tagged_questions:
        issues_found = True
        print(f"  - Found {len(tagged_questions)} sub-questions with HTML tags")
    
    # Check for fragmented sub-questions (too many packets)
    fragmented_questions = [(k, v) for k, v in sub_questions.items() if v['packets'] > 10]
    if fragmented_questions:
        issues_found = True
        print(f"  - Found {len(fragmented_questions)} highly fragmented sub-questions")
    
    if not issues_found:
        print("  ✅ No issues found!")
    
    print("\n" + "=" * 80)

def find_latest_log():
    """Find the latest stream log file."""
    log_dir = Path("/tmp/onyx_stream_logs")
    if not log_dir.exists():
        print(f"Log directory {log_dir} does not exist")
        return None
    
    log_files = list(log_dir.glob("stream_*.json"))
    if not log_files:
        print(f"No stream log files found in {log_dir}")
        return None
    
    # Sort by modification time and get the latest
    latest = max(log_files, key=lambda p: p.stat().st_mtime)
    return latest

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Use provided log file
        log_file = Path(sys.argv[1])
    else:
        # Find latest log file
        log_file = find_latest_log()
    
    if log_file and log_file.exists():
        analyze_stream_log(log_file)
    else:
        print("No valid log file found. Please provide a log file path or ensure stream logging is enabled.")
        print("Usage: python test_streaming_fix.py [log_file_path]")