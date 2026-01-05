#!/bin/bash
# Quick start script for Z-Image Turbo NSFW ComfyUI API

echo "🚀 Starting Z-Image Turbo NSFW ComfyUI API..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from template..."
    
    cat > .env << EOF
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=8000

# ComfyUI Configuration
COMFYUI_HOST=127.0.0.1
COMFYUI_PORT=8188

# Model Paths (relative to project root)
MODEL_CHECKPOINT=models/checkpoints/zImageTurboNSFW_20BF16AIO.safetensors
MODEL_VAE=models/vae/ae.safetensors
MODEL_CLIP=models/clip/Qwen3-4B-Q5_K_M.gguf

# Generation Defaults
DEFAULT_STEPS=8
DEFAULT_WIDTH=1024
DEFAULT_HEIGHT=1024
DEFAULT_SEED=-1

# RTX 4060 Optimization
ENABLE_QUANTIZATION=true
BATCH_SIZE=1
LOW_VRAM_MODE=true
EOF
    
    echo "✅ .env file created!"
    echo "⚠️  Please edit .env and add your DISCORD_TOKEN"
    echo ""
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if models exist
echo "Checking models..."
models_ok=true

if [ ! -f "models/checkpoints/zImageTurboNSFW_20BF16AIO.safetensors" ]; then
    echo "❌ Checkpoint model not found!"
    models_ok=false
fi

if [ ! -f "models/vae/ae.safetensors" ]; then
    echo "❌ VAE model not found!"
    models_ok=false
fi

if [ ! -f "models/clip/Qwen3-4B-Q5_K_M.gguf" ]; then
    echo "❌ CLIP model not found!"
    models_ok=false
fi

if [ "$models_ok" = true ]; then
    echo "✅ All models found!"
else
    echo "⚠️  Some models are missing. See MODEL_SETUP.md for download links."
    echo ""
fi

# Check if ComfyUI is running
echo "Checking ComfyUI connection..."
if curl -s http://127.0.0.1:8188 > /dev/null 2>&1; then
    echo "✅ ComfyUI is running!"
else
    echo "⚠️  ComfyUI is not running on port 8188"
    echo "Please start ComfyUI first:"
    echo "  cd /path/to/ComfyUI && python main.py --port 8188"
    echo ""
fi

# Start the application
echo "Starting application..."
python3 main.py

