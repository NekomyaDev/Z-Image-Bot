"""
Queue Manager for Discord Bot
Handles generation queue and rate limiting
"""

import asyncio
import time
from collections import deque
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    """Queue item for generation requests"""
    user_id: int
    prompt: str
    timestamp: float
    priority: int = 0  # Higher = more priority


class QueueManager:
    """Manages generation queue and rate limiting"""
    
    def __init__(self, max_size: int = 10, rate_limit: int = 5, rate_window: int = 60):
        """
        Initialize queue manager
        
        Args:
            max_size: Maximum queue size
            rate_limit: Maximum requests per window
            rate_window: Time window in seconds
        """
        self.queue: deque = deque(maxlen=max_size)
        self.processing: Dict[int, QueueItem] = {}  # user_id -> current processing
        self.max_size = max_size
        self.rate_limit = rate_limit
        self.rate_window = rate_window
        self.user_requests: Dict[int, List[float]] = {}  # user_id -> [timestamps]
        self.lock = asyncio.Lock()
    
    async def add_request(self, user_id: int, prompt: str, priority: int = 0) -> tuple[bool, Optional[str], int]:
        """
        Add request to queue
        
        Returns:
            (success, error_message, position)
        """
        async with self.lock:
            # Check rate limit
            if not await self._check_rate_limit(user_id):
                return False, f"Rate limit exceeded. Max {self.rate_limit} requests per {self.rate_window} seconds.", -1
            
            # Check queue size
            if len(self.queue) >= self.max_size:
                return False, f"Queue is full (max {self.max_size}). Please try again later.", -1
            
            # Check if user already has request in queue
            if any(item.user_id == user_id for item in self.queue):
                return False, "You already have a request in queue. Please wait.", -1
            
            # Check if user is currently processing
            if user_id in self.processing:
                return False, "You have a generation in progress. Please wait.", -1
            
            # Add to queue
            item = QueueItem(
                user_id=user_id,
                prompt=prompt,
                timestamp=time.time(),
                priority=priority
            )
            
            # Insert based on priority
            inserted = False
            for i, existing_item in enumerate(self.queue):
                if priority > existing_item.priority:
                    self.queue.insert(i, item)
                    inserted = True
                    break
            
            if not inserted:
                self.queue.append(item)
            
            position = list(self.queue).index(item) + 1
            
            # Update rate limit tracking
            if user_id not in self.user_requests:
                self.user_requests[user_id] = []
            self.user_requests[user_id].append(time.time())
            
            logger.info(f"Added request to queue: user={user_id}, position={position}, queue_size={len(self.queue)}")
            return True, None, position
    
    async def get_next(self) -> Optional[QueueItem]:
        """Get next item from queue"""
        async with self.lock:
            if not self.queue:
                return None
            
            item = self.queue.popleft()
            self.processing[item.user_id] = item
            logger.info(f"Processing request: user={item.user_id}")
            return item
    
    async def complete_request(self, user_id: int):
        """Mark request as complete"""
        async with self.lock:
            if user_id in self.processing:
                del self.processing[user_id]
                logger.info(f"Completed request: user={user_id}")
    
    async def cancel_request(self, user_id: int) -> bool:
        """Cancel user's request from queue"""
        async with self.lock:
            # Remove from queue
            for item in list(self.queue):
                if item.user_id == user_id:
                    self.queue.remove(item)
                    logger.info(f"Cancelled request from queue: user={user_id}")
                    return True
            
            # Cancel processing (if possible)
            if user_id in self.processing:
                # Note: Actual cancellation depends on API implementation
                logger.info(f"Request in progress, cannot cancel: user={user_id}")
                return False
            
            return False
    
    async def get_position(self, user_id: int) -> Optional[int]:
        """Get user's position in queue"""
        async with self.lock:
            for i, item in enumerate(self.queue):
                if item.user_id == user_id:
                    return i + 1
            return None
    
    async def get_queue_info(self) -> Dict:
        """Get queue information"""
        async with self.lock:
            return {
                "queue_size": len(self.queue),
                "processing": len(self.processing),
                "max_size": self.max_size,
                "waiting_users": [item.user_id for item in self.queue]
            }
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        now = time.time()
        
        if user_id not in self.user_requests:
            return True
        
        # Remove old requests outside window
        self.user_requests[user_id] = [
            ts for ts in self.user_requests[user_id]
            if now - ts < self.rate_window
        ]
        
        # Check limit
        return len(self.user_requests[user_id]) < self.rate_limit
    
    async def get_rate_limit_info(self, user_id: int) -> Dict:
        """Get rate limit information for user"""
        now = time.time()
        
        if user_id not in self.user_requests:
            return {
                "requests": 0,
                "limit": self.rate_limit,
                "window": self.rate_window,
                "reset_in": self.rate_window
            }
        
        # Remove old requests
        self.user_requests[user_id] = [
            ts for ts in self.user_requests[user_id]
            if now - ts < self.rate_window
        ]
        
        oldest_request = min(self.user_requests[user_id]) if self.user_requests[user_id] else now
        reset_in = max(0, self.rate_window - (now - oldest_request))
        
        return {
            "requests": len(self.user_requests[user_id]),
            "limit": self.rate_limit,
            "window": self.rate_window,
            "reset_in": int(reset_in)
        }

