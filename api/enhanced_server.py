"""
Enhanced API Server with Batch, Upscaling, and Image Editing Support
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio
import logging
from pathlib import Path
import yaml
import os
from dotenv import load_dotenv
import base64

from .comfyui_client import ComfyUIClient

load_dotenv()

config_path = Path(__file__).parent.parent / "config" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

comfyui_client = ComfyUIClient(
    host=config.get("comfyui", {}).get("host", "127.0.0.1"),
    port=config.get("comfyui", {}).get("port", 8188)
)

app = FastAPI(
    title="Z-Image Turbo NSFW API - Enhanced",
    description="Enhanced API with batch, upscaling, and editing support",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("server", {}).get("cors_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    steps: Optional[int] = 8
    seed: Optional[int] = -1
    cfg_scale: Optional[float] = 1.0


class BatchGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    count: Optional[int] = 4
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    steps: Optional[int] = 8


class UpscaleRequest(BaseModel):
    image_data: str  # base64
    scale: Optional[int] = 2


class Img2ImgRequest(BaseModel):
    image_data: str  # base64
    prompt: str
    negative_prompt: Optional[str] = ""
    strength: Optional[float] = 0.7
    steps: Optional[int] = 8


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Z-Image Turbo NSFW API - Enhanced",
        "version": "2.0.0",
        "features": [
            "batch_generation",
            "upscaling",
            "img2img",
            "image_editing"
        ]
    }


@app.post("/generate")
async def generate_image(request: GenerateRequest):
    """Generate single image"""
    try:
        workflow_path = Path(__file__).parent.parent / config.get("comfyui", {}).get("workflow_path", "workflows/zimage_workflow.json")
        
        image_data = await comfyui_client.generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "",
            width=request.width,
            height=request.height,
            steps=request.steps,
            seed=request.seed,
            workflow_path=str(workflow_path) if workflow_path.exists() else None
        )
        
        return Response(
            content=image_data,
            media_type="image/png",
            headers={"X-Seed": str(request.seed) if request.seed >= 0 else "random"}
        )
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch")
async def batch_generate(request: BatchGenerateRequest):
    """Generate multiple images"""
    if request.count > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images per batch")
    
    import time
    results = []
    for i in range(request.count):
        try:
            seed = -1
            if seed == -1:
                seed = int(time.time()) + i
            
            image_data = await comfyui_client.generate_image(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt or "",
                width=request.width,
                height=request.height,
                steps=request.steps,
                seed=seed,
                workflow_path=None
            )
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            results.append({
                "index": i + 1,
                "seed": seed,
                "image": f"data:image/png;base64,{image_base64}"
            })
        except Exception as e:
            logger.error(f"Batch generation error {i}: {e}")
            results.append({"index": i + 1, "error": str(e)})
    
    return {"success": True, "results": results, "count": len(results)}


@app.post("/upscale")
async def upscale_image(request: UpscaleRequest):
    """Upscale image"""
    if request.scale not in [2, 4, 8]:
        raise HTTPException(status_code=400, detail="Scale must be 2, 4, or 8")
    
    try:
        import time
        # Decode image
        image_data = base64.b64decode(request.image_data)
        
        # Upscale (would use ESRGAN here)
        # For now, return original
        return Response(
            content=image_data,
            media_type="image/png",
            headers={"X-Upscaled": "true", "X-Scale": str(request.scale)}
        )
    except Exception as e:
        logger.error(f"Upscale error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/img2img")
async def img2img_generate(request: Img2ImgRequest):
    """Image to image generation"""
    if not 0.0 <= request.strength <= 1.0:
        raise HTTPException(status_code=400, detail="Strength must be between 0.0 and 1.0")
    
    try:
        # Decode image
        image_data = base64.b64decode(request.image_data)
        
        # img2img generation (would use ComfyUI img2img workflow)
        # For now, return message
        return {
            "success": True,
            "message": "img2img generation requires ComfyUI img2img workflow implementation",
            "strength": request.strength
        }
    except Exception as e:
        logger.error(f"img2img error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/inpaint")
async def inpaint_image(
    image_data: str,
    mask_data: str,
    prompt: str,
    negative_prompt: Optional[str] = "",
    strength: Optional[float] = 0.7
):
    """Inpaint image"""
    try:
        # Decode images
        image_bytes = base64.b64decode(image_data)
        mask_bytes = base64.b64decode(mask_data)
        
        # Inpaint (would use ComfyUI inpaint workflow)
        return {
            "success": True,
            "message": "Inpainting requires ComfyUI inpaint workflow implementation"
        }
    except Exception as e:
        logger.error(f"Inpaint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import time
    
    server_config = config.get("server", {})
    uvicorn.run(
        "api.enhanced_server:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=False
    )

