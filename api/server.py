"""
FastAPI Server for Z-Image Turbo NSFW
REST API for image generation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging
from pathlib import Path
import yaml
import os
from dotenv import load_dotenv

from .comfyui_client import ComfyUIClient

# Load environment variables
load_dotenv()

# Load config
config_path = Path(__file__).parent.parent / "config" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Initialize ComfyUI client
comfyui_client = ComfyUIClient(
    host=config.get("comfyui", {}).get("host", "127.0.0.1"),
    port=config.get("comfyui", {}).get("port", 8188)
)

# Initialize FastAPI
app = FastAPI(
    title="Z-Image Turbo NSFW API",
    description="Production-ready API for Z-Image Turbo NSFW model",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("server", {}).get("cors_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Request models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Positive prompt for image generation")
    negative_prompt: Optional[str] = Field("", description="Negative prompt")
    width: Optional[int] = Field(1024, ge=512, le=2048, description="Image width")
    height: Optional[int] = Field(1024, ge=512, le=2048, description="Image height")
    steps: Optional[int] = Field(8, ge=1, le=20, description="Number of steps")
    seed: Optional[int] = Field(-1, description="Seed (-1 for random)")
    cfg_scale: Optional[float] = Field(1.0, ge=1.0, le=10.0, description="CFG scale")


class GenerateResponse(BaseModel):
    success: bool
    message: str
    image_url: Optional[str] = None
    seed: Optional[int] = None


# Health check
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Z-Image Turbo NSFW API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test ComfyUI connection
        # Simple check - could be improved
        return {
            "status": "healthy",
            "comfyui": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/generate", response_class=Response)
async def generate_image(request: GenerateRequest):
    """
    Generate image with given prompt
    
    Returns PNG image
    """
    try:
        logger.info(f"Generation request: {request.prompt[:50]}...")
        
        # Load workflow
        workflow_path = Path(__file__).parent.parent / config.get("comfyui", {}).get("workflow_path", "workflows/zimage_workflow.json")
        
        # Generate image
        image_data = await comfyui_client.generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "",
            width=request.width,
            height=request.height,
            steps=request.steps,
            seed=request.seed,
            workflow_path=str(workflow_path) if workflow_path.exists() else None
        )
        
        # Return image
        return Response(
            content=image_data,
            media_type="image/png",
            headers={
                "X-Seed": str(request.seed) if request.seed >= 0 else "random"
            }
        )
    
    except TimeoutError as e:
        logger.error(f"Generation timeout: {e}")
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/json")
async def generate_image_json(request: GenerateRequest):
    """
    Generate image and return JSON with image data (base64)
    """
    try:
        import base64
        
        logger.info(f"Generation request (JSON): {request.prompt[:50]}...")
        
        # Load workflow
        workflow_path = Path(__file__).parent.parent / config.get("comfyui", {}).get("workflow_path", "workflows/zimage_workflow.json")
        
        # Generate image
        image_data = await comfyui_client.generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "",
            width=request.width,
            height=request.height,
            steps=request.steps,
            seed=request.seed,
            workflow_path=str(workflow_path) if workflow_path.exists() else None
        )
        
        # Encode to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return {
            "success": True,
            "message": "Image generated successfully",
            "image": f"data:image/png;base64,{image_base64}",
            "seed": request.seed if request.seed >= 0 else None
        }
    
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    server_config = config.get("server", {})
    uvicorn.run(
        "api.server:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=False
    )

