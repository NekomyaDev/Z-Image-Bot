"""
Production-ready Database module
Supports: Gallery, Collections, Challenges, Monetization, Analytics, Gamification
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager - Production Ready"""
    
    def __init__(self, db_path: str = "data/bot.db"):
        """Initialize database"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        """Initialize all database tables"""
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                credits INTEGER DEFAULT 100,
                is_premium INTEGER DEFAULT 0,
                subscription_tier TEXT DEFAULT 'free',
                subscription_expires TIMESTAMP,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                settings TEXT DEFAULT '{}',
                api_key TEXT UNIQUE,
                webhook_url TEXT
            )
        """)
        
        # Generations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                prompt TEXT,
                negative_prompt TEXT,
                seed INTEGER,
                steps INTEGER,
                width INTEGER,
                height INTEGER,
                image_path TEXT,
                thumbnail_path TEXT,
                is_public INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                generation_time REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Collections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                description TEXT,
                is_public INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Collection items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER,
                generation_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collection_id) REFERENCES collections(id),
                FOREIGN KEY (generation_id) REFERENCES generations(id)
            )
        """)
        
        # Challenges table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                theme TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Challenge submissions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenge_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id INTEGER,
                user_id INTEGER,
                generation_id INTEGER,
                votes INTEGER DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (challenge_id) REFERENCES challenges(id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (generation_id) REFERENCES generations(id)
            )
        """)
        
        # Subscriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tier TEXT,
                price REAL,
                status TEXT DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Marketplace items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                item_type TEXT,
                name TEXT,
                description TEXT,
                price REAL,
                file_path TEXT,
                downloads INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                reviews_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users(user_id)
            )
        """)
        
        # Marketplace purchases
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER,
                item_id INTEGER,
                price REAL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (buyer_id) REFERENCES users(user_id),
                FOREIGN KEY (item_id) REFERENCES marketplace_items(id)
            )
        """)
        
        # Analytics events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Achievements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_type TEXT,
                achievement_data TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Presets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                prompt TEXT,
                negative_prompt TEXT,
                steps INTEGER DEFAULT 8,
                width INTEGER DEFAULT 1024,
                height INTEGER DEFAULT 1024,
                is_public INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Favorites table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                generation_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (generation_id) REFERENCES generations(id)
            )
        """)
        
        # Statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                total_generations INTEGER DEFAULT 0,
                total_time REAL DEFAULT 0,
                favorite_prompts TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Credit history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Webhooks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT,
                events TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Moderation logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                reason TEXT,
                moderator_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_generations_user ON generations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_generations_public ON generations(is_public)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenges_active ON challenges(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics_events(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type)")
        
        self.conn.commit()
        logger.info("Database tables initialized")
    
    # User methods
    def get_or_create_user(self, user_id: int, username: str = "") -> Dict:
        """Get or create user"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, username, credits) VALUES (?, ?, 100)",
                (user_id, username)
            )
            self.conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            # Create statistics entry
            cursor.execute("INSERT INTO statistics (user_id) VALUES (?)", (user_id,))
            self.conn.commit()
        
        return dict(user)
    
    def update_user_settings(self, user_id: int, settings: Dict):
        """Update user settings"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET settings = ? WHERE user_id = ?",
            (json.dumps(settings), user_id)
        )
        self.conn.commit()
    
    def get_user_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return json.loads(result['settings'] or '{}')
        return {}
    
    def add_xp(self, user_id: int, amount: int):
        """Add XP and check level up"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            new_xp = user['xp'] + amount
            level = user['level']
            
            # Check level up (100 XP per level)
            while new_xp >= level * 100:
                new_xp -= level * 100
                level += 1
            
            cursor.execute(
                "UPDATE users SET xp = ?, level = ? WHERE user_id = ?",
                (new_xp, level, user_id)
            )
            self.conn.commit()
            return level > user['level']  # Return True if leveled up
        return False
    
    # Generation methods
    def save_generation(
        self,
        user_id: int,
        prompt: str,
        negative_prompt: str,
        seed: int,
        steps: int,
        width: int,
        height: int,
        image_path: str,
        thumbnail_path: Optional[str] = None,
        generation_time: Optional[float] = None,
        is_public: bool = False
    ) -> int:
        """Save generation to database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO generations 
            (user_id, prompt, negative_prompt, seed, steps, width, height, image_path, thumbnail_path, generation_time, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, prompt, negative_prompt, seed, steps, width, height, image_path, thumbnail_path, generation_time, 1 if is_public else 0))
        self.conn.commit()
        
        gen_id = cursor.lastrowid
        
        # Update statistics
        cursor.execute("""
            UPDATE statistics 
            SET total_generations = total_generations + 1,
                total_time = total_time + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (generation_time or 0, user_id))
        self.conn.commit()
        
        # Add XP
        self.add_xp(user_id, 10)
        
        # Log analytics
        self.log_analytics(user_id, "generation", {"generation_id": gen_id, "steps": steps})
        
        return gen_id
    
    def get_user_generations(self, user_id: int, limit: int = 20, offset: int = 0, public_only: bool = False) -> List[Dict]:
        """Get user's generations"""
        cursor = self.conn.cursor()
        if public_only:
            cursor.execute("""
                SELECT * FROM generations 
                WHERE is_public = 1 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM generations 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_public_gallery(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Get public gallery"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT g.*, u.username 
            FROM generations g
            JOIN users u ON g.user_id = u.user_id
            WHERE g.is_public = 1
            ORDER BY g.likes DESC, g.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_generation(self, generation_id: int) -> Optional[Dict]:
        """Get generation by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM generations WHERE id = ?", (generation_id,))
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def like_generation(self, generation_id: int, user_id: int) -> bool:
        """Like a generation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE generations SET likes = likes + 1 WHERE id = ?
        """, (generation_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def increment_views(self, generation_id: int):
        """Increment view count"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE generations SET views = views + 1 WHERE id = ?
        """, (generation_id,))
        self.conn.commit()
    
    # Collection methods
    def create_collection(self, user_id: int, name: str, description: str = "", is_public: bool = False) -> int:
        """Create collection"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO collections (user_id, name, description, is_public)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, description, 1 if is_public else 0))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_to_collection(self, collection_id: int, generation_id: int):
        """Add generation to collection"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO collection_items (collection_id, generation_id)
            VALUES (?, ?)
        """, (collection_id, generation_id))
        self.conn.commit()
    
    def get_collections(self, user_id: int) -> List[Dict]:
        """Get user's collections"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, COUNT(ci.id) as item_count
            FROM collections c
            LEFT JOIN collection_items ci ON c.id = ci.collection_id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_collection_items(self, collection_id: int) -> List[Dict]:
        """Get collection items"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT g.* FROM generations g
            JOIN collection_items ci ON g.id = ci.generation_id
            WHERE ci.collection_id = ?
            ORDER BY ci.added_at DESC
        """, (collection_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # Challenge methods
    def create_challenge(self, name: str, description: str, theme: str, start_date: datetime, end_date: datetime) -> int:
        """Create challenge"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO challenges (name, description, theme, start_date, end_date)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, theme, start_date, end_date))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_active_challenges(self) -> List[Dict]:
        """Get active challenges"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM challenges 
            WHERE is_active = 1 AND datetime('now') BETWEEN start_date AND end_date
            ORDER BY end_date ASC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def submit_to_challenge(self, challenge_id: int, user_id: int, generation_id: int) -> int:
        """Submit to challenge"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO challenge_submissions (challenge_id, user_id, generation_id)
            VALUES (?, ?, ?)
        """, (challenge_id, user_id, generation_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def vote_challenge_submission(self, submission_id: int):
        """Vote for challenge submission"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE challenge_submissions SET votes = votes + 1 WHERE id = ?
        """, (submission_id,))
        self.conn.commit()
    
    def get_challenge_leaderboard(self, challenge_id: int, limit: int = 10) -> List[Dict]:
        """Get challenge leaderboard"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT cs.*, u.username, g.prompt, g.image_path
            FROM challenge_submissions cs
            JOIN users u ON cs.user_id = u.user_id
            JOIN generations g ON cs.generation_id = g.id
            WHERE cs.challenge_id = ?
            ORDER BY cs.votes DESC
            LIMIT ?
        """, (challenge_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    # Subscription methods
    def create_subscription(self, user_id: int, tier: str, price: float, expires_at: datetime) -> int:
        """Create subscription"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO subscriptions (user_id, tier, price, expires_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, tier, price, expires_at))
        
        cursor.execute("""
            UPDATE users SET subscription_tier = ?, subscription_expires = ? WHERE user_id = ?
        """, (tier, expires_at, user_id))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """Get user subscription"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status = 'active' AND expires_at > datetime('now')
            ORDER BY expires_at DESC LIMIT 1
        """, (user_id,))
        result = cursor.fetchone()
        return dict(result) if result else None
    
    # Marketplace methods
    def create_marketplace_item(
        self,
        seller_id: int,
        item_type: str,
        name: str,
        description: str,
        price: float,
        file_path: str
    ) -> int:
        """Create marketplace item"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO marketplace_items (seller_id, item_type, name, description, price, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (seller_id, item_type, name, description, price, file_path))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_marketplace_items(self, item_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get marketplace items"""
        cursor = self.conn.cursor()
        if item_type:
            cursor.execute("""
                SELECT * FROM marketplace_items 
                WHERE item_type = ? AND is_active = 1
                ORDER BY rating DESC, downloads DESC
                LIMIT ?
            """, (item_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM marketplace_items 
                WHERE is_active = 1
                ORDER BY rating DESC, downloads DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def purchase_marketplace_item(self, buyer_id: int, item_id: int) -> bool:
        """Purchase marketplace item"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT price, seller_id FROM marketplace_items WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            return False
        
        # Check if user has enough credits
        cursor.execute("SELECT credits FROM users WHERE user_id = ?", (buyer_id,))
        user = cursor.fetchone()
        
        if user and user['credits'] >= item['price']:
            # Deduct credits
            cursor.execute("UPDATE users SET credits = credits - ? WHERE user_id = ?", (item['price'], buyer_id))
            # Add to seller
            cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (item['price'] * 0.9, item['seller_id']))
            # Record purchase
            cursor.execute("""
                INSERT INTO marketplace_purchases (buyer_id, item_id, price)
                VALUES (?, ?, ?)
            """, (buyer_id, item_id, item['price']))
            # Update item stats
            cursor.execute("UPDATE marketplace_items SET downloads = downloads + 1 WHERE id = ?", (item_id,))
            self.conn.commit()
            return True
        return False
    
    # Analytics methods
    def log_analytics(self, user_id: int, event_type: str, event_data: Dict):
        """Log analytics event"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO analytics_events (user_id, event_type, event_data)
            VALUES (?, ?, ?)
        """, (user_id, event_type, json.dumps(event_data)))
        self.conn.commit()
    
    def get_analytics(self, event_type: Optional[str] = None, days: int = 30) -> List[Dict]:
        """Get analytics"""
        cursor = self.conn.cursor()
        if event_type:
            cursor.execute("""
                SELECT * FROM analytics_events
                WHERE event_type = ? AND created_at > datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
            """, (event_type, days))
        else:
            cursor.execute("""
                SELECT * FROM analytics_events
                WHERE created_at > datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
            """, (days,))
        return [dict(row) for row in cursor.fetchall()]
    
    # Achievement methods
    def unlock_achievement(self, user_id: int, achievement_type: str, achievement_data: Dict):
        """Unlock achievement"""
        cursor = self.conn.cursor()
        # Check if already unlocked
        cursor.execute("""
            SELECT id FROM achievements 
            WHERE user_id = ? AND achievement_type = ?
        """, (user_id, achievement_type))
        if cursor.fetchone():
            return False
        
        cursor.execute("""
            INSERT INTO achievements (user_id, achievement_type, achievement_data)
            VALUES (?, ?, ?)
        """, (user_id, achievement_type, json.dumps(achievement_data)))
        self.conn.commit()
        
        # Add XP bonus
        self.add_xp(user_id, 50)
        return True
    
    def get_user_achievements(self, user_id: int) -> List[Dict]:
        """Get user achievements"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # Webhook methods
    def create_webhook(self, user_id: int, url: str, events: List[str]) -> int:
        """Create webhook"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO webhooks (user_id, url, events)
            VALUES (?, ?, ?)
        """, (user_id, url, json.dumps(events)))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_webhooks(self, user_id: int) -> List[Dict]:
        """Get user webhooks"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM webhooks WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # API Key methods
    def generate_api_key(self, user_id: int) -> str:
        """Generate API key"""
        import secrets
        api_key = f"zimg_{secrets.token_urlsafe(32)}"
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET api_key = ? WHERE user_id = ?", (api_key, user_id))
        self.conn.commit()
        return api_key
    
    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get user by API key"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
        result = cursor.fetchone()
        return dict(result) if result else None
    
    # Credits methods
    def add_credits(self, user_id: int, amount: int, reason: str = ""):
        """Add credits to user"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("INSERT INTO credit_history (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, amount, reason))
        self.conn.commit()
    
    def use_credits(self, user_id: int, amount: int, reason: str = "") -> bool:
        """Use credits"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result and result['credits'] >= amount:
            cursor.execute("UPDATE users SET credits = credits - ? WHERE user_id = ?", (amount, user_id))
            cursor.execute("INSERT INTO credit_history (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, -amount, reason))
            self.conn.commit()
            return True
        return False
    
    def get_user_credits(self, user_id: int) -> int:
        """Get user credits"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result['credits'] if result else 0
    
    # Statistics methods
    def get_user_statistics(self, user_id: int) -> Dict:
        """Get user statistics"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM statistics WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            stats = dict(result)
            stats['favorite_prompts'] = json.loads(stats.get('favorite_prompts', '[]'))
            return stats
        return {}
    
    def get_global_statistics(self) -> Dict:
        """Get global statistics"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT COUNT(*) as total_generations FROM generations")
        total_generations = cursor.fetchone()['total_generations']
        
        cursor.execute("SELECT SUM(total_time) as total_time FROM statistics")
        total_time = cursor.fetchone()['total_time'] or 0
        
        return {
            "total_users": total_users,
            "total_generations": total_generations,
            "total_time": total_time
        }
    
    # Preset methods (keeping existing)
    def create_preset(self, user_id: int, name: str, prompt: str, negative_prompt: str = "", steps: int = 8, width: int = 1024, height: int = 1024, is_public: bool = False) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO presets (user_id, name, prompt, negative_prompt, steps, width, height, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, prompt, negative_prompt, steps, width, height, 1 if is_public else 0))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_presets(self, user_id: Optional[int] = None, public_only: bool = False) -> List[Dict]:
        cursor = self.conn.cursor()
        if public_only:
            cursor.execute("SELECT * FROM presets WHERE is_public = 1 ORDER BY created_at DESC")
        elif user_id:
            cursor.execute("SELECT * FROM presets WHERE user_id = ? OR is_public = 1 ORDER BY created_at DESC", (user_id,))
        else:
            cursor.execute("SELECT * FROM presets ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        self.conn.close()
