#!/bin/bash
# Script to start vllm servers for Whisper models

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting vllm servers for Whisper models...${NC}"

# Check if vllm is installed
if ! command -v vllm &> /dev/null; then
    echo -e "${YELLOW}vllm not found. Please install it first:${NC}"
    echo "  pip install vllm"
    exit 1
fi

# Start primary model (Whisper Large V3) on port 8000
echo -e "${GREEN}Starting Whisper Large V3 on port 8000...${NC}"
vllm serve openai/whisper-large-v3 --port 8000 &
PRIMARY_PID=$!

# Wait a bit
sleep 5

# Start secondary model (Whisper Turbo) on port 8001
echo -e "${GREEN}Starting Whisper Turbo on port 8001...${NC}"
vllm serve openai/whisper-large-v3-turbo --port 8001 &
SECONDARY_PID=$!

echo -e "${GREEN}Both servers started!${NC}"
echo "Primary (Large V3): http://localhost:8000 (PID: $PRIMARY_PID)"
echo "Secondary (Turbo): http://localhost:8001 (PID: $SECONDARY_PID)"
echo ""
echo "To stop servers:"
echo "  kill $PRIMARY_PID $SECONDARY_PID"
echo ""
echo "Or use: pkill -f vllm"

# Keep script running
wait
