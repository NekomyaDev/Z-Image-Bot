"""
Enhanced Discord Bot with Queue, Progress, and History
Production-ready features
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
from datetime import datetime
from typing import Optional, Dict, List

from .queue_manager import QueueManager, QueueItem

# Load environment variables
load_dotenv()

# Load config
config_path = Path(__file__).parent.parent / "config" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
queue_config = config.get("discord", {})
queue_manager = QueueManager(
    max_size=queue_config.get("max_queue_size", 10),
    rate_limit=config.get("server", {}).get("rate_limit", {}).get("requests_per_minute", 60),
    rate_window=60
)

# Simple history storage (in production, use database)
user_history: Dict[int, List[Dict]] = {}


@bot.event
async def on_ready():
    """Called when bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")


@bot.tree.command(name="generate", description="Generate an image with Z-Image Turbo NSFW")
async def generate_command(
    interaction: discord.Interaction,
    prompt: str,
    negative_prompt: str = "",
    steps: int = 8,
    width: int = 1024,
    height: int = 1024,
    seed: int = -1
):
    """Generate image command with queue support"""
    user_id = interaction.user.id
    
    # Check rate limit and add to queue
    success, error_msg, position = await queue_manager.add_request(user_id, prompt)
    
    if not success:
        await interaction.response.send_message(f"❌ {error_msg}")
        return
    
    # Show queue position if not first
    if position > 1:
        await interaction.response.send_message(
            f"⏳ Added to queue. Position: **{position}**\n"
            f"**Prompt:** {prompt[:100]}..."
        )
    else:
        await interaction.response.defer(thinking=True)
    
    # Wait for turn
    while True:
        queue_item = await queue_manager.get_next()
        if queue_item and queue_item.user_id == user_id:
            break
        elif queue_item:
            # Process other user's request
            await process_generation(queue_item, interaction)
        else:
            await asyncio.sleep(1)
    
    # Process user's request
    await process_generation(queue_item, interaction, user_id)


async def process_generation(
    queue_item: QueueItem,
    interaction: discord.Interaction,
    user_id: Optional[int] = None
):
    """Process generation request"""
    if user_id is None:
        user_id = queue_item.user_id
    
    try:
        # Update message if in queue
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        else:
            await interaction.followup.send("🔄 Processing your request...")
        
        # Call API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/generate",
                json={
                    "prompt": queue_item.prompt,
                    "negative_prompt": "",
                    "steps": 8,
                    "width": 1024,
                    "height": 1024,
                    "seed": -1
                },
                timeout=aiohttp.ClientTimeout(total=config.get("discord", {}).get("default_timeout", 300))
            ) as response:
                if response.status == 200:
                    # Get image data
                    image_data = await response.read()
                    
                    # Save to history
                    if user_id not in user_history:
                        user_history[user_id] = []
                    
                    history_item = {
                        "prompt": queue_item.prompt,
                        "timestamp": datetime.now().isoformat(),
                        "seed": response.headers.get("X-Seed", "random")
                    }
                    user_history[user_id].append(history_item)
                    
                    # Create file object
                    image_file = discord.File(
                        io.BytesIO(image_data),
                        filename="generated.png"
                    )
                    
                    # Get seed from headers
                    seed_used = response.headers.get("X-Seed", "random")
                    
                    # Send image
                    embed = discord.Embed(
                        title="🎨 Image Generated",
                        description=f"**Prompt:** {queue_item.prompt[:200]}",
                        color=0x00ff00
                    )
                    embed.add_field(name="Steps", value="8", inline=True)
                    embed.add_field(name="Resolution", value="1024x1024", inline=True)
                    embed.add_field(name="Seed", value=seed_used, inline=True)
                    embed.set_image(url="attachment://generated.png")
                    
                    if interaction.response.is_done():
                        await interaction.followup.send(embed=embed, file=image_file)
                    else:
                        await interaction.followup.send(embed=embed, file=image_file)
                else:
                    error_text = await response.text()
                    await interaction.followup.send(f"❌ Error: {error_text}")
    
    except asyncio.TimeoutError:
        await interaction.followup.send("❌ Generation timeout. Please try again.")
    except Exception as e:
        logger.error(f"Generation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")
    finally:
        await queue_manager.complete_request(user_id)


@bot.tree.command(name="queue", description="Check queue status")
async def queue_command(interaction: discord.Interaction):
    """Queue status command"""
    user_id = interaction.user.id
    queue_info = await queue_manager.get_queue_info()
    position = await queue_manager.get_position(user_id)
    rate_info = await queue_manager.get_rate_limit_info(user_id)
    
    embed = discord.Embed(
        title="📋 Queue Status",
        color=0x0099ff
    )
    
    embed.add_field(
        name="Queue",
        value=f"**Size:** {queue_info['queue_size']}/{queue_info['max_size']}\n"
              f"**Processing:** {queue_info['processing']}\n"
              f"**Your Position:** {position if position else 'None'}",
        inline=False
    )
    
    embed.add_field(
        name="Rate Limit",
        value=f"**Requests:** {rate_info['requests']}/{rate_info['limit']}\n"
              f"**Reset in:** {rate_info['reset_in']}s",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="history", description="View your generation history")
async def history_command(interaction: discord.Interaction, page: int = 1):
    """View generation history"""
    user_id = interaction.user.id
    
    if user_id not in user_history or not user_history[user_id]:
        await interaction.response.send_message("📭 No generation history found.")
        return
    
    # Pagination
    items_per_page = 10
    total_items = len(user_history[user_id])
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Available: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    page_items = user_history[user_id][start_idx:end_idx]
    
    embed = discord.Embed(
        title="📚 Generation History",
        description=f"Page {page}/{total_pages}",
        color=0x0099ff
    )
    
    for i, item in enumerate(page_items, start=start_idx + 1):
        timestamp = item.get("timestamp", "Unknown")
        prompt = item.get("prompt", "N/A")[:50]
        seed = item.get("seed", "random")
        
        embed.add_field(
            name=f"#{i}",
            value=f"**Prompt:** {prompt}...\n**Seed:** {seed}\n**Time:** {timestamp[:19]}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="cancel", description="Cancel your queued request")
async def cancel_command(interaction: discord.Interaction):
    """Cancel queued request"""
    user_id = interaction.user.id
    cancelled = await queue_manager.cancel_request(user_id)
    
    if cancelled:
        await interaction.response.send_message("✅ Request cancelled.")
    else:
        await interaction.response.send_message("❌ No request to cancel or request is already processing.")


@bot.tree.command(name="status", description="Check bot and API status")
async def status_command(interaction: discord.Interaction):
    """Status command"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    health_data = await response.json()
                    queue_info = await queue_manager.get_queue_info()
                    
                    embed = discord.Embed(
                        title="✅ Bot Status",
                        color=0x00ff00
                    )
                    embed.add_field(name="API", value=health_data.get('status', 'unknown'), inline=True)
                    embed.add_field(name="ComfyUI", value=health_data.get('comfyui', 'unknown'), inline=True)
                    embed.add_field(name="Queue", value=f"{queue_info['queue_size']}/{queue_info['max_size']}", inline=True)
                    
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("⚠️ API is not responding")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}")


@bot.tree.command(name="help", description="Show help message")
async def help_command(interaction: discord.Interaction):
    """Help command"""
    embed = discord.Embed(
        title="🤖 Z-Image Turbo NSFW Bot",
        description="Image generation bot using Z-Image Turbo NSFW model",
        color=0x0099ff
    )
    
    embed.add_field(
        name="/generate",
        value="Generate an image\n"
              "**Parameters:**\n"
              "- `prompt`: Your image prompt (required)\n"
              "- `negative_prompt`: Negative prompt (optional)\n"
              "- `steps`: Number of steps (default: 8, max: 20)\n"
              "- `width`: Image width (default: 1024, max: 2048)\n"
              "- `height`: Image height (default: 1024, max: 2048)\n"
              "- `seed`: Seed for generation (-1 for random)",
        inline=False
    )
    
    embed.add_field(
        name="/queue",
        value="Check queue status and your position",
        inline=False
    )
    
    embed.add_field(
        name="/history",
        value="View your generation history",
        inline=False
    )
    
    embed.add_field(
        name="/cancel",
        value="Cancel your queued request",
        inline=False
    )
    
    embed.add_field(
        name="/status",
        value="Check bot and API status",
        inline=False
    )
    
    embed.add_field(
        name="/help",
        value="Show this help message",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)


def run_bot():
    """Run Discord bot"""
    token = os.getenv("DISCORD_TOKEN") or config.get("discord", {}).get("token", "").replace("${DISCORD_TOKEN}", os.getenv("DISCORD_TOKEN", ""))
    
    if not token or token == "":
        logger.error("DISCORD_TOKEN not found in environment or config!")
        logger.error("Please set DISCORD_TOKEN in .env file or environment variable")
        return
    
    bot.run(token)


if __name__ == "__main__":
    run_bot()

