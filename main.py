import os
import asyncio
import aiohttp
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

cooldowns = {
    "dissoku up": timedelta(hours=1),
    "bump": timedelta(hours=2)
}

last_executed = {cmd: datetime.min for cmd in cooldowns}

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    execute_command.start()

@tasks.loop(seconds=60)
async def execute_command():
    now = datetime.now()
    for command, cooldown in cooldowns.items():
        if now - last_executed[command] >= cooldown:
            last_executed[command] = now
            await send_command(command)

async def send_command(command):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        try:
            await channel.send(f"/{command}")
            logger.info(f"Sent command: {command}")
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
    else:
        logger.error(f"Channel with ID {CHANNEL_ID} not found")

@bot.event
async def on_message(message):
    if message.guild.id != GUILD_ID or message.channel.id != CHANNEL_ID:
        return

    if message.content.lower() == "miaq" and message.reference:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "username": ref_msg.author.name,
                    "display_name": ref_msg.author.display_name,
                    "text": ref_msg.content,
                    "avatar": str(ref_msg.author.avatar.url),
                    "color": True
                }
                async with session.post("https://api.voids.top/quote", json=payload) as resp:
                    if resp.status == 200:
                        quote_data = await resp.json()
                        await message.channel.send(quote_data['url'])
                    else:
                        logger.error(f"Error from quote API: {resp.status}")
        except Exception as e:
            logger.error(f"Error processing 'miaq' command: {e}")

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
