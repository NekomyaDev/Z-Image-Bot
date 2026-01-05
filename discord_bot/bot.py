"""
Discord Bot for Z-Image Turbo NSFW
Simple Discord bot with image generation commands
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
    """Generate image command"""
    await interaction.response.defer(thinking=True)
    
    try:
        # Validate parameters
        gen_config = config.get("generation", {})
        max_steps = config.get("discord", {}).get("commands", {}).get("generate", {}).get("max_steps", 20)
        max_resolution = config.get("discord", {}).get("commands", {}).get("generate", {}).get("max_resolution", 2048)
        
        if steps > max_steps:
            await interaction.followup.send(f"❌ Steps cannot exceed {max_steps}")
            return
        
        if width > max_resolution or height > max_resolution:
            await interaction.followup.send(f"❌ Resolution cannot exceed {max_resolution}x{max_resolution}")
            return
        
        # Call API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/generate",
                json={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "steps": steps,
                    "width": width,
                    "height": height,
                    "seed": seed
                },
                timeout=aiohttp.ClientTimeout(total=config.get("discord", {}).get("default_timeout", 300))
            ) as response:
                if response.status == 200:
                    # Get image data
                    image_data = await response.read()
                    
                    # Create file object
                    image_file = discord.File(
                        io.BytesIO(image_data),
                        filename="generated.png"
                    )
                    
                    # Get seed from headers if available
                    seed_used = response.headers.get("X-Seed", "random")
                    
                    # Send image
                    embed = discord.Embed(
                        title="🎨 Image Generated",
                        description=f"**Prompt:** {prompt[:200]}",
                        color=0x00ff00
                    )
                    embed.add_field(name="Steps", value=str(steps), inline=True)
                    embed.add_field(name="Resolution", value=f"{width}x{height}", inline=True)
                    embed.add_field(name="Seed", value=seed_used, inline=True)
                    embed.set_image(url="attachment://generated.png")
                    
                    await interaction.followup.send(
                        embed=embed,
                        file=image_file
                    )
                else:
                    error_text = await response.text()
                    await interaction.followup.send(f"❌ Error: {error_text}")
    
    except asyncio.TimeoutError:
        await interaction.followup.send("❌ Generation timeout. Please try again.")
    except Exception as e:
        logger.error(f"Generation error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="status", description="Check bot and API status")
async def status_command(interaction: discord.Interaction):
    """Status command"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    health_data = await response.json()
                    await interaction.response.send_message(
                        f"✅ **Status:** Online\n"
                        f"**API:** {health_data.get('status', 'unknown')}\n"
                        f"**ComfyUI:** {health_data.get('comfyui', 'unknown')}"
                    )
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

