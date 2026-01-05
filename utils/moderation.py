"""
Content Moderation System
"""

import logging
from typing import Optional, Dict
from database.db import Database

logger = logging.getLogger(__name__)


class ModerationSystem:
    """Content moderation and safety checks"""
    
    def __init__(self, db: Database):
        self.db = db
        self.blocked_keywords = [
            # Add blocked keywords here
            # "illegal_content",
        ]
    
    def check_prompt(self, prompt: str) -> tuple[bool, Optional[str]]:
        """Check if prompt is safe"""
        prompt_lower = prompt.lower()
        
        # Check blocked keywords
        for keyword in self.blocked_keywords:
            if keyword in prompt_lower:
                return False, f"Prompt contains blocked content: {keyword}"
        
        # Check prompt length
        if len(prompt) > 2000:
            return False, "Prompt too long (max 2000 characters)"
        
        return True, None
    
    def log_moderation_action(self, user_id: int, action: str, reason: str, moderator_id: Optional[int] = None):
        """Log moderation action"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO moderation_logs (user_id, action, reason, moderator_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, action, reason, moderator_id))
        self.db.conn.commit()

