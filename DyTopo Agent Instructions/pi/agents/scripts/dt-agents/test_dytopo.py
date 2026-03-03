#!/usr/bin/env python3
"""
DyTopo Test Suite

Comprehensive pytest tests for all DyTopo semantic matching components.

Run with:
    pytest test_dytopo.py -v
    pytest test_dytopo.py -v --tb=short
    pytest test_dytopo.py::TestSemanticMatcher -v

Requirements:
    pip install pytest requests redis
"""

import json
import os
import sys
import time
import tempfile
import subprocess
from unittest.mock import patch, MagicMock

import pytest
import requests
import redis

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semantic_matcher import get_embedding, cosine_similarity, calculate_semantic_matches, route_messages
from dytopo_redis import get_redis_client, parse_request_key, build_request_key, read_agent_response


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing."""
    return [
        {
            "role": "Architect",
            "query_descriptor": "Implementation details for Python async patterns",
            "key_descriptor": "System design and architecture patterns expertise",
            "public_message": "Initial design proposal",
            "private_message": "Use Strategy pattern"
        },
        {
            "role": "Developer",
            "query_descriptor": "How to structure the factory class with async support",
            "key_descriptor": "Python implementation and coding expertise",
            "public_message": "Implementation plan",
            "private_message": "Will use asyncio"
        },
        {
            "role": "Tester",
            "query_descriptor": "How to mock async dependencies for unit tests",
            "key_descriptor": "Testing strategies and test framework expertise",
            "public_message": "Test plan ready",
            "private_message": "Using pytest-asyncio"
        },
        {
            "role": "Reviewer",
            "query_descriptor": "Code review for async implementation quality",
            "key_descriptor": "Code review and quality assurance expertise",
            "public_message": "Review checklist",
            "private_message": "Focus on error handling"
        }
    ]


@pytest.fixture
def redis_client():
    """Redis client fixture with cleanup."""
    try:
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2
        )
        if not client.ping():
            pytest.skip("Redis not available")
        
        # Clean up test keys before and after
        test_keys = client.keys("Request-TEST*")
        if test_keys:
            client.delete(*test_keys)
        
        yield client
        
        # Cleanup after test
        test_keys = client.keys("Request-TEST*")
        if test_keys:
            client.delete(*test_keys)
    except redis.ConnectionError:
        pytest.skip("Redis connection failed")


# =============================================================================
# Test Suite: Prerequisites
# =============================================================================

class TestPrerequisites:
    """Test that all prerequisites are met."""
    
    def test_python_packages_installed(self):
        """Test that required Python packages are available."""
        required = ['redis', 'requests']
        for package in required:
            try:
                __import__(package)
            except ImportError:
                pytest.fail(f"Required package '{package}' not installed")
    
    def test_redis_connection(self):
        """Test Redis is running and accessible."""
        try:
            client = redis.Redis(socket_connect_timeout=2)
            assert client.ping(), "Redis ping failed"
        except redis.ConnectionError:
            pytest.skip("Redis not running")
    
    def test_ollama_running(self):
        """Test Ollama service is available."""
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=2
            )
            assert response.status_code == 200, "Ollama API error"
        except requests.RequestException:
            pytest.skip("Ollama not running")
    
    def test_ollama_has_embedding_model(self):
        """Test that nomic-embed-text model is available."""
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=2
            )
            data = response.json()
            model_names = [m.get('name', '') for m in data.get('models', [])]
            
            has_model = any('nomic-embed-text' in name for name in model_names)
            assert has_model, f"nomic-embed-text not found. Available: {model_names}"
        except requests.RequestException:
            pytest.skip("Ollama not running")


# =============================================================================
# Test Suite: Semantic Matcher
# =============================================================================

class TestSemanticMatcher:
    """Test semantic matching functionality."""
    
    def test_get_embedding(self):
        """Test that embeddings are generated correctly."""
        text = "Test embedding generation"
        embedding = get_embedding(text)
        
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"
        assert all(isinstance(x, (int, float)) for x in embedding), "All values should be numeric"
    
    def test_get_embedding_consistency(self):
        """Test that same text produces same embedding."""
        text = "Consistent embedding test"
        emb1 = get_embedding(text)
        emb2 = get_embedding(text)
        
        assert len(emb1) == len(emb2), "Embeddings should have same length"
        # Allow small floating point differences
        differences = [abs(a - b) for a, b in zip(emb1, emb2)]
        assert all(d < 1e-6 for d in differences), "Same text should produce same embedding"
    
    def test_cosine_similarity_identical(self):
        """Test that identical vectors have similarity 1.0."""
        vec = [1.0, 2.0, 3.0, 4.0]
        score = cosine_similarity(vec, vec)
        assert abs(score - 1.0) < 1e-10, f"Identical vectors should have similarity 1.0, got {score}"
    
    def test_cosine_similarity_orthogonal(self):
        """Test that orthogonal vectors have similarity 0.0."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        score = cosine_similarity(vec_a, vec_b)
        assert abs(score) < 1e-10, f"Orthogonal vectors should have similarity 0.0, got {score}"
    
    def test_cosine_similarity_opposite(self):
        """Test that opposite vectors have similarity -1.0."""
        vec_a = [1.0, 2.0, 3.0]
        vec_b = [-1.0, -2.0, -3.0]
        score = cosine_similarity(vec_a, vec_b)
        assert abs(score - (-1.0)) < 1e-10, f"Opposite vectors should have similarity -1.0, got {score}"
    
    def test_cosine_similarity_dimensions(self):
        """Test that mismatched dimensions raise error."""
        vec_a = [1.0, 2.0]
        vec_b = [1.0, 2.0, 3.0]
        
        with pytest.raises(ValueError, match="dimension mismatch"):
            cosine_similarity(vec_a, vec_b)
    
    def test_semantic_similarity_related_texts(self):
        """Test that related texts have higher similarity."""
        text1 = "Python programming language"
        text2 = "Python coding and development"
        text3 = "Machine learning with TensorFlow"
        
        emb1 = get_embedding(text1)
        emb2 = get_embedding(text2)
        emb3 = get_embedding(text3)
        
        score_related = cosine_similarity(emb1, emb2)
        score_unrelated = cosine_similarity(emb1, emb3)
        
        assert score_related > score_unrelated, \
            f"Related texts should have higher similarity: {score_related} vs {score_unrelated}"
        assert score_related > 0.5, f"Related texts should have score > 0.5, got {score_related}"
    
    def test_calculate_semantic_matches(self, sample_agent_data):
        """Test full semantic matching pipeline."""
        edges, metadata = calculate_semantic_matches(
            sample_agent_data,
            threshold=0.5
        )
        
        # Check structure
        assert isinstance(edges, list), "Edges should be a list"
        assert isinstance(metadata, dict), "Metadata should be a dict"
        
        # Check metadata
        assert metadata['agent_count'] == 4
        assert metadata['threshold'] == 0.5
        assert 'total_pairs_evaluated' in metadata
        assert 'embeddings' in metadata
        assert metadata['embeddings']['dimension'] == 768
        
        # Check edges format (edges are tuples: (from, to, score))
        for edge in edges:
            assert len(edge) == 3
            from_role, to_role, score = edge
            assert isinstance(from_role, str)
            assert isinstance(to_role, str)
            assert 0.0 <= score <= 1.0
    
    def test_calculate_semantic_matches_threshold(self, sample_agent_data):
        """Test that threshold filters edges correctly."""
        edges_high, _ = calculate_semantic_matches(
            sample_agent_data,
            threshold=0.7
        )
        edges_low, _ = calculate_semantic_matches(
            sample_agent_data,
            threshold=0.4
        )
        
        # Lower threshold should produce more edges
        assert len(edges_low) >= len(edges_high), \
            f"Lower threshold should produce more edges: {len(edges_low)} vs {len(edges_high)}"
    
    def test_route_messages(self, sample_agent_data):
        """Test message routing."""
        # Create sample edges
        edges = [
            ("Developer", "Architect", 0.7),
            ("Tester", "Developer", 0.6),
            ("Reviewer", "Developer", 0.5)
        ]
        
        agent_messages = {
            "Developer": {"private_message": "Dev insights", "public_message": ""},
            "Tester": {"private_message": "Test insights", "public_message": ""},
            "Reviewer": {"private_message": "Review insights", "public_message": ""}
        }
        
        routing = route_messages(edges, agent_messages, sample_agent_data)
        
        # Check routing structure
        assert "Architect" in routing
        assert "Developer" in routing
        
        # Check that messages are routed correctly
        assert len(routing["Architect"]) > 0, "Architect should receive messages"
        
        # Check that Developer receives from Tester and Reviewer
        dev_messages = [m for m in routing["Developer"] if m['from'] in ["Tester", "Reviewer"]]
        assert len(dev_messages) == 2, f"Developer should receive 2 messages, got {len(dev_messages)}"
        
        # Check that messages are sorted by score
        dev_msgs_sorted = routing["Developer"]
        scores = [m['relevance_score'] for m in dev_msgs_sorted]
        assert scores == sorted(scores, reverse=True), "Messages should be sorted by relevance"


# =============================================================================
# Test Suite: Redis Interface
# =============================================================================

class TestRedisInterface:
    """Test Redis read/write functionality."""
    
    def test_parse_request_key_valid(self):
        """Test parsing valid request keys."""
        key = "Request-20231024-143000:Task-20231024:Round-1:From:DT-Architect:To:DT-Manager"
        result = parse_request_key(key)
        
        assert result is not None
        assert result['request_id'] == "20231024-143000"
        assert result['task_id'] == "20231024"
        assert result['round'] == 1
        assert result['from_role'] == "Architect"
        assert result['to_role'] == "Manager"
    
    def test_parse_request_key_invalid(self):
        """Test parsing invalid request keys."""
        assert parse_request_key("invalid-key") is None
        assert parse_request_key("") is None
        assert parse_request_key("Request-2023:Task-2023") is None
    
    def test_build_request_key(self):
        """Test building request keys."""
        key = build_request_key(
            "20231024-143000",
            "20231024",
            1,
            "Architect",
            "Manager"
        )
        expected = "Request-20231024-143000:Task-20231024:Round-1:From:DT-Architect:To:DT-Manager"
        assert key == expected
    
    def test_read_agent_response(self, redis_client):
        """Test reading agent response from Redis."""
        # Write test data
        key = "Request-TEST-001:Task-TEST:Round-0:From:DT-Architect:To:DT-Manager"
        test_data = {
            "Agent_Role": "DT-Architect",
            "Public_Message": "Public msg",
            "Private_Message": "Private msg",
            "Query_Descriptor": "Need design help",
            "Key_Descriptor": "Design expertise"
        }
        redis_client.set(key, json.dumps(test_data))
        
        # Read back
        response = read_agent_response(
            redis_client,
            "TEST-001",
            "TEST",
            0,
            "Architect"
        )
        
        assert response is not None
        assert response['role'] == "Architect"
        assert response['query_descriptor'] == "Need design help"
        assert response['key_descriptor'] == "Design expertise"
        assert response['public_message'] == "Public msg"
        assert response['private_message'] == "Private msg"
    
    def test_read_agent_response_missing(self, redis_client):
        """Test reading non-existent agent response."""
        response = read_agent_response(
            redis_client,
            "NONEXISTENT",
            "TASK",
            0,
            "NoOne"
        )
        assert response is None


# =============================================================================
# Test Suite: Command Line Interface
# =============================================================================

class TestCLI:
    """Test command-line interface."""
    
    def test_semantic_matcher_cli(self):
        """Test semantic_matcher.py CLI."""
        # Create temp input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([
                {"role": "A", "query_descriptor": "Need help", "key_descriptor": "Can help"},
                {"role": "B", "query_descriptor": "Need help", "key_descriptor": "Can help"}
            ], f)
            input_file = f.name
        
        output_file = input_file.replace('.json', '_out.json')
        
        try:
            result = subprocess.run([
                'python3', 'semantic_matcher.py',
                '--input', input_file,
                '--output', output_file,
                '--threshold', '0.5'
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            assert os.path.exists(output_file), "Output file not created"
            
            with open(output_file) as f:
                data = json.load(f)
                assert 'edges' in data
                assert 'metadata' in data
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_dytopo_setup_cli(self):
        """Test dytopo_setup.py CLI."""
        result = subprocess.run(
            ['python3', 'dytopo_setup.py'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        # Should succeed if prerequisites are met, or exit with specific status
        assert result.returncode in [0, 1], f"Unexpected exit code: {result.returncode}"
        output = result.stdout + result.stderr
        assert "DyTopo Setup Validator" in output
    
    def test_run_dytopo_round_help(self):
        """Test run_dytopo_round.sh help."""
        result = subprocess.run(
            ['./run_dytopo_round.sh', '--help'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        # Bash scripts often return exit code 1 for --help (calls usage() which exits 1)
        assert result.returncode in [0, 1], f"Help failed with unexpected code: {result.returncode}"
        assert "Process a DyTopo round" in result.stdout
        assert "--request-date" in result.stdout


# =============================================================================
# Test Suite: Performance
# =============================================================================

class TestPerformance:
    """Performance benchmarks."""
    
    def test_embedding_performance(self):
        """Test embedding generation performance."""
        text = "Performance test text"
        
        # First call (includes model load)
        start = time.time()
        emb1 = get_embedding(text)
        first_call_time = time.time() - start
        
        # Second call (should be faster - cached)
        start = time.time()
        emb2 = get_embedding(text)
        second_call_time = time.time() - start
        
        # Check that both calls return same result
        assert cosine_similarity(emb1, emb2) > 0.9999
        
        # Warn if first call is very slow (but don't fail - depends on hardware)
        if first_call_time > 5:
            pytest.skip(f"First embedding call too slow ({first_call_time:.2f}s) - may indicate slow GPU")
    
    def test_similarity_calculation_speed(self):
        """Test that similarity calculation is fast."""
        vec = [1.0] * 768  # 768-dimensional vector
        
        start = time.time()
        for _ in range(100):
            cosine_similarity(vec, vec)
        elapsed = time.time() - start
        
        # Should be very fast (much less than 1 second)
        assert elapsed < 1.0, f"Similarity calculation too slow: {elapsed:.3f}s for 100 calls"


# =============================================================================
# Test Suite: Integration
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_round_trip(self, redis_client, sample_agent_data):
        """Test complete round processing."""
        request_date = "TEST-20250301-120000"
        task_date = "TEST-20250301"
        round_num = 0
        
        # Step 1: Write worker responses to Redis
        for i, agent in enumerate(sample_agent_data):
            response = {
                "Agent_Role": f"DT-{agent['role']}",
                "Public_Message": f"{agent['role']} public msg",
                "Private_Message": f"{agent['role']} private msg",
                "Query_Descriptor": agent['query_descriptor'],
                "Key_Descriptor": agent['key_descriptor']
            }
            key = f"Request-{request_date}:Task-{task_date}:Round-{round_num}:From:DT-{agent['role']}:To:DT-Manager"
            redis_client.set(key, json.dumps(response))
        
        # Step 2: Read responses back
        from dytopo_redis import read_all_worker_responses
        workers = [a['role'] for a in sample_agent_data]
        responses = read_all_worker_responses(
            redis_client, request_date, task_date, round_num, workers
        )
        
        assert len(responses) == 4, f"Expected 4 responses, got {len(responses)}"
        
        # Step 3: Perform semantic matching
        edges, metadata = calculate_semantic_matches(responses, threshold=0.5)
        
        # Step 4: Verify results
        assert metadata['agent_count'] == 4
        assert len(edges) > 0, "Should have at least some edges"
        
        # Step 5: Write routing info
        from dytopo_redis import write_routing_info
        
        agent_messages = {
            r['role']: {
                'public_message': r.get('public_message', ''),
                'private_message': r.get('private_message', '')
            }
            for r in responses
        }
        
        # edges is already list of tuples (from, to, score) from calculate_semantic_matches
        routing = route_messages(
            edges,
            agent_messages,
            [{'role': r['role']} for r in responses]
        )
        
        write_routing_info(redis_client, request_date, task_date, round_num, routing, edges)
        
        # Step 6: Verify routing was written
        routing_key = f"Request-{request_date}:Task-{task_date}:Round-{round_num}:Routing"
        routing_data = redis_client.get(routing_key)
        
        assert routing_data is not None, "Routing not written to Redis"
        data = json.loads(routing_data)
        assert 'routing' in data
        assert 'edges' in data
        
        print(f"✓ Full round trip complete: {len(edges)} edges, routing written")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
