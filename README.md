# Z-Image Turbo NSFW - ComfyUI API Server

Production-ready ComfyUI API server with Discord bot integration for Z-Image Turbo NSFW model.

## 🚀 Features

- ✅ Z-Image Turbo NSFW model support
- ✅ Qwen3-4B text encoder
- ✅ Custom VAE support
- ✅ REST API for image generation
- ✅ Discord bot integration
- ✅ RTX 4060 optimized (8GB VRAM)
- ✅ Production ready
- ✅ Easy setup - just add Discord token and run!

## 📋 Requirements

- Python 3.10+
- CUDA 12.0+ (for RTX 4060)
- 16GB+ VRAM
- Discord Bot Token
- ComfyUI installed and running

## 🛠️ Quick Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd zimage-comfyui-api
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Models

Download and place models in correct directories (see [MODEL_SETUP.md](MODEL_SETUP.md)):

- `models/checkpoints/zImageTurboNSFW_20BF16AIO.safetensors`
- `models/vae/ae.safetensors`
- `models/clip/Qwen3-4B-Q5_K_M.gguf`

### 4. Configure Discord Bot

1. Create `.env` file (or use `start.sh` to auto-create):
```bash
DISCORD_TOKEN=your_discord_bot_token_here
```

2. Get Discord token from [Discord Developer Portal](https://discord.com/developers/applications)

### 5. Start ComfyUI

In a separate terminal, start ComfyUI:
```bash
cd /path/to/ComfyUI
python main.py --port 8188
```

### 6. Run

```bash
# Option 1: Use start script
./start.sh

# Option 2: Direct Python
python main.py
```

That's it! The server will start and Discord bot will be ready.

## 📁 Project Structure

```
zimage-comfyui-api/
├── models/
│   ├── checkpoints/     # Z-Image Turbo NSFW model
│   ├── vae/             # VAE model (ae.safetensors)
│   └── clip/            # Qwen3-4B encoder
├── api/
│   ├── server.py        # FastAPI server
│   └── comfyui_client.py # ComfyUI API client
├── discord_bot/
│   └── bot.py           # Discord bot
├── workflows/
│   └── zimage_workflow.json # ComfyUI workflow
├── config/
│   └── config.yaml      # Configuration
├── .env                 # Environment variables (create this)
├── requirements.txt     # Python dependencies
├── main.py             # Entry point
├── start.sh            # Quick start script
├── README.md           # This file
├── SETUP.md            # Detailed setup guide
└── MODEL_SETUP.md      # Model download guide
```

## 🎮 Usage

### API Endpoint

```bash
POST http://localhost:8000/generate
Content-Type: application/json

{
  "prompt": "your prompt here",
  "negative_prompt": "negative prompt",
  "width": 1024,
  "height": 1024,
  "steps": 8,
  "seed": -1
}
```

### Discord Commands

- `/generate prompt:<your prompt>` - Generate image
- `/generate prompt:<your prompt> negative_prompt:<negative>` - With negative prompt
- `/generate prompt:<your prompt> steps:<number>` - Custom steps
- `/status` - Check bot and API status
- `/help` - Show help message

## ⚙️ Configuration

Edit `config/config.yaml` for advanced settings:

```yaml
model:
  checkpoint: "zImageTurboNSFW_20BF16AIO.safetensors"
  vae: "ae.safetensors"
  clip: "Qwen3-4B-Q5_K_M.gguf"

generation:
  default_steps: 8
  default_width: 1024
  default_height: 1024
  default_seed: -1

server:
  host: "0.0.0.0"
  port: 8000
```

## 🔧 RTX 4060 Optimization

Optimized for 16GB VRAM:
- Model quantization enabled
- Efficient memory management
- Batch size: 1
- Low VRAM mode enabled

## 📚 Documentation

- [SETUP.md](SETUP.md) - Detailed setup instructions
- [MODEL_SETUP.md](MODEL_SETUP.md) - Model download and placement guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

## 🐛 Troubleshooting

### "Model not found" error
- Check models are in correct directories (see MODEL_SETUP.md)
- Verify file names match config.yaml

### "ComfyUI connection failed"
- Ensure ComfyUI is running on port 8188
- Check firewall settings

### "Discord bot not starting"
- Verify DISCORD_TOKEN in .env file
- Check bot has correct permissions

## 📝 License

MIT License - see [LICENSE](LICENSE) file

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check SETUP.md for common problems
- Review MODEL_SETUP.md for model issues

---

**Made with ❤️ for the Z-Image Turbo community**
