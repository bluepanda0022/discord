import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    await sync_commands()

async def sync_commands():
    guild = discord.Object(id=1144201109154566154)
    await bot.tree.sync(guild=guild)

@bot.tree.command(name="test")
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("Hello from the test command!")
    
bot.run('MTI4NTQ3MDQ2MjEwNDgzMDAzNg.G6UQXQ.UpdeB_7_Ppla8P0AMCcgVWdRcDi6OblePv83Aw')