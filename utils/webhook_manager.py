"""
Webhook Manager for Integration Features
"""

import aiohttp
import json
import logging
from typing import List, Dict, Optional
from database.db import Database

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages webhook notifications"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def send_webhook(self, user_id: int, event_type: str, data: Dict):
        """Send webhook notification"""
        webhooks = self.db.get_webhooks(user_id)
        
        for webhook in webhooks:
            events = json.loads(webhook.get('events', '[]'))
            if event_type in events or '*' in events:
                await self._send_request(webhook['url'], {
                    "event": event_type,
                    "data": data,
                    "timestamp": data.get("timestamp")
                })
    
    async def _send_request(self, url: str, payload: Dict):
        """Send HTTP request to webhook URL"""
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            logger.error(f"Invalid webhook URL: {url}")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook sent successfully to {url}")
                    else:
                        logger.warning(f"Webhook failed: {response.status}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")

