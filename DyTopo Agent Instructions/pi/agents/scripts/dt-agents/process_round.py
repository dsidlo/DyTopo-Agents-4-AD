#!/usr/bin/env python3
"""
DyTopo Round Processor

Processes a complete DyTopo round including:
1. Reading worker responses from Redis
2. Performing semantic matching
3. Calculating routing
4. Writing results back to Redis
"""

import json
import sys
import os
import argparse
from datetime import datetime
from typing import Dict, List, Any

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semantic_matcher import get_embedding, cosine_similarity, route_messages
from dytopo_redis import get_redis_client, read_all_worker_responses, write_routing_info


def process_round(
    request_date: str,
    task_date: str,
    round_num: int,
    worker_roles: List[str] = ["Architect", "Developer", "Tester", "Reviewer"],
    threshold: float = 0.7,
    ollama_model: str = "nomic-embed-text:latest"
) -> Dict[str, Any]:
    """
    Process a complete DyTopo round.
    
    This implements the full pipeline:
    - Read worker responses from Redis
    - Extract Query/Key descriptors
    - Generate embeddings via Ollama
    - Calculate semantic matches
    - Create routing decisions
    - Write results to Redis
    
    Returns:
        Dictionary with edges, routing, and metadata
    """
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Processing Round {round_num}", file=sys.stderr)
    print(f"Request: {request_date}, Task: {task_date}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    # Get Redis connection
    redis_client = get_redis_client()
    
    # Step 1: Read all worker responses
    print("Step 1: Reading worker responses...", file=sys.stderr)
    agent_data = read_all_worker_responses(
        redis_client, request_date, task_date, round_num, worker_roles
    )
    
    if not agent_data:
        print(f"No worker responses found for round {round_num}", file=sys.stderr)
        return None
    
    print(f"  Found {len(agent_data)} worker responses")
    for agent in agent_data:
        print(f"  ✓ {agent['role']}: Q='{agent['query_descriptor'][:50]}...'")
    
    # Step 2: Calculate semantic matching
    print("\nStep 2: Calculating semantic matches...", file=sys.stderr)
    
    # Cache embeddings
    embeddings = {}
    agent_info = []
    
    for agent in agent_data:
        role = agent['role']
        agent_info.append({
            'role': role,
            'query': agent.get('query_descriptor', ''),
            'key': agent.get('key_descriptor', '')
        })
        
        print(f"  Generating embeddings for {role}...\r", end='', file=sys.stderr)
        
        # Query embedding
        query_key = f"{role}:query"
        if query_key not in embeddings:
            embeddings[query_key] = get_embedding(agent.get('query_descriptor', ''), ollama_model)
        
        # Key embedding
        key_key = f"{role}:key"
        if key_key not in embeddings:
            embeddings[key_key] = get_embedding(agent.get('key_descriptor', ''), ollama_model)
    
    print(f"  Generated {len(embeddings)} embeddings                          ", file=sys.stderr)
    
    # Calculate all pairwise similarities
    edges = []
    score_matrix = {}
    
    print("  Computing similarity matrix...", file=sys.stderr)
    
    for i, agent_i in enumerate(agent_data):
        for j, agent_j in enumerate(agent_data):
            if i == j:
                continue
            
            role_i = agent_i['role']
            role_j = agent_j['role']
            
            # Query_i vs Key_j
            query_i = embeddings[f"{role_i}:query"]
            key_j = embeddings[f"{role_j}:key"]
            
            score = cosine_similarity(query_i, key_j)
            score_matrix[f"{role_i}<-{role_j}"] = score
            
            if score >= threshold:
                edges.append({
                    'from': role_j,
                    'to': role_i,
                    'score': round(score, 4)
                })
    
    # Sort edges by score
    edges.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"  Created {len(edges)} edges (threshold={threshold})", file=sys.stderr)
    for edge in edges:
        print(f"    {edge['from']} -> {edge['to']} ({edge['score']:.3f})", file=sys.stderr)
    
    # Step 3: Calculate routing
    print("\nStep 3: Calculating message routing...", file=sys.stderr)
    
    agent_messages = {
        agent['role']: {
            'public_message': agent.get('public_message', ''),
            'private_message': agent.get('private_message', '')
        }
        for agent in agent_data
    }
    
    routing = route_messages(
        [(e['from'], e['to'], e['score']) for e in edges],
        agent_messages,
        [{'role': a['role']} for a in agent_data]
    )
    
    print("  Routing summary:", file=sys.stderr)
    for role, messages in routing.items():
        count = len(messages)
        sources = [m['from'] for m in messages]
        print(f"    {role}: {count} messages from {sources or 'none'}", file=sys.stderr)
    
    # Step 4: Write results to Redis
    print("\nStep 4: Writing results to Redis...", file=sys.stderr)
    write_routing_info(redis_client, request_date, task_date, round_num, routing, edges)
    
    # Prepare return data
    result = {
        'round': round_num,
        'request_date': request_date,
        'task_date': task_date,
        'edges': edges,
        'routing': routing,
        'metadata': {
            'agent_count': len(agent_data),
            'threshold': threshold,
            'edges_created': len(edges),
            'similarity_scores': {k: round(v, 4) for k, v in score_matrix.items()},
            'processing_time': datetime.now().isoformat()
        }
    }
    
    # Save to file for debugging
    output_file = f"/tmp/round_{round_num}_result.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"  Results saved to {output_file}", file=sys.stderr)
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Round {round_num} processing complete", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Process a DyTopo round")
    parser.add_argument("--request-date", required=True, help="Request date (YYYYMMDD-HHMMSS)")
    parser.add_argument("--task-date", required=True, help="Task date (YYYYMMDD)")
    parser.add_argument("--round", type=int, required=True, help="Round number")
    parser.add_argument("--workers", default="Architect,Developer,Tester,Reviewer",
                        help="Comma-separated worker roles")
    parser.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold")
    parser.add_argument("--model", default="nomic-embed-text:latest", help="Ollama model")
    
    args = parser.parse_args()
    
    worker_roles = [w.strip() for w in args.workers.split(',')]
    
    result = process_round(
        request_date=args.request_date,
        task_date=args.task_date,
        round_num=args.round,
        worker_roles=worker_roles,
        threshold=args.threshold,
        ollama_model=args.model
    )
    
    if result:
        # Output result as JSON for manager to use
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({"error": "Failed to process round"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
