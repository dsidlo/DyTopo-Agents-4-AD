#!/usr/bin/env python3
"""
DyTopo Redis Interface

Handles reading agent data from Redis and writing semantic matching results back.
Works with dt-manager to persist DyTopo state.
"""

import json
import sys
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import redis


def get_redis_client(host='localhost', port=6379, db=0) -> redis.Redis:
    """Get Redis client connection."""
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
        print(f"Redis connection failed: {e}", file=sys.stderr)
        sys.exit(1)


def parse_request_key(key: str) -> Dict[str, str]:
    """
    Parse DyTopo Redis key format.
    
    Format: Request-<YYYYmmDD-HHMMSS>:Task-<YYYYmmDD>:Round-<n>:From:DT-<Role>:To:DT-<Role>
    """
    pattern = r'Request-(\d{8}-\d{6}):Task-(\d{8}):Round-(\d+):From:DT-([\w-]+):To:DT-([\w-]+)'
    match = re.match(pattern, key)
    
    if match:
        return {
            'request_id': match.group(1),
            'task_id': match.group(2),
            'round': int(match.group(3)),
            'from_role': match.group(4),
            'to_role': match.group(5)
        }
    return None


def build_request_key(
    request_date: str,
    task_date: str,
    round_num: int,
    from_role: str,
    to_role: str
) -> str:
    """Build DyTopo Redis key from components."""
    return f"Request-{request_date}:Task-{task_date}:Round-{round_num}:From:DT-{from_role}:To:DT-{to_role}"


def read_agent_response(
    redis_client: redis.Redis,
    request_date: str,
    task_date: str,
    round_num: int,
    worker_role: str
) -> Optional[Dict[str, Any]]:
    """
    Read worker agent response from Redis.
    
    Reads the Worker's response written to Redis after completing their task.
    Key format: Request-<date>:Task-<date>:Round-<n>:From:DT-<Worker>:To:DT-Manager
    
    Returns:
        Parsed JSON response or None if not found
    """
    key = build_request_key(request_date, task_date, round_num, worker_role, "Manager")
    
    data = redis_client.get(key)
    if not data:
        return None
    
    try:
        response = json.loads(data)
        return {
            'role': worker_role,
            'agent_role': response.get('Agent_Role', worker_role),
            'public_message': response.get('Public_Message', ''),
            'private_message': response.get('Private_Message', ''),
            'query_descriptor': response.get('Query_Descriptor', ''),
            'key_descriptor': response.get('Key_Descriptor', ''),
            'raw': response
        }
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON for {key}: {e}", file=sys.stderr)
        return None


def read_all_worker_responses(
    redis_client: redis.Redis,
    request_date: str,
    task_date: str,
    round_num: int,
    worker_roles: List[str]
) -> List[Dict[str, Any]]:
    """Read all worker responses for a given round."""
    responses = []
    
    for role in worker_roles:
        response = read_agent_response(redis_client, request_date, task_date, round_num, role)
        if response:
            responses.append(response)
    
    return responses


def write_routing_info(
    redis_client: redis.Redis,
    request_date: str,
    task_date: str,
    round_num: int,
    routing: Dict[str, List[Dict[str, Any]]],
    semantic_edges: List[Dict[str, Any]]
) -> None:
    """
    Write semantic routing information to Redis.
    
    Stores the routing decisions so they're available for the next round.
    Key: Request-<date>:Task-<date>:Round-<n>:Routing
    """
    routing_key = f"Request-{request_date}:Task-{task_date}:Round-{round_num}:Routing"
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'routing': routing,
        'edges': semantic_edges,
        'round': round_num
    }
    
    redis_client.set(routing_key, json.dumps(data, indent=2))
    print(f"Wrote routing to {routing_key}", file=sys.stderr)


def write_round_report(
    redis_client: redis.Redis,
    request_date: str,
    task_date: str,
    round_num: int,
    report: Dict[str, Any]
) -> None:
    """Write round completion report to Redis."""
    key = f"Request-{request_date}:Task-{task_date}:Round-{round_num}:Round-Report"
    
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'round': round_num,
        'report': report
    }
    
    redis_client.set(key, json.dumps(report_data, indent=2))
    print(f"Wrote round report to {key}", file=sys.stderr)


def write_final_report(
    redis_client: redis.Redis,
    request_date: str,
    task_date: str,
    final_report: Dict[str, Any]
) -> None:
    """Write final consolidated report to Redis."""
    key = f"Request-{request_date}:Final-Report"
    
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'task_id': task_date,
        'report': final_report
    }
    
    redis_client.set(key, json.dumps(report_data, indent=2))
    print(f"Wrote final report to {key}", file=sys.stderr)


def check_prerequisites() -> bool:
    """Check if Redis and Ollama are running."""
    import subprocess
    import requests
    
    print("Checking prerequisites...")
    
    # Check Redis
    try:
        client = redis.Redis(socket_connect_timeout=2)
        if client.ping():
            print("✓ Redis is running")
        else:
            print("✗ Redis ping failed")
            return False
    except redis.ConnectionError:
        print("✗ Redis is not running (redis-cli ping)")
        return False
    
    # Check Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json()
            model_names = [m['name'] for m in models.get('models', [])]
            if 'nomic-embed-text:latest' in model_names:
                print("✓ Ollama is running with nomic-embed-text:latest")
            else:
                print("✗ Ollama is running but nomic-embed-text:latest not found")
                print(f"  Available models: {model_names}")
                return False
        else:
            print("✗ Ollama API error")
            return False
    except requests.RequestException:
        print("✗ Ollama is not running (curl http://localhost:11434/api/tags)")
        return False
    
    return True


def main():
    """CLI for Redis operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DyTopo Redis Interface")
    parser.add_argument("command", choices=['check', 'read', 'write'])
    parser.add_argument("--request-date", help="Request date (YYYYMMDD-HHMMSS)")
    parser.add_argument("--task-date", help="Task date (YYYYMMDD)")
    parser.add_argument("--round", type=int, help="Round number")
    parser.add_argument("--role", help="Agent role")
    
    args = parser.parse_args()
    
    if args.command == 'check':
        success = check_prerequisites()
        sys.exit(0 if success else 1)
    
    elif args.command == 'read':
        if not all([args.request_date, args.task_date, args.round, args.role]):
            print("Usage: --read --request-date DATE --task-date DATE --round N --role ROLE")
            sys.exit(1)
        
        client = get_redis_client()
        response = read_agent_response(
            client, args.request_date, args.task_date, args.round, args.role
        )
        
        if response:
            print(json.dumps(response, indent=2))
        else:
            print(f"No response found for {args.role} in round {args.round}")
    
    elif args.command == 'write':
        print("Use write_routing_info(), write_round_report(), or write_final_report()")


if __name__ == "__main__":
    main()
