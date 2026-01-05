"""
Image storage and management utilities
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from PIL import Image
import hashlib
import logging

logger = logging.getLogger(__name__)


class ImageStorage:
    """Manages image storage and thumbnails"""
    
    def __init__(self, base_path: str = "storage/images", thumbnail_size: tuple = (256, 256)):
        """
        Initialize image storage
        
        Args:
            base_path: Base directory for images
            thumbnail_size: Thumbnail dimensions
        """
        self.base_path = Path(base_path)
        self.thumbnail_path = self.base_path / "thumbnails"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.thumbnail_path.mkdir(parents=True, exist_ok=True)
        self.thumbnail_size = thumbnail_size
    
    def save_image(self, image_data: bytes, user_id: int, generation_id: Optional[int] = None) -> tuple[str, str]:
        """
        Save image and create thumbnail
        
        Returns:
            (image_path, thumbnail_path)
        """
        # Create user directory
        user_dir = self.base_path / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        if generation_id:
            filename = f"{generation_id}.png"
        else:
            # Use hash of image data
            hash_obj = hashlib.md5(image_data)
            filename = f"{hash_obj.hexdigest()}.png"
        
        # Save image
        image_path = user_dir / filename
        with open(image_path, 'wb') as f:
            f.write(image_data)
        
        # Create thumbnail
        thumbnail_path = self.thumbnail_path / str(user_id) / filename
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            img = Image.open(image_path)
            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, "PNG")
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            thumbnail_path = None
        
        return str(image_path.relative_to(self.base_path.parent)), str(thumbnail_path.relative_to(self.base_path.parent)) if thumbnail_path else None
    
    def get_image_path(self, user_id: int, filename: str) -> Path:
        """Get full image path"""
        return self.base_path / str(user_id) / filename
    
    def get_thumbnail_path(self, user_id: int, filename: str) -> Optional[Path]:
        """Get thumbnail path"""
        path = self.thumbnail_path / str(user_id) / filename
        return path if path.exists() else None
    
    def delete_image(self, user_id: int, filename: str) -> bool:
        """Delete image and thumbnail"""
        try:
            image_path = self.get_image_path(user_id, filename)
            if image_path.exists():
                image_path.unlink()
            
            thumbnail_path = self.get_thumbnail_path(user_id, filename)
            if thumbnail_path and thumbnail_path.exists():
                thumbnail_path.unlink()
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            return False
    
    def cleanup_old_images(self, days: int = 30):
        """Cleanup images older than specified days"""
        import time
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        deleted = 0
        for user_dir in self.base_path.iterdir():
            if user_dir.is_dir():
                for image_file in user_dir.iterdir():
                    if image_file.is_file() and image_file.stat().st_mtime < cutoff_time:
                        image_file.unlink()
                        deleted += 1
        
        logger.info(f"Cleaned up {deleted} old images")
        return deleted

