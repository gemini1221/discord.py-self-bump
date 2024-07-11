import os
import asyncio
import aiohttp
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import logging
import discord
from discord import app_commands

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の取得と検証
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

if not all([TOKEN, GUILD_ID, CHANNEL_ID]):
    raise ValueError("必要な環境変数が設定されていません。")

GUILD_ID = int(GUILD_ID)
CHANNEL_ID = int(CHANNEL_ID)

# コマンドIDを定義
commands_info = {
    "dissoku up": 828002256690610256,
    "bump": 947088344167366698
}

cooldowns = {
    "dissoku up": timedelta(hours=1),
    "bump": timedelta(hours=2)
}

last_executed = {cmd: datetime.min for cmd in cooldowns}

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.session = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

    async def close(self):
        await self.session.close()
        await super().close()

bot = MyBot()

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
    command_id = commands_info[command]
    url = "https://discord.com/api/v9/interactions"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "type": 2,
        "application_id": bot.user.id,
        "guild_id": GUILD_ID,
        "channel_id": CHANNEL_ID,
        "data": {
            "id": str(command_id),
            "name": command,
            "type": 1
        }
    }
    logger.info(f"Sending command {command} with ID {command_id}")
    try:
        async with bot.session.post(url, headers=headers, json=data) as resp:
            response_text = await resp.text()
            if resp.status == 204:
                logger.info(f"Sent command: {command}")
            else:
                logger.error(f"Error sending command {command}: {resp.status} - {response_text}")
    except aiohttp.ClientError as e:
        logger.error(f"HTTP request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

@bot.tree.command(name="quote", description="引用画像を生成します", guild=discord.Object(id=GUILD_ID))
async def quote(interaction: discord.Interaction, message_id: str):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        message = await channel.fetch_message(int(message_id))
        
        payload = {
            "username": message.author.name,
            "display_name": message.author.display_name,
            "text": message.content,
            "avatar": str(message.author.avatar.url),
            "color": True
        }
        
        async with bot.session.post("https://api.voids.top/quote", json=payload) as resp:
            if resp.status == 200:
                quote_data = await resp.json()
                await interaction.response.send_message(quote_data['url'])
            else:
                logger.error(f"Error from quote API: {resp.status}")
                await interaction.response.send_message("引用画像の生成に失敗しました。", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in quote command: {e}")
        await interaction.response.send_message("エラーが発生しました。", ephemeral=True)

@bot.event
async def on_message(message):
    if message.guild.id != GUILD_ID or message.channel.id != CHANNEL_ID:
        return

    if message.content.lower() == "miaq" and message.reference:
        await quote(message, str(message.reference.message_id))

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
