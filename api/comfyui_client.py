"""
ComfyUI API Client
Handles communication with ComfyUI server for image generation
"""

import json
import uuid
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import websockets
import logging

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Client for interacting with ComfyUI API"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws?clientId={uuid.uuid4()}"
        
    async def queue_prompt(self, prompt: Dict[str, Any]) -> str:
        """Queue a prompt and return prompt ID"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt",
                json={"prompt": prompt}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("prompt_id")
                else:
                    error = await response.text()
                    raise Exception(f"Failed to queue prompt: {error}")
    
    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download generated image"""
        url = f"{self.base_url}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    raise Exception(f"Failed to get image: {response.status}")
    
    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get generation history for a prompt ID"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/history/{prompt_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get history: {response.status}")
    
    async def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for prompt completion via WebSocket"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                start_time = asyncio.get_event_loop().time()
                
                while True:
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        raise TimeoutError(f"Generation timeout after {timeout}s")
                    
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Check if our prompt is complete
                    if data.get("type") == "execution_cached":
                        if data.get("data", {}).get("prompt_id") == prompt_id:
                            return await self.get_history(prompt_id)
                    
                    if data.get("type") == "executing":
                        if data.get("data", {}).get("node") is None:
                            # Execution finished
                            return await self.get_history(prompt_id)
                    
                    if data.get("type") == "progress":
                        # Log progress
                        progress = data.get("data", {})
                        logger.info(f"Progress: {progress.get('value', 0)}/{progress.get('max', 100)}")
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            # Fallback to polling
            return await self._poll_for_completion(prompt_id, timeout)
    
    async def _poll_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Fallback: Poll for completion"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            history = await self.get_history(prompt_id)
            if prompt_id in history:
                return history
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Generation timeout after {timeout}s")
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 8,
        seed: int = -1,
        workflow_path: Optional[str] = None
    ) -> bytes:
        """Generate image with given parameters"""
        
        # Load workflow
        if workflow_path:
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
        else:
            workflow = self._create_default_workflow()
        
        # Update workflow with parameters
        workflow = self._update_workflow(
            workflow,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            seed=seed
        )
        
        # Queue prompt
        prompt_id = await self.queue_prompt(workflow)
        logger.info(f"Queued prompt: {prompt_id}")
        
        # Wait for completion
        history = await self.wait_for_completion(prompt_id)
        
        # Get output image
        output_data = history.get(prompt_id, {}).get("outputs", {})
        if not output_data:
            raise Exception("No output generated")
        
        # Find image output node
        for node_id, node_output in output_data.items():
            if "images" in node_output:
                image_info = node_output["images"][0]
                filename = image_info["filename"]
                subfolder = image_info.get("subfolder", "")
                
                # Download image
                return await self.get_image(filename, subfolder)
        
        raise Exception("No image found in output")
    
    def _create_default_workflow(self) -> Dict[str, Any]:
        """Create default Z-Image workflow"""
        # This will be loaded from workflow file
        return {}
    
    def _update_workflow(
        self,
        workflow: Dict[str, Any],
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        seed: int
    ) -> Dict[str, Any]:
        """Update workflow with generation parameters"""
        # Find and update prompt nodes
        for node_id, node in workflow.items():
            if isinstance(node, dict):
                # Update CLIP text encode nodes (for Z-Image, might be Qwen3 encoder)
                if node.get("class_type") == "CLIPTextEncode" or node.get("class_type") == "Qwen3TextEncode":
                    inputs = node.get("inputs", {})
                    if "text" in inputs:
                        # Check node ID or title to determine positive/negative
                        node_title = node.get("_meta", {}).get("title", "").lower()
                        if "positive" in node_title or "prompt" in node_title or node_id == "2":
                            inputs["text"] = prompt
                        elif "negative" in node_title or node_id == "3":
                            inputs["text"] = negative_prompt
                
                # Update sampler nodes (Z-Image uses FlowMatch)
                if node.get("class_type") in ["KSampler", "FlowMatchSampler", "SamplerCustomAdvanced"]:
                    inputs = node.get("inputs", {})
                    if "seed" in inputs:
                        inputs["seed"] = seed if seed >= 0 else -1
                    if "steps" in inputs:
                        inputs["steps"] = steps
                    if "cfg" in inputs:
                        inputs["cfg"] = 1.0  # Z-Image default
                
                # Update empty latent image
                if node.get("class_type") == "EmptyLatentImage":
                    inputs = node.get("inputs", {})
                    if "width" in inputs:
                        inputs["width"] = width
                    if "height" in inputs:
                        inputs["height"] = height
        
        return workflow

