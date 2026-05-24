#!/bin/bash
echo "Pulling llama3.2 model..."
curl -X POST http://ollama:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "llama3.2"}'
echo "Model pulled successfully" 