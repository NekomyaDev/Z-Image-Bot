# Model Setup Guide

This guide explains where to place model files for Z-Image Turbo NSFW ComfyUI API.

## 📁 Directory Structure

```
zimage-comfyui-api/
└── models/
    ├── checkpoints/     # Main model files
    ├── vae/             # VAE models
    ├── clip/            # Text encoders (Qwen3)
    └── loras/           # LoRA files (optional)
```

## 📥 Model Downloads

### 1. Z-Image Turbo NSFW Model

**File:** `zImageTurboNSFW_20BF16AIO.safetensors`

**Location:** `models/checkpoints/`

**Download Link:** [Will be provided by user]

**Size:** ~20GB (BF16 format)

**Notes:**
- This is the main diffusion model
- BF16 format for better quality
- Optimized for NSFW content

### 2. Qwen3-4B Text Encoder

**File:** `Qwen3-4B-Q5_K_M.gguf`

**Location:** `models/clip/`

**Download Link:** [Will be provided by user]

**Size:** ~3-4GB (quantized)

**Notes:**
- Q5_K_M quantization for balance between quality and size
- Required for Z-Image Turbo text encoding
- Different from standard CLIP encoders

### 3. VAE Model

**File:** `ae.safetensors`

**Location:** `models/vae/`

**Download Link:** [Will be provided by user]

**Size:** ~300-500MB

**Notes:**
- VAE (Variational Autoencoder) for image encoding/decoding
- Required for latent space operations

## ✅ Verification

After placing models, verify they're in the correct locations:

```bash
# Check checkpoint
ls -lh models/checkpoints/zImageTurboNSFW_20BF16AIO.safetensors

# Check VAE
ls -lh models/vae/ae.safetensors

# Check CLIP
ls -lh models/clip/Qwen3-4B-Q5_K_M.gguf
```

## 🔧 ComfyUI Integration

### For Standard ComfyUI

If using standard ComfyUI installation, models should be placed in ComfyUI's model directories:

```bash
# ComfyUI model paths
ComfyUI/models/checkpoints/zImageTurboNSFW_20BF16AIO.safetensors
ComfyUI/models/vae/ae.safetensors
ComfyUI/models/clip/Qwen3-4B-Q5_K_M.gguf
```

### Custom Node Requirements

Z-Image Turbo may require custom ComfyUI nodes:
- Qwen3 encoder node (for text encoding)
- FlowMatch sampler node (for Z-Image's flow matching)

Check ComfyUI custom nodes directory for:
- `ComfyUI-Qwen3-Encoder` (or similar)
- `ComfyUI-FlowMatch` (or similar)

## ⚠️ Important Notes

1. **File Names:** Model file names must match exactly as specified in `config/config.yaml`
2. **Permissions:** Ensure files are readable (chmod 644)
3. **Disk Space:** Ensure sufficient disk space (~25GB total)
4. **VRAM:** Models require 16GB+ VRAM (RTX 4060 recommended)

## 🐛 Troubleshooting

### "Model not found" error

- Verify file names match config exactly
- Check file permissions
- Ensure files are in correct directories

### "Text encoder not found" error

- Verify Qwen3 encoder is in `models/clip/`
- Check if custom ComfyUI node is installed
- Verify ComfyUI can load Qwen3 encoder

### "VAE not found" error

- Verify VAE file is in `models/vae/`
- Check file name matches config
- Ensure VAE is compatible with Z-Image Turbo

## 📚 Additional Resources

- [ComfyUI Model Management](https://github.com/comfyanonymous/ComfyUI/wiki/Model-Management)
- [Z-Image Turbo Documentation](https://github.com/Tongyi-MAI/Z-Image-Turbo)

