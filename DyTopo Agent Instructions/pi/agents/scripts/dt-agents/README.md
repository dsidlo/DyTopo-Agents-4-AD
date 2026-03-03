# DyTopo Scripts for DT-Manager

This directory contains Python scripts for implementing the DyTopo semantic matching protocol, as specified in the dytopo paper (arXiv:2602.06039v1).

## Quick Start

```bash
# 1. Check prerequisites
python3 dytopo_setup.py

# 2. Or use the wrapper
./run_dytopo_round.sh --check

# 3. Process a complete round
./run_dytopo_round.sh \
    --request-date 20250301-143000 \
    --task-date 20250301 \
    --round 0
```

## Scripts Overview

### Core Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `semantic_matcher.py` | Calculates semantic similarity between agent Query/Key descriptors | Module or CLI |
| `dytopo_redis.py` | Handles Redis read/write for DyTopo protocol | Module or CLI |
| `process_round.py` | Processes a complete DyTopo round end-to-end | CLI |
| `dytopo_setup.py` | Validates prerequisites (Redis, Ollama, packages) | CLI |
| `dytopo_requests_report.py` | Generates reports of all DyTopo requests from Redis | CLI |
| `run_dytopo_round.sh` | Bash wrapper with argument validation | CLI |

### Data Flow

```
Round N:
  1. Manager calls teams to invoke workers
  2. Each worker writes response to Redis
     Key: Request-<date>:Task-<date>:Round-N:From:DT-<Worker>:To:DT-Manager
     Value: JSON with Query_Descriptor, Key_Descriptor, messages
  
  3. Manager calls process_round.py
     - Reads all worker responses from Redis
     - Generates embeddings via Ollama
     - Calculates cosine similarity
     - Creates edges where score >= 0.7
     - Calculates message routing
     - Writes routing to Redis
     
  4. Manager uses routing for next round's worker prompts
```

### Redis Key Patterns

**Messages from Manager to Workers:**
```
Request-<YYYYMMDD-HHMMSS>:Task-<YYYYMMDD>:Round-<N>:From:DT-Manager:To:DT-<Worker>
```

**Responses from Workers to Manager:**
```
Request-<YYYYMMDD-HHMMSS>:Task-<YYYYMMDD>:Round-<N>:From:DT-<Worker>:To:DT-Manager
```

**Routing Information:**
```
Request-<YYYYMMDD-HHMMSS>:Task-<YYYYMMDD>:Round-<N>:Routing
```

**Round Reports:**
```
Request-<YYYYMMDD-HHMMSS>:Task-<YYYYMMDD>:Round-<N>:Round-Report
```

**Final Report:**
```
Request-<YYYYMMDD-HHMMSS>:Final-Report
```

## JSON Schema

### Worker Response (from Redis)

```json
{
  "Agent_Role": "DT-Architect",
  "Public_Message": "I've analyzed the requirements...",
  "Private_Message": "Key insight: should use Strategy pattern",
  "Query_Descriptor": "Implementation details for Python factory",
  "Key_Descriptor": "System architecture and design patterns",
  "Round": 0,
  "Timestamp": "2025-03-01T14:30:00Z"
}
```

### Semantic Matching Output

```json
{
  "edges": [
    {"from": "Developer", "to": "Tester", "score": 0.87},
    {"from": "Architect", "to": "Developer", "score": 0.72}
  ],
  "routing": {
    "Developer": [
      {"from": "Architect", "relevance_score": 0.72, "content": "..."}
    ],
    "Tester": [
      {"from": "Developer", "relevance_score": 0.87, "content": "..."}
    ]
  },
  "metadata": {
    "agent_count": 4,
    "threshold": 0.7,
    "edges_created": 2,
    "similarity_scores": {...}
  }
}
```

## Prerequisites

### 1. Redis Server
```bash
# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

### 2. Ollama with nomic-embed-text
```bash
# Install Ollama (https://ollama.ai)
curl https://ollama.ai/install.sh | sh

# Pull the embedding model
ollama pull nomic-embed-text:latest

# Verify
ollama list
```

### 3. Python Packages
```bash
pip install redis requests numpy
```

### 4. Verify Setup
```bash
python3 dytopo_setup.py
```

## Python API Usage

### From dt-manager (Python)

```python
import sys
sys.path.insert(0, os.path.expanduser('~/.pi/agent/scripts/dt-agents'))

from process_round import process_round
from dytopo_redis import get_redis_client, write_round_report

# Process a round
result = process_round(
    request_date="20250301-143000",
    task_date="20250301",
    round_num=0,
    worker_roles=["Architect", "Developer", "Tester", "Reviewer"],
    threshold=0.7
)

# Use the result
edges = result['edges']
routing = result['routing']

# Write report
redis_client = get_redis_client()
write_round_report(redis_client, request_date, task_date, round_num, report_data)
```

### Direct Library Import

```python
from semantic_matcher import get_embedding, cosine_similarity, route_messages

# Get embeddings
text1 = "Need help with Python asyncio"
text2 = "Expert in async/await patterns"

emb1 = get_embedding(text1)
emb2 = get_embedding(text2)

# Calculate similarity
score = cosine_similarity(emb1, emb2)
print(f"Similarity: {score}")  # 0.0 to 1.0
```

## CLI Examples

### Check Prerequisites
```bash
python3 dytopo_setup.py
# or
./run_dytopo_round.sh --check
```

### Process Round
```bash
python3 process_round.py \
    --request-date 20250301-143000 \
    --task-date 20250301 \
    --round 0 \
    --workers "Architect,Developer,Tester,Reviewer" \
    --threshold 0.7
```

### Semantic Matching Only
```bash
# Create input JSON
cat > /tmp/agents.json << 'EOF'
[
  {
    "role": "Architect",
    "query_descriptor": "Implementation details for Python async",
    "key_descriptor": "System design and architecture patterns"
  },
  {
    "role": "Developer",
    "query_descriptor": "How to structure the factory class",
    "key_descriptor": "Python implementation expertise"
  }
]
EOF

# Run semantic matching
python3 semantic_matcher.py \
    --input /tmp/agents.json \
    --output /tmp/matches.json \
    --threshold 0.7
```

### Generate Requests Report
```bash
# Full detailed report with all requests
python3 dytopo_requests_report.py

# Compact table view
python3 dytopo_requests_report.py --compact

# Export to JSON
python3 dytopo_requests_report.py --export /tmp/dytopo_report.json

# Sort by number of rounds
python3 dytopo_requests_report.py --sort rounds

# Connect to remote Redis
python3 dytopo_requests_report.py --host 192.168.1.100 --port 6379
```

**Report Output:**
- Request date/time and task ID
- Number of rounds and round numbers
- Workers involved
- Initial user task and goal
- Final status (SUCCESS, FAILED, IN PROGRESS)
- Root cause and summary (for completed requests)

### Redis Operations
```bash
# Check if Redis is working
python3 dytopo_redis.py check

# Read a worker response
python3 dytopo_redis.py read \
    --request-date 20250301-143000 \
    --task-date 20250301 \
    --round 0 \
    --role Architect
```

## Semantic Matching Algorithm

This implements Step 4 of the DyTopo protocol:

1. **Generate Embeddings**
   - Call Ollama API with `nomic-embed-text:latest`
   - Creates 768-dimensional vector per text
   
2. **Calculate Cosine Similarity**
   - Formula: `dot(a, b) / (norm(a) * norm(b))`
   - Range: -1.0 to 1.0 (typically 0.3-0.9 for semantic matches)
   
3. **Create Edges**
   - If score >= threshold (0.7): create directed edge
   - Edge direction: Key holder → Query requester
   
4. **Route Messages**
   - Source agent's private message → Target agent
   - Sorted by relevance score

## Configuration

### Adjusting Threshold

Lower threshold = more connections, more messages
Higher threshold = fewer connections, higher relevance

```bash
# Exploratory phase (--round 0)
./run_dytopo_round.sh --threshold 0.5 --round 0

# Focused phase (--round > 0)
./run_dytopo_round.sh --threshold 0.75 --round 1
```

### Custom Worker Roles

```bash
./run_dytopo_round.sh \
    --workers "Security,Performance,API,Database" \
    --round 0
```

## Troubleshooting

### Redis Connection Failed
```bash
# Check if running
redis-cli ping
# Should return: PONG

# If not, start it
sudo systemctl start redis
```

### Ollama Not Running
```bash
# Start Ollama
ollama serve

# Or check status
curl http://localhost:11434/api/tags
```

### Embeddings Timeout
```bash
# Try with longer timeout
python3 semantic_matcher.py ... --timeout 30
```

### Model Not Found
```bash
# Download model
ollama pull nomic-embed-text:latest

# Verify
ollama list
```

## Testing

Run the comprehensive pytest test suite:

```bash
# Install test dependencies
pip install pytest

# Run all tests
pytest test_dytopo.py -v

# Run specific test classes
pytest test_dytopo.py::TestPrerequisites -v
pytest test_dytopo.py::TestSemanticMatcher -v
pytest test_dytopo.py::TestRedisInterface -v
pytest test_dytopo.py::TestCLI -v
pytest test_dytopo.py::TestPerformance -v
pytest test_dytopo.py::TestIntegration -v

# Quick test (skip slow embedding tests)
pytest test_dytopo.py -v -k "not embedding" --tb=short

# With coverage
pytest test_dytopo.py --cov=. --cov-report=html
```

### Test Coverage

| Test Suite | Tests | Purpose |
|------------|-------|---------|
| `TestPrerequisites` | 4 | Verify Redis, Ollama, packages, model |
| `TestSemanticMatcher` | 8 | Embedding generation, similarity, matching |
| `TestRedisInterface` | 5 | Key parsing, read/write operations |
| `TestCLI` | 3 | Command-line interfaces |
| `TestPerformance` | 2 | Speed benchmarks |
| `TestIntegration` | 1 | Full round trip |
| **Total** | **25** | Complete coverage |

## Architecture

```
dt-manager (Pi Agent)
    ├── calls: process_round.py (orchestrates)
    │       ├── semantic_matcher.py (embeddings)
    │       └── dytopo_redis.py (persistence)
    ├── receives: routing.json
    ├── uses: routing for next round
    └── writes: reports to Redis
```

## References

- DyTopo Paper: Dynamic Topology Routing for Multi-Agent Reasoning via Semantic Matching (arXiv:2602.06039v1)
- Ollama: https://ollama.ai
- nomic-embed-text: https://ollama.com/library/nomic-embed-text
- Redis: https://redis.io

## License

Same as Pi agent project.
