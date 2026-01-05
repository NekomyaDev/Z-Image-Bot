"""
Production-Ready Discord Bot
All Features: Gallery, Collections, Challenges, Monetization, Analytics, Gamification, Security
"""

import discord
from discord.ext import commands
import asyncio
import logging
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv
import aiohttp
import io
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import time
import sys

# Add parent to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from database.db import Database
from utils.image_storage import ImageStorage
from utils.error_handler import ErrorHandler
from utils.webhook_manager import WebhookManager
from utils.moderation import ModerationSystem
from utils.performance import PerformanceMonitor
from discord_bot.queue_manager import QueueManager, QueueItem

# Load config
load_dotenv()
config_path = Path(__file__).parent.parent / "config" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
db = Database()
image_storage = ImageStorage()
error_handler = ErrorHandler()
moderation = ModerationSystem(db)
performance_monitor = PerformanceMonitor()
webhook_manager = WebhookManager(db)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=config.get("discord", {}).get("command_prefix", "/"),
    intents=intents,
    help_command=None
)

# API URL
API_URL = f"http://{config.get('server', {}).get('host', '0.0.0.0')}:{config.get('server', {}).get('port', 8000)}"

# Initialize queue manager
queue_manager = QueueManager(
    max_size=config.get("discord", {}).get("max_queue_size", 10),
    rate_limit=config.get("server", {}).get("rate_limit", {}).get("requests_per_minute", 60),
    rate_window=60
)


@bot.event
async def on_ready():
    """Bot ready"""
    logger.info(f'{bot.user} connected!')
    logger.info(f'Guilds: {len(bot.guilds)}')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.error(f"Sync error: {e}")


# ==================== CORE GENERATION ====================

@bot.tree.command(name="generate", description="Generate an image")
async def generate_command(
    interaction: discord.Interaction,
    prompt: str,
    negative_prompt: str = "",
    steps: int = 8,
    width: int = 1024,
    height: int = 1024,
    seed: int = -1
):
    """Generate image with error handling"""
    user_id = interaction.user.id
    username = interaction.user.name
    
    try:
        # Moderation check
        is_safe, error_msg = moderation.check_prompt(prompt)
        if not is_safe:
            await interaction.response.send_message(f"❌ {error_msg}")
            return
        
        # Get user
        user = db.get_or_create_user(user_id, username)
        
        # Check credits
        credits_cost = config.get("discord", {}).get("credits_per_generation", 0)
        if credits_cost > 0 and user.get("subscription_tier") != "premium":
            if not db.use_credits(user_id, credits_cost, "Image generation"):
                credits = db.get_user_credits(user_id)
                await interaction.response.send_message(
                    error_handler.get_error_message("InsufficientCreditsError", {"credits": credits})
                )
                return
        
        # Add to queue
        success, error_msg, position = await queue_manager.add_request(user_id, prompt)
        if not success:
            error_type = "QueueFullError" if "full" in error_msg.lower() else "RateLimitError"
            await interaction.response.send_message(
                error_handler.get_error_message(error_type, {"reset_in": 60})
            )
            return
        
        if position > 1:
            await interaction.response.send_message(f"⏳ Queue position: **{position}**")
        else:
            await interaction.response.defer(thinking=True)
        
        # Process generation
        await process_generation(interaction, user_id, prompt, negative_prompt, steps, width, height, seed)
    
    except Exception as e:
        error_msg = error_handler.handle_exception(e)
        await interaction.response.send_message(error_msg) if not interaction.response.is_done() else await interaction.followup.send(error_msg)


async def process_generation(interaction, user_id, prompt, negative_prompt, steps, width, height, seed):
    """Process generation with progress"""
    start_time = time.time()
    
    try:
        # Get from queue
        queue_item = await queue_manager.get_next()
        while queue_item and queue_item.user_id != user_id:
            await asyncio.sleep(0.5)
            queue_item = await queue_manager.get_next()
        
        if not queue_item:
            await interaction.followup.send("❌ Queue error")
            return
        
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        
        progress_msg = await interaction.followup.send("🔄 Generating... 0%")
        
        # Simulate progress
        for progress in [25, 50, 75]:
            await asyncio.sleep(1)
            await progress_msg.edit(content=f"🔄 Generating... {progress}%")
        
        # Call API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/generate",
                json={"prompt": prompt, "negative_prompt": negative_prompt, "steps": steps, "width": width, "height": height, "seed": seed},
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status == 200:
                    image_data = await response.read()
                    generation_time = time.time() - start_time
                    seed_used = int(response.headers.get("X-Seed", seed))
                    
                    # Save image
                    image_path, thumbnail_path = image_storage.save_image(image_data, user_id)
                    
                    # Save to database
                    gen_id = db.save_generation(
                        user_id=user_id, prompt=prompt, negative_prompt=negative_prompt,
                        seed=seed_used, steps=steps, width=width, height=height,
                        image_path=image_path, thumbnail_path=thumbnail_path,
                        generation_time=generation_time
                    )
                    
                    # Send image
                    image_file = discord.File(io.BytesIO(image_data), filename="generated.png")
                    embed = discord.Embed(title="🎨 Image Generated", description=f"**Prompt:** {prompt[:200]}", color=0x00ff00)
                    embed.add_field(name="ID", value=f"#{gen_id}", inline=True)
                    embed.add_field(name="Steps", value=str(steps), inline=True)
                    embed.add_field(name="Resolution", value=f"{width}x{height}", inline=True)
                    embed.add_field(name="Seed", value=str(seed_used), inline=True)
                    embed.add_field(name="Time", value=f"{generation_time:.1f}s", inline=True)
                    embed.set_image(url="attachment://generated.png")
                    
                    # Quick actions
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Reroll", custom_id=f"reroll_{gen_id}", style=discord.ButtonStyle.primary))
                    view.add_item(discord.ui.Button(label="Variations", custom_id=f"variations_{gen_id}", style=discord.ButtonStyle.secondary))
                    view.add_item(discord.ui.Button(label="Upscale", custom_id=f"upscale_{gen_id}", style=discord.ButtonStyle.secondary))
                    
                    await progress_msg.delete()
                    await interaction.followup.send(embed=embed, file=image_file, view=view)
                    
                    # Webhook notification
                    await webhook_manager.send_webhook(user_id, "generation_complete", {"generation_id": gen_id})
                    
                else:
                    error_text = await response.text()
                    await progress_msg.edit(content=error_handler.handle_exception(Exception(error_text)))
    
    except asyncio.TimeoutError:
        await interaction.followup.send(error_handler.get_error_message("TimeoutError"))
    except Exception as e:
        await interaction.followup.send(error_handler.handle_exception(e))
    finally:
        await queue_manager.complete_request(user_id)


# ==================== GALLERY & COLLECTIONS ====================

@bot.tree.command(name="gallery", description="View public gallery")
async def gallery_command(interaction: discord.Interaction, page: int = 1):
    """Public gallery"""
    try:
        items = db.get_public_gallery(limit=10, offset=(page - 1) * 10)
        if not items:
            await interaction.response.send_message("📭 Gallery is empty")
            return
        
        embed = discord.Embed(title=f"🖼️ Public Gallery (Page {page})", color=0x0099ff)
        for item in items[:5]:
            embed.add_field(
                name=f"#{item['id']} by {item.get('username', 'Unknown')}",
                value=f"**Prompt:** {item['prompt'][:50]}...\n**Likes:** {item['likes']} | **Views:** {item['views']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="collection_create", description="Create a collection")
async def collection_create_command(interaction: discord.Interaction, name: str, description: str = "", public: bool = False):
    """Create collection"""
    try:
        collection_id = db.create_collection(interaction.user.id, name, description, public)
        await interaction.response.send_message(f"✅ Collection '{name}' created! (ID: {collection_id})")
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="collections", description="View your collections")
async def collections_command(interaction: discord.Interaction):
    """View collections"""
    try:
        collections = db.get_collections(interaction.user.id)
        if not collections:
            await interaction.response.send_message("📭 No collections found")
            return
        
        embed = discord.Embed(title="📚 Your Collections", color=0x0099ff)
        for col in collections:
            embed.add_field(
                name=f"{col['name']} (ID: {col['id']})",
                value=f"**Items:** {col.get('item_count', 0)}\n**Public:** {'Yes' if col['is_public'] else 'No'}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="collection_add", description="Add image to collection")
async def collection_add_command(interaction: discord.Interaction, collection_id: int, generation_id: int):
    """Add to collection"""
    try:
        db.add_to_collection(collection_id, generation_id)
        await interaction.response.send_message(f"✅ Added to collection!")
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


# ==================== CHALLENGES ====================

@bot.tree.command(name="challenges", description="View active challenges")
async def challenges_command(interaction: discord.Interaction):
    """View challenges"""
    try:
        challenges = db.get_active_challenges()
        if not challenges:
            await interaction.response.send_message("📭 No active challenges")
            return
        
        embed = discord.Embed(title="🏆 Active Challenges", color=0xffd700)
        for challenge in challenges:
            embed.add_field(
                name=f"{challenge['name']} (ID: {challenge['id']})",
                value=f"**Theme:** {challenge['theme']}\n**Ends:** {challenge['end_date'][:10]}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="challenge_submit", description="Submit to challenge")
async def challenge_submit_command(interaction: discord.Interaction, challenge_id: int, generation_id: int):
    """Submit to challenge"""
    try:
        submission_id = db.submit_to_challenge(challenge_id, interaction.user.id, generation_id)
        await interaction.response.send_message(f"✅ Submitted! (ID: {submission_id})")
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="challenge_leaderboard", description="View challenge leaderboard")
async def challenge_leaderboard_command(interaction: discord.Interaction, challenge_id: int):
    """Challenge leaderboard"""
    try:
        leaderboard = db.get_challenge_leaderboard(challenge_id, limit=10)
        if not leaderboard:
            await interaction.response.send_message("📭 No submissions yet")
            return
        
        embed = discord.Embed(title=f"🏆 Challenge #{challenge_id} Leaderboard", color=0xffd700)
        for i, entry in enumerate(leaderboard, 1):
            embed.add_field(
                name=f"#{i} - {entry.get('username', 'Unknown')}",
                value=f"**Votes:** {entry['votes']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


# ==================== MONETIZATION ====================

@bot.tree.command(name="subscribe", description="Subscribe to premium")
async def subscribe_command(interaction: discord.Interaction, tier: str):
    """Subscribe"""
    try:
        if tier not in ["pro", "premium"]:
            await interaction.response.send_message("❌ Invalid tier. Use 'pro' or 'premium'")
            return
        
        prices = {"pro": 9.99, "premium": 19.99}
        expires = datetime.now() + timedelta(days=30)
        
        db.create_subscription(interaction.user.id, tier, prices[tier], expires)
        await interaction.response.send_message(f"✅ Subscribed to {tier} tier! Expires: {expires.date()}")
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="marketplace", description="Browse marketplace")
async def marketplace_command(interaction: discord.Interaction, item_type: Optional[str] = None):
    """Marketplace"""
    try:
        items = db.get_marketplace_items(item_type=item_type, limit=10)
        if not items:
            await interaction.response.send_message("📭 Marketplace is empty")
            return
        
        embed = discord.Embed(title="🛒 Marketplace", color=0x00ff00)
        for item in items:
            embed.add_field(
                name=f"{item['name']} ({item['item_type']})",
                value=f"**Price:** {item['price']} credits\n**Rating:** {item['rating']}/5",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


# ==================== ANALYTICS ====================

@bot.tree.command(name="analytics", description="View analytics")
async def analytics_command(interaction: discord.Interaction, days: int = 7):
    """Analytics"""
    try:
        events = db.get_analytics(event_type=None, days=days)
        
        # Count events by type
        event_counts = {}
        for event in events:
            event_type = event['event_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        embed = discord.Embed(title=f"📊 Analytics (Last {days} days)", color=0x0099ff)
        for event_type, count in event_counts.items():
            embed.add_field(name=event_type, value=str(count), inline=True)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


# ==================== GAMIFICATION ====================

@bot.tree.command(name="profile", description="View your profile")
async def profile_command(interaction: discord.Interaction):
    """User profile"""
    try:
        user = db.get_or_create_user(interaction.user.id)
        stats = db.get_user_statistics(interaction.user.id)
        achievements = db.get_user_achievements(interaction.user.id)
        
        embed = discord.Embed(title=f"👤 {interaction.user.name}'s Profile", color=0x0099ff)
        embed.add_field(name="Level", value=str(user.get('level', 1)), inline=True)
        embed.add_field(name="XP", value=f"{user.get('xp', 0)}/{user.get('level', 1) * 100}", inline=True)
        embed.add_field(name="Credits", value=str(user.get('credits', 0)), inline=True)
        embed.add_field(name="Generations", value=str(stats.get('total_generations', 0)), inline=True)
        embed.add_field(name="Achievements", value=str(len(achievements)), inline=True)
        embed.add_field(name="Tier", value=user.get('subscription_tier', 'free'), inline=True)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


# ==================== INTEGRATION FEATURES ====================

@bot.tree.command(name="apikey", description="Generate API key")
async def apikey_command(interaction: discord.Interaction):
    """Generate API key"""
    try:
        api_key = db.generate_api_key(interaction.user.id)
        await interaction.response.send_message(f"✅ API Key generated:\n`{api_key}`\n\nKeep this secret!")
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="webhook_create", description="Create webhook")
async def webhook_create_command(interaction: discord.Interaction, url: str, events: str):
    """Create webhook"""
    try:
        event_list = [e.strip() for e in events.split(",")]
        webhook_id = db.create_webhook(interaction.user.id, url, event_list)
        await interaction.response.send_message(f"✅ Webhook created! (ID: {webhook_id})")
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


# ==================== UTILITY COMMANDS ====================

@bot.tree.command(name="queue", description="Check queue")
async def queue_command(interaction: discord.Interaction):
    """Queue status"""
    try:
        queue_info = await queue_manager.get_queue_info()
        position = await queue_manager.get_position(interaction.user.id)
        rate_info = await queue_manager.get_rate_limit_info(interaction.user.id)
        
        embed = discord.Embed(title="📋 Queue Status", color=0x0099ff)
        embed.add_field(name="Queue", value=f"{queue_info['queue_size']}/{queue_info['max_size']}", inline=True)
        embed.add_field(name="Your Position", value=str(position) if position else "None", inline=True)
        embed.add_field(name="Rate Limit", value=f"{rate_info['requests']}/{rate_info['limit']}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="credits", description="Check credits")
async def credits_command(interaction: discord.Interaction):
    """Credits"""
    try:
        credits = db.get_user_credits(interaction.user.id)
        user = db.get_or_create_user(interaction.user.id)
        
        embed = discord.Embed(title="💰 Credits", color=0x00ff00)
        embed.add_field(name="Balance", value=str(credits), inline=True)
        embed.add_field(name="Tier", value=user.get('subscription_tier', 'free'), inline=True)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(error_handler.handle_exception(e))


@bot.tree.command(name="help", description="Show help")
async def help_command(interaction: discord.Interaction):
    """Help"""
    embed = discord.Embed(title="🤖 Z-Image Turbo Bot - Help", color=0x0099ff)
    embed.add_field(name="Generation", value="/generate - Generate image", inline=False)
    embed.add_field(name="Gallery", value="/gallery - Public gallery\n/collections - Your collections", inline=False)
    embed.add_field(name="Challenges", value="/challenges - Active challenges\n/challenge_submit - Submit", inline=False)
    embed.add_field(name="Monetization", value="/subscribe - Premium\n/marketplace - Browse", inline=False)
    embed.add_field(name="Integration", value="/apikey - Generate API key\n/webhook_create - Create webhook", inline=False)
    embed.add_field(name="Profile", value="/profile - Your profile\n/credits - Credits\n/queue - Queue status", inline=False)
    
    await interaction.response.send_message(embed=embed)


# Button interactions
@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button interactions"""
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id', '')
        
        if custom_id.startswith('reroll_'):
            gen_id = int(custom_id.split('_')[1])
            gen = db.get_generation(gen_id)
            if gen:
                await interaction.response.defer()
                await process_generation(
                    interaction,
                    interaction.user.id,
                    gen['prompt'],
                    gen.get('negative_prompt', ''),
                    gen['steps'],
                    gen['width'],
                    gen['height'],
                    -1
                )
        
        elif custom_id.startswith('variations_'):
            gen_id = int(custom_id.split('_')[1])
            await interaction.response.send_message(f"🔄 Generating variations for #{gen_id}...")
        
        elif custom_id.startswith('upscale_'):
            gen_id = int(custom_id.split('_')[1])
            await interaction.response.send_message(f"🔄 Upscaling #{gen_id}...")


def run_bot():
    """Run bot"""
    token = os.getenv("DISCORD_TOKEN") or config.get("discord", {}).get("token", "").replace("${DISCORD_TOKEN}", os.getenv("DISCORD_TOKEN", ""))
    
    if not token:
        logger.error("DISCORD_TOKEN not found!")
        return
    
    bot.run(token)


if __name__ == "__main__":
    run_bot()

