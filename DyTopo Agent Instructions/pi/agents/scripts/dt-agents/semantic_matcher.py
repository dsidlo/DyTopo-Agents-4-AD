#!/usr/bin/env python3
"""
DyTopo Semantic Matcher

Performs semantic matching between agent Query and Key descriptors
using nomic-embed-text embeddings via local Ollama.

This script implements Step 4 of the DyTopo protocol:
- Generates embeddings for Query_Descriptor_i and Key_Descriptor_j
- Calculates cosine similarity using numpy
- Creates directed edges for matches >= 0.7 threshold
"""

import json
import sys
import math
import argparse
from typing import List, Dict, Tuple, Any
import redis
import requests


def get_embedding(text: str, model: str = "nomic-embed-text:latest", ollama_url: str = "http://localhost:11434") -> List[float]:
    """
    Get text embedding from local Ollama instance.
    
    Args:
        text: The text to embed
        model: Ollama model name (default: nomic-embed-text:latest)
        ollama_url: Ollama API URL
        
    Returns:
        Embedding vector as list of floats
    """
    try:
        response = requests.post(
            f"{ollama_url}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except requests.RequestException as e:
        print(f"Error calling Ollama: {e}", file=sys.stderr)
        raise


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors using NumPy-compatible math.
    
    Args:
        vec_a: First embedding vector
        vec_b: Second embedding vector
        
    Returns:
        Cosine similarity score (-1.0 to 1.0)
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")
    
    # Manual calculation (equivalent to numpy.dot + norms)
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    norm_b = math.sqrt(sum(x * x for x in vec_b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def calculate_semantic_matches(
    agent_data: List[Dict[str, Any]],
    threshold: float = 0.7,
    ollama_model: str = "nomic-embed-text:latest"
) -> Tuple[List[Tuple[str, str, float]], Dict[str, Any]]:
    """
    Perform semantic matching across all agent Query(Key descriptor pairs.
    
    Implements Algorithm 1 from the DyTopo paper:
    For each pair (Worker_i, Worker_j) where i ≠ j:
    1. Embed Query_i and Key_j using nomic-embed-text
    2. Calculate cosine similarity
    3. If score >= threshold, create directed edge Worker_j → Worker_i
    
    Args:
        agent_data: List of agent dictionaries with 'role', 'query_descriptor', 'key_descriptor'
        threshold: Minimum similarity for edge creation (default: 0.7)
        ollama_model: Ollama model to use
        
    Returns:
        Tuple of (edges list, metadata dict)
        edges: List of (source_role, target_role, score) tuples
        metadata: Computation details including embeddings and scores
    """
    
    # Cache embeddings to avoid duplicate API calls
    embeddings = {}
    
    # Generate embeddings for all queries and keys
    for agent in agent_data:
        role = agent['role']
        
        # Embed Query descriptor (what the agent needs)
        query_text = agent.get('query_descriptor', '')
        query_key = f"{role}:query"
        if query_key not in embeddings:
            embeddings[query_key] = get_embedding(query_text, ollama_model)
        
        # Embed Key descriptor (what the agent offers)
        key_text = agent.get('key_descriptor', '')
        key_key = f"{role}:key"
        if key_key not in embeddings:
            embeddings[key_key] = get_embedding(key_text, ollama_model)
    
    # Perform semantic matching
    edges = []
    detailed_scores = {}
    
    for i, agent_i in enumerate(agent_data):
        for j, agent_j in enumerate(agent_data):
            if i == j:
                continue  # Skip self-matches
            
            role_i = agent_i['role']
            role_j = agent_j['role']
            
            # Get embeddings: Query_i vs Key_j
            query_i = embeddings[f"{role_i}:query"]
            key_j = embeddings[f"{role_j}:key"]
            
            # Calculate similarity
            score = cosine_similarity(query_i, key_j)
            
            detailed_scores[f"{role_i}<-{role_j}"] = {
                "query_agent": role_i,
                "key_agent": role_j,
                "score": round(score, 4)
            }
            
            # Create edge if score >= threshold
            if score >= threshold:
                # Directed edge: Worker_j → Worker_i
                # (Worker_j can help Worker_i with their need)
                edges.append((role_j, role_i, round(score, 4)))
    
    # Sort edges by score descending (highest relevance first)
    edges.sort(key=lambda x: x[2], reverse=True)
    
    metadata = {
        "agent_count": len(agent_data),
        "threshold": threshold,
        "total_pairs_evaluated": len(agent_data) * (len(agent_data) - 1),
        "edges_created": len(edges),
        "all_scores": detailed_scores,
        "embeddings": {
            "model": ollama_model,
            "dimension": len(embeddings[list(embeddings.keys())[0]]) if embeddings else 0
        }
    }
    
    return edges, metadata


def route_messages(
    edges: List[Tuple[str, str, float]],
    agent_messages: Dict[str, Any],
    agent_data: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Route private messages along semantic edges.
    
    For each directed edge (j → i), Worker_j's Private_Message goes to Worker_i
    if similarity score >= threshold.
    
    Args:
        edges: List of (source, target, score) tuples
        agent_messages: Dict mapping agent roles to their messages/content
        agent_data: Full agent data for context
        
    Returns:
        Dictionary mapping target agent to list of incoming messages
    """
    routing = {agent['role']: [] for agent in agent_data}
    
    for source_role, target_role, score in edges:
        # Get source agent's private message
        source_message = agent_messages.get(source_role, {}).get('private_message', '')
        source_public = agent_messages.get(source_role, {}).get('public_message', '')
        
        if source_message or source_public:
            routing[target_role].append({
                "from": source_role,
                "relevance_score": score,
                "content": source_message or source_public,
                "message_type": "private" if source_message else "public"
            })
    
    # Sort each agent's incoming messages by relevance
    for target in routing:
        routing[target].sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return routing


def main():
    """CLI entry point for semantic matching."""
    parser = argparse.ArgumentParser(
        description="DyTopo Semantic Matcher - Calculate semantic edges between agents"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="JSON file containing agent data with query/key descriptors"
    )
    parser.add_argument(
        "--output", "-o",
        default="/tmp/dytopo_matches.json",
        help="Output JSON file for match results"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.7,
        help="Similarity threshold for edge creation (default: 0.7)"
    )
    parser.add_argument(
        "--model", "-m",
        default="nomic-embed-text:latest",
        help="Ollama embedding model (default: nomic-embed-text:latest)"
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API URL"
    )
    
    args = parser.parse_args()
    
    # Load agent data
    with open(args.input, 'r') as f:
        agent_data = json.load(f)
    
    print(f"Processing {len(agent_data)} agents...", file=sys.stderr)
    
    # Calculate matches
    edges, metadata = calculate_semantic_matches(
        agent_data,
        threshold=args.threshold,
        ollama_model=args.model
    )
    
    # Prepare output
    result = {
        "edges": [
            {"from": src, "to": tgt, "score": score}
            for src, tgt, score in edges
        ],
        "metadata": metadata
    }
    
    # Write output
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Found {len(edges)} semantic edges (threshold={args.threshold})")
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
