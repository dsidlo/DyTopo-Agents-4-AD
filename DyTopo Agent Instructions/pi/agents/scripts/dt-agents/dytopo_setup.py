#!/usr/bin/env python3
"""
DyTopo Setup Validator

Validates that all prerequisites are met for dt-manager to function.
Checks:
- Redis is running and accessible
- Ollama is running
- nomic-embed-text model is available
- Required Python packages are installed
- Scripts directory is set up correctly
"""

import sys
import subprocess
import json
import requests
import os

def check_redis() -> tuple:
    """Check if Redis is running."""
    try:
        import redis
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            socket_connect_timeout=3,
            decode_responses=True
        )
        if client.ping():
            info = client.info('server')
            version = info.get('redis_version', 'unknown')
            return (True, f"✓ Redis is running (v{version})")
    except ImportError:
        return (False, "✗ redis-py package not installed (pip install redis)")
    except Exception as e:
        return (False, f"✗ Redis connection failed: {e}")
    
    return (False, "✗ Redis ping failed")


def check_ollama() -> tuple:
    """Check if Ollama is running and has nomic-embed-text."""
    try:
        response = requests.get(
            "http://localhost:11434/api/tags",
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        models = data.get('models', [])
        
        # Check for nomic-embed-text
        model_names = [m.get('name', '') for m in models]
        
        if 'nomic-embed-text:latest' in model_names:
            return (True, "✓ Ollama running with nomic-embed-text:latest")
        elif any('nomic-embed-text' in name for name in model_names):
            # Has nomic but not latest
            actual = [name for name in model_names if 'nomic' in name.lower()]
            return (False, f"⚠ Ollama running but nomic-embed-text:latest not found. Found: {actual}")
        else:
            return (False, f"✗ nomic-embed-text not found. Available: {model_names[:5]}...")
            
    except requests.exceptions.ConnectionError:
        return (False, "✗ Ollama not running (http://localhost:11434)")
    except requests.exceptions.Timeout:
        return (False, "✗ Ollama timed out")
    except Exception as e:
        return (False, f"✗ Ollama check failed: {e}")


def check_python_packages() -> tuple:
    """Check required Python packages."""
    required = ['redis', 'requests', 'numpy']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        return (False, f"✗ Missing packages: {', '.join(missing)}. Run: pip install {' '.join(missing)}")
    
    return (True, f"✓ All required packages installed: {', '.join(required)}")


def check_scripts_directory() -> tuple:
    """Check that scripts directory exists with required files."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    required_scripts = [
        'semantic_matcher.py',
        'dytopo_redis.py',
        'process_round.py',
        'dytopo_setup.py'
    ]
    
    missing = []
    for script in required_scripts:
        path = os.path.join(script_dir, script)
        if not os.path.exists(path):
            missing.append(script)
        else:
            size = os.path.getsize(path)
            if size == 0:
                missing.append(f"{script} (empty file)")
    
    if missing:
        return (False, f"✗ Missing or empty scripts: {', '.join(missing)}")
    
    return (True, f"✓ Scripts directory ready ({script_dir})")


def test_embedding() -> tuple:
    """Quick test of embedding functionality."""
    try:
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "nomic-embed-text:latest",
                "prompt": "test embedding"
            },
            timeout=10
        )
        response.raise_for_status()
        
        embedding = response.json().get('embedding')
        if embedding and len(embedding) > 0:
            return (True, f"✓ Embedding test passed ({len(embedding)} dimensions)")
        else:
            return (False, "✗ Embedding returned empty")
            
    except Exception as e:
        return (False, f"✗ Embedding test failed: {e}")


def run_all_checks() -> bool:
    """Run all prerequisite checks."""
    print("\n" + "="*60)
    print("DyTopo Setup Validator")
    print("="*60 + "\n")
    
    checks = [
        ("Python Packages", check_python_packages),
        ("Redis Server", check_redis),
        ("Ollama Service", check_ollama),
        ("Scripts Directory", check_scripts_directory),
        ("Embedding Test", test_embedding),
    ]
    
    results = []
    for name, check_func in checks:
        ok, message = check_func()
        results.append((name, ok, message))
        status = "✓" if ok else "✗"
        print(f"{status} {name}: {message}")
    
    print("\n" + "="*60)
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("✓ All checks passed! DyTopo is ready.")
        print("="*60 + "\n")
        return True
    else:
        print("✗ Some checks failed. Fix above issues before running DyTopo.")
        print("="*60 + "\n")
        return False


def print_help():
    """Print help for fixing common issues."""
    print("""
DyTopo Setup Help:
==================

1. Install Redis:
   - Ubuntu: sudo apt-get install redis-server && sudo systemctl start redis
   - macOS: brew install redis && brew services start redis
   - Docker: docker run -d -p 6379:6379 redis:latest

2. Install Ollama:
   - Visit: https://ollama.ai
   - Run: curl https://ollama.ai/install.sh | sh
   
3. Download nomic-embed-text model:
   - ollama pull nomic-embed-text:latest
   
4. Install Python packages:
   - pip install redis requests numpy

5. Verify installation:
   - python3 ~/.pi/agent/scripts/dt-agents/dytopo_setup.py

For more details, see:
- https://redis.io/docs/getting-started/
- https://ollama.ai
""")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate DyTopo prerequisites")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--help-setup", action="store_true", help="Show setup instructions")
    
    args = parser.parse_args()
    
    if args.help_setup:
        print_help()
        sys.exit(0)
    
    success = run_all_checks()
    sys.exit(0 if success else 1)
