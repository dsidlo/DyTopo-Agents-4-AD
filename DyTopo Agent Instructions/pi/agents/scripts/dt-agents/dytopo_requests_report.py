#!/usr/bin/env python3
"""
DyTopo Requests Report Generator

Pulls all DyTopo requests from Redis and displays:
- Request Date/Time
- Number of rounds
- Initial user request (from Round 0)
- Task description
- Workers involved
- Final status (if available)
"""

import redis
import json
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional


def get_redis_client(host='localhost', port=6379, db=0) -> Optional[redis.Redis]:
    """Connect to Redis and return client."""
    try:
        client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=5
        )
        client.ping()
        return client
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return None


def parse_request_key(key: str) -> Optional[Dict[str, Any]]:
    """
    Parse DyTopo Redis key format.
    
    Format examples:
    - Request-<YYYYmmDD-HHMMSS>:Task-<YYYYmmDD>:Round-<n>:From:DT-<Role>:To:DT-<Role>
    - Request-<YYYYmmDD-HHMMSS>:Final-Report
    """
    # Try message key pattern
    msg_pattern = r'Request-(\d{8}-\d{6}):Task-(\d{8}):Round-(\d+):From:DT-([\w-]+):To:DT-([\w-]+)'
    match = re.match(msg_pattern, key)
    
    if match:
        return {
            'type': 'message',
            'request_id': match.group(1),
            'task_id': match.group(2),
            'round': int(match.group(3)),
            'from_role': match.group(4),
            'to_role': match.group(5)
        }
    
    # Try final report pattern
    final_pattern = r'Request-(\d{8}-\d{6}):Final-Report'
    match = re.match(final_pattern, key)
    
    if match:
        return {
            'type': 'final_report',
            'request_id': match.group(1)
        }
    
    # Try other patterns (routing, status, etc.)
    other_pattern = r'Request-(\d{8}-\d{6}):Task-(\d{8}):Round-(\d+):(\w+)'
    match = re.match(other_pattern, key)
    
    if match:
        return {
            'type': 'other',
            'request_id': match.group(1),
            'task_id': match.group(2),
            'round': int(match.group(3)),
            'suffix': match.group(4)
        }
    
    return None


def format_datetime(request_id: str) -> str:
    """Format request ID (YYYYMMDD-HHMMSS) to readable datetime."""
    try:
        dt = datetime.strptime(request_id, "%Y%m%d-%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return request_id


def extract_initial_request(redis_client: redis.Redis, request_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    """
    Extract the initial user request from Round 0.
    
    Looks for Manager -> Worker messages in Round 0 and extracts:
    - Task description
    - Context/Goal
    - Target workers
    """
    # Look for any Round 0 message from Manager to a worker
    pattern = f"Request-{request_id}:Task-{task_id}:Round-0:From:DT-Manager:To:*"
    keys = redis_client.keys(pattern)
    
    if not keys:
        return None
    
    # Get the first Manager message (usually to Architect)
    for key in sorted(keys):
        data = redis_client.get(key)
        if data:
            try:
                msg = json.loads(data)
                return {
                    'task': msg.get('Task', 'N/A'),
                    'goal': msg.get('Goal', 'N/A'),
                    'target_worker': msg.get('Target_Worker', 'N/A'),
                    'context': msg.get('Context', {}),
                    'full_message': msg
                }
            except json.JSONDecodeError:
                continue
    
    return None


def extract_final_report(redis_client: redis.Redis, request_id: str) -> Optional[Dict[str, Any]]:
    """Extract final report if available."""
    key = f"Request-{request_id}:Final-Report"
    data = redis_client.get(key)
    
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {'raw': data}
    
    return None


def collect_request_data(redis_client: redis.Redis) -> Dict[str, Dict[str, Any]]:
    """
    Collect all request data from Redis.
    
    Returns dict keyed by request_id with:
    - rounds: set of round numbers
    - task_id: task identifier
    - messages: list of all message keys
    - workers: set of workers involved
    - has_final_report: bool
    """
    # Get all Request-* keys
    all_keys = redis_client.keys("Request-*")
    
    requests = defaultdict(lambda: {
        'rounds': set(),
        'task_id': None,
        'messages': [],
        'workers': set(),
        'has_final_report': False,
        'other_keys': []
    })
    
    for key in all_keys:
        parsed = parse_request_key(key)
        
        if not parsed:
            continue
        
        req_id = parsed.get('request_id')
        if not req_id:
            continue
        
        if parsed['type'] == 'message':
            requests[req_id]['rounds'].add(parsed['round'])
            requests[req_id]['task_id'] = parsed['task_id']
            requests[req_id]['messages'].append(key)
            requests[req_id]['workers'].add(parsed['from_role'])
            requests[req_id]['workers'].add(parsed['to_role'])
            
        elif parsed['type'] == 'final_report':
            requests[req_id]['has_final_report'] = True
            requests[req_id]['other_keys'].append(key)
            
        elif parsed['type'] == 'other':
            requests[req_id]['rounds'].add(parsed['round'])
            requests[req_id]['task_id'] = parsed['task_id']
            requests[req_id]['other_keys'].append(key)
    
    return dict(requests)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text


def wrap_text(text: str, width: int = 80) -> List[str]:
    """Wrap text to specified width."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def print_header():
    """Print report header."""
    print("=" * 100)
    print(" " * 30 + "DYTOPO REQUESTS REPORT")
    print("=" * 100)
    print()


def print_request_summary(request_id: str, data: Dict[str, Any], 
                         initial_request: Optional[Dict], 
                         final_report: Optional[Dict]):
    """Print summary for a single request."""
    
    # Format datetime
    dt_str = format_datetime(request_id)
    task_id = data.get('task_id', 'N/A')
    
    # Round info
    rounds = sorted(data['rounds'])
    num_rounds = len(rounds)
    rounds_str = ', '.join(map(str, rounds))
    
    # Status
    if final_report:
        status = final_report.get('Final_Status', 'UNKNOWN')
        status_icon = "✅" if 'SUCCESS' in status else "❌" if 'FAIL' in status else "⚠️"
    else:
        status = "INCOMPLETE"
        status_icon = "⏳"
    
    # Print header block
    print("─" * 100)
    print(f"📅  Date/Time:     {dt_str}")
    print(f"📋  Task ID:       {task_id}")
    print(f"🔄  Rounds:        {num_rounds} ({rounds_str})")
    print(f"👥  Workers:       {', '.join(sorted(data['workers']))}")
    print(f"📊  Status:        {status_icon} {status}")
    
    # Initial request details
    if initial_request:
        task = initial_request.get('task', 'N/A')
        goal = initial_request.get('goal', 'N/A')
        
        print()
        print(f"📝  Initial Task:")
        for line in wrap_text(task, 90):
            print(f"    {line}")
        
        print()
        print(f"🎯  Goal:")
        for line in wrap_text(goal, 90):
            print(f"    {line}")
        
        # Context summary
        context = initial_request.get('context', {})
        if context:
            print()
            print(f"📄  Context Summary:")
            
            if 'Problem_Summary' in context:
                print(f"      Problem: {truncate_text(context['Problem_Summary'], 80)}")
            
            if 'Symptoms' in context and isinstance(context['Symptoms'], list):
                print(f"      Symptoms ({len(context['Symptoms'])}):")
                for symptom in context['Symptoms'][:3]:
                    print(f"        • {truncate_text(symptom, 75)}")
    
    # Final report summary
    if final_report:
        print()
        print(f"🏁  Final Summary:")
        summary = final_report.get('Summary', 'N/A')
        for line in wrap_text(summary, 90):
            print(f"    {line}")
        
        # Root cause if available
        root_cause = final_report.get('Root_Cause', '')
        if root_cause:
            print()
            print(f"🔍  Root Cause:")
            for line in wrap_text(root_cause, 90):
                print(f"    {line}")
    
    print()


def generate_requests_report(redis_host='localhost', redis_port=6379, 
                             show_details=True, sort_by='date_desc'):
    """
    Generate a complete report of all DyTopo requests.
    
    Args:
        redis_host: Redis server hostname
        redis_port: Redis server port
        show_details: Whether to show detailed initial request info
        sort_by: Sort order ('date_desc', 'date_asc', 'rounds')
    """
    
    # Connect to Redis
    client = get_redis_client(redis_host, redis_port)
    if not client:
        return
    
    print_header()
    print(f"Connected to Redis at {redis_host}:{redis_port}")
    print()
    
    # Collect all request data
    requests = collect_request_data(client)
    
    if not requests:
        print("No DyTopo requests found in Redis.")
        return
    
    # Sort requests
    if sort_by == 'date_desc':
        sorted_requests = sorted(requests.items(), key=lambda x: x[0], reverse=True)
    elif sort_by == 'date_asc':
        sorted_requests = sorted(requests.items(), key=lambda x: x[0])
    elif sort_by == 'rounds':
        sorted_requests = sorted(requests.items(), 
                               key=lambda x: len(x[1]['rounds']), 
                               reverse=True)
    else:
        sorted_requests = sorted(requests.items(), key=lambda x: x[0], reverse=True)
    
    # Statistics
    total_requests = len(requests)
    total_completed = sum(1 for _, d in requests.items() if d['has_final_report'])
    
    print(f"📈  Statistics:")
    print(f"    Total Requests: {total_requests}")
    print(f"    Completed: {total_completed}")
    print(f"    In Progress: {total_requests - total_completed}")
    print()
    
    # Print each request
    for request_id, data in sorted_requests:
        task_id = data.get('task_id', '')
        
        # Get initial request details
        initial_request = None
        if task_id and show_details:
            initial_request = extract_initial_request(client, request_id, task_id)
        
        # Get final report
        final_report = None
        if data['has_final_report']:
            final_report = extract_final_report(client, request_id)
        
        print_request_summary(request_id, data, initial_request, final_report)
    
    print("─" * 100)
    print()
    print("Report complete.")


def generate_compact_report(redis_host='localhost', redis_port=6379):
    """
    Generate a compact table-style report.
    
    Shows:
    - Date/Time | Task Date | # Rounds | Round Numbers | Status | Task (truncated)
    """
    
    client = get_redis_client(redis_host, redis_port)
    if not client:
        return
    
    print("=" * 120)
    print(f"{'Date/Time':<22} {'Task Date':<12} {'Rounds':<8} {'Round Numbers':<25} {'Status':<12} {'Task'}")
    print("=" * 120)
    
    requests = collect_request_data(client)
    
    if not requests:
        print("No DyTopo requests found.")
        return
    
    # Sort by date descending
    sorted_requests = sorted(requests.items(), key=lambda x: x[0], reverse=True)
    
    for request_id, data in sorted_requests:
        dt_str = format_datetime(request_id)
        task_id = data.get('task_id', 'N/A')
        
        # Format task date
        if task_id and len(task_id) == 8:
            task_date = f"{task_id[:4]}-{task_id[4:6]}-{task_id[6:8]}"
        else:
            task_date = task_id
        
        # Rounds info
        rounds = sorted(data['rounds'])
        num_rounds = len(rounds)
        rounds_str = ', '.join(map(str, rounds))
        if len(rounds_str) > 23:
            rounds_str = rounds_str[:20] + "..."
        
        # Status
        if data['has_final_report']:
            final_report = extract_final_report(client, request_id)
            if final_report:
                status = final_report.get('Final_Status', 'UNKNOWN')
                if 'SUCCESS' in status:
                    status_str = "✅ SUCCESS"
                elif 'FAIL' in status:
                    status_str = "❌ FAILED"
                else:
                    status_str = status[:11]
            else:
                status_str = "✅ DONE"
        else:
            status_str = "⏳ ACTIVE"
        
        # Task (get from Round 0 if possible)
        task_str = "N/A"
        if task_id:
            initial = extract_initial_request(client, request_id, task_id)
            if initial:
                task_str = truncate_text(initial.get('task', 'N/A'), 45)
        
        print(f"{dt_str:<22} {task_date:<12} {num_rounds:<8} {rounds_str:<25} {status_str:<12} {task_str}")
    
    print("=" * 120)
    print(f"\nTotal Requests: {len(requests)}")


def export_to_json(redis_host='localhost', redis_port=6379, 
                   output_file='dytopo_requests_export.json'):
    """Export all request data to JSON file."""
    
    client = get_redis_client(redis_host, redis_port)
    if not client:
        return
    
    requests = collect_request_data(client)
    
    export_data = []
    
    for request_id, data in sorted(requests.items(), key=lambda x: x[0], reverse=True):
        task_id = data.get('task_id', '')
        
        record = {
            'request_id': request_id,
            'request_datetime': format_datetime(request_id),
            'task_id': task_id,
            'task_date': task_id if task_id else 'N/A',
            'num_rounds': len(data['rounds']),
            'rounds': sorted(data['rounds']),
            'workers': sorted(data['workers']),
            'has_final_report': data['has_final_report']
        }
        
        # Add initial request details
        if task_id:
            initial = extract_initial_request(client, request_id, task_id)
            if initial:
                record['initial_task'] = initial.get('task', 'N/A')
                record['initial_goal'] = initial.get('goal', 'N/A')
        
        # Add final report if available
        if data['has_final_report']:
            final = extract_final_report(client, request_id)
            if final:
                record['final_status'] = final.get('Final_Status', 'UNKNOWN')
                record['final_summary'] = final.get('Summary', 'N/A')
        
        export_data.append(record)
    
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Exported {len(export_data)} requests to {output_file}")


def main():
    """Main entry point with CLI arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='DyTopo Requests Report Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Full detailed report
  %(prog)s --compact                # Compact table view
  %(prog)s --export results.json    # Export to JSON
  %(prog)s --sort rounds            # Sort by number of rounds
  %(prog)s --host 192.168.1.100     # Connect to remote Redis
        """
    )
    
    parser.add_argument('--host', default='localhost',
                        help='Redis host (default: localhost)')
    parser.add_argument('--port', type=int, default=6379,
                        help='Redis port (default: 6379)')
    parser.add_argument('--compact', action='store_true',
                        help='Show compact table view')
    parser.add_argument('--export', metavar='FILE',
                        help='Export to JSON file')
    parser.add_argument('--sort', choices=['date_desc', 'date_asc', 'rounds'],
                        default='date_desc',
                        help='Sort order (default: date_desc)')
    
    args = parser.parse_args()
    
    if args.export:
        export_to_json(args.host, args.port, args.export)
    elif args.compact:
        generate_compact_report(args.host, args.port)
    else:
        generate_requests_report(args.host, args.port, 
                                show_details=True, 
                                sort_by=args.sort)


if __name__ == '__main__':
    main()
