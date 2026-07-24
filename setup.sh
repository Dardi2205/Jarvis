#!/bin/bash

echo "=== JARVIS Setup for Oracle Cloud ==="

# Update system
sudo dnf update -y

# Install Python
sudo dnf install -y python3.11 python3-pip curl git

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Create app directory
sudo mkdir -p /opt/jarvis
sudo chown $USER:$USER /opt/jarvis

# Copy files
cp -r . /opt/jarvis/
cd /opt/jarvis

# Install Python dependencies
pip3 install --break-system-packages -r backend/requirements.txt

# Pull the model
ollama pull llama3.2 &

# Start Ollama
ollama serve &
sleep 10

# Start JARVIS
nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 &

echo "=== JARVIS is running on port 8080 ==="
echo "Test: curl http://localhost:8080/api/health"
