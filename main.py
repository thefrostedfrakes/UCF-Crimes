'''

UCF Crimes: main.py
Written by Ethan Frakes

'''

import discord
from discord.ext import commands
import time
from datetime import date, timedelta
import asyncio
from configparser import ConfigParser
from loadcrimes import crime_load, backup_crimes, load_crime_and_status_lists, setup_db
from sendcrimes import crime_send, list_locations, list_crimes
from image import generate_heatmap
from get_place_name import change_all_addresses
    
intents = discord.Intents.all()
client = commands.Bot(intents=intents, command_prefix = '!')
client.remove_command('help')

main_config = ConfigParser()
main_config.read('config.ini')

bot_channel_id = main_config.get("DISCORD", "CRIME_CHANNEL_ID")

@client.event
async def on_ready():
    print("CrimeBot is online!")
    await client.wait_until_ready()

    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} commands")
    
    except Exception as e:
        print(f"Error syncing commands: {e}")

    while not client.is_closed():
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)

        if current_time == "00:30:00":
            today = date.today()
            yesterday = (today - timedelta(days=1)).strftime("%m/%d/%y")
            await crime_send(None, client, yesterday, bot_channel_id, main_config)

        await asyncio.sleep(1)

@client.tree.command(name='ping', description="Ping the bot! (Just to test)")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{interaction.user.mention} pong!", ephemeral=True)

@client.tree.command(name='crimes', description="Search for all available crimes in the database. Search by date, location, or status.")
async def crimes(interaction: discord.Interaction, parameter: str):
    if parameter == "all":
        await list_crimes(interaction, client, bot_channel_id)
    else:
        await crime_send(interaction, client, parameter, bot_channel_id, main_config)

@client.tree.command(name='locations', description="List all available locations in the database.")
async def locations(interaction: discord.Interaction):
    await list_locations(interaction, client, bot_channel_id)

@client.tree.command(name='heatmap', description="View a heatmap of all reported crimes at the main campus, downtown campus, or Rosen.")
async def heatmap(interaction: discord.Interaction, campus: str):
    await generate_heatmap(interaction, campus, main_config)

@client.event
async def on_message(message: discord.Message):
    try:
        print(f"User {message.author} just sent this message in {message.channel.name}: {message.content}")
    except AttributeError as e:
        print(f"Error displaying message sent by {message.author}: {e}")

    if message.content.startswith('-loadcrimes') or message.content.startswith('-addcrimes'):
        if not message.author.guild_permissions.administrator:
            await message.reply('Sorry, you do not have permission to use this command!')
            return
        crime_load(message.content, main_config.get("DISCORD", "GMAPS_API_KEY"))

    elif message.content.startswith('-backup'):
        backup_crimes()

    elif message.content.startswith('-crime-status-list'):
        if not message.author.guild_permissions.administrator:
            await message.reply('Sorry, you do not have permission to use this command!')
            return
        load_crime_and_status_lists()

    elif message.content.startswith('-change_all_places'):
        if not message.author.guild_permissions.administrator:
            await message.reply('Sorry, you do not have permission to use this command!')
            return
        change_all_addresses(main_config.get("DISCORD", "GMAPS_API_KEY"))

client.run(main_config.get("DISCORD", "TOKEN"))
