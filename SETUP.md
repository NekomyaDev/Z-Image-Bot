# Setup Guide - Z-Image Turbo NSFW ComfyUI API

## 📋 Prerequisites

- Python 3.10 or higher
- CUDA 12.0+ (for GPU acceleration)
- RTX 4060 or compatible GPU (16GB+ VRAM recommended)
- Discord Bot Token (for Discord integration)

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Download Models

Download and place models in the following directories:

#### 1. Z-Image Turbo NSFW Model
- **File:** `zImageTurboNSFW_20BF16AIO.safetensors`
- **Place in:** `models/checkpoints/`
- **Download link:** [Will be provided]

#### 2. Qwen3-4B Text Encoder
- **File:** `Qwen3-4B-Q5_K_M.gguf`
- **Place in:** `models/clip/`
- **Download link:** [Will be provided]

#### 3. VAE Model
- **File:** `ae.safetensors`
- **Place in:** `models/vae/`
- **Download link:** [Will be provided]

### Step 3: Configure Environment

1. Copy environment template:
```bash
cp .env.example .env
```

2. Edit `.env` file and add your Discord token:
```
DISCORD_TOKEN=your_discord_bot_token_here
```

### Step 4: Start ComfyUI (Required)

Before running the API server, you need to start ComfyUI:

```bash
# Navigate to your ComfyUI installation
cd /home/neko/StabilityMatrix/Packages/ComfyUI

# Start ComfyUI server
python main.py --port 8188
```

Keep this running in a separate terminal.

### Step 5: Run API Server and Discord Bot

```bash
python main.py
```

That's it! The server will:
- Start API server on `http://localhost:8000`
- Connect Discord bot (if token is provided)
- Be ready to generate images!

## 🔧 Manual Setup (Detailed)

### Model Directory Structure

After downloading models, your directory structure should look like:

```
zimage-comfyui-api/
├── models/
│   ├── checkpoints/
│   │   └── zImageTurboNSFW_20BF16AIO.safetensors  ✅
│   ├── vae/
│   │   └── ae.safetensors  ✅
│   └── clip/
│       └── Qwen3-4B-Q5_K_M.gguf  ✅
```

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section
4. Create a bot and copy the token
5. Enable "Message Content Intent" in Bot settings
6. Invite bot to your server with these permissions:
   - Send Messages
   - Attach Files
   - Use Slash Commands

### Configuration

Edit `config/config.yaml` for advanced settings:

```yaml
# Change default generation parameters
generation:
  default_steps: 8
  default_width: 1024
  default_height: 1024

# Change server port
server:
  port: 8000
```

## ✅ Verification

### Check API Server

```bash
curl http://localhost:8000/health
```

Should return:
```json
{"status": "healthy", "comfyui": "connected"}
```

### Test Image Generation

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful landscape",
    "steps": 8,
    "width": 1024,
    "height": 1024
  }' \
  --output test_image.png
```

### Test Discord Bot

In Discord, type:
```
/generate prompt:a beautiful landscape
```

## 🐛 Troubleshooting

### "Model not found" error

- Check that model files are in correct directories
- Verify file names match config.yaml
- Check file permissions

### "ComfyUI connection failed"

- Make sure ComfyUI is running on port 8188
- Check firewall settings
- Verify ComfyUI is accessible at `http://127.0.0.1:8188`

### "Discord bot not starting"

- Check DISCORD_TOKEN in .env file
- Verify token is valid
- Check bot has correct permissions in Discord server

### "Out of memory" error

- Reduce image resolution (width/height)
- Reduce batch size in config
- Enable low_vram_mode in config

## 📚 Additional Resources

- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🆘 Support

For issues, please check:
1. All models are downloaded and in correct locations
2. ComfyUI is running and accessible
3. Discord token is valid
4. Python version is 3.10+

If problems persist, open an issue on GitHub.

