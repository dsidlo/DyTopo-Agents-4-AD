#!/bin/bash
# DyTopo Round Processor Wrapper
# 
# Convenience script for dt-manager to process a DyTopo round
# Usage: ./run_dytopo_round.sh --request-date YYYYMMDD-HHMMSS --task-date YYYYMMDD --round N
#
# This script:
# 1. Validates prerequisites (Redis, Ollama)
# 2. Processes the round using process_round.py
# 3. Returns JSON output for the manager

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Process a DyTopo round for semantic matching.

Required Options:
    --request-date DATE    Request timestamp (YYYYMMDD-HHMMSS)
    --task-date DATE       Task date (YYYYMMDD)
    --round N              Round number (0, 1, 2, ...)

Optional Options:
    --workers LIST         Comma-separated worker roles (default: Architect,Developer,Tester,Reviewer)
    --threshold FLOAT      Similarity threshold (default: 0.7)
    --model MODEL          Ollama model (default: nomic-embed-text:latest)
    --check                Run prerequisite checks only
    --help                 Show this help message

Examples:
    $0 --request-date 20250301-143000 --task-date 20250301 --round 0
    $0 --request-date 20250301-143000 --task-date 20250301 --round 1 --threshold 0.6
    $0 --check

EOF
    exit 1
}

# Parse arguments
REQUEST_DATE=""
TASK_DATE=""
ROUND=""
WORKERS="Architect,Developer,Tester,Reviewer"
THRESHOLD="0.7"
MODEL="nomic-embed-text:latest"
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --request-date)
            REQUEST_DATE="$2"
            shift 2
            ;;
        --task-date)
            TASK_DATE="$2"
            shift 2
            ;;
        --round)
            ROUND="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Run checks if requested
if [ "$CHECK_ONLY" = true ]; then
    echo "Running DyTopo prerequisite checks..."
    python3 "$SCRIPT_DIR/dytopo_setup.py"
    exit $?
fi

# Validate required arguments
if [ -z "$REQUEST_DATE" ] || [ -z "$TASK_DATE" ] || [ -z "$ROUND" ]; then
    echo "Error: Missing required arguments"
    usage
fi

# Validate round number
if ! [[ "$ROUND" =~ ^[0-9]+$ ]]; then
    echo "Error: Round must be a non-negative integer"
    exit 1
fi

# Run the round processor
exec python3 "$SCRIPT_DIR/process_round.py" \
    --request-date "$REQUEST_DATE" \
    --task-date "$TASK_DATE" \
    --round "$ROUND" \
    --workers "$WORKERS" \
    --threshold "$THRESHOLD" \
    --model "$MODEL"
