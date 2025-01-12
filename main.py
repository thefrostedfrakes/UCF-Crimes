'''

UCF Crimes: main.py
Written by Ethan Frakes

'''

import discord
from discord.ext import commands, tasks
from datetime import date, datetime, timedelta
from configparser import ConfigParser
from loadcrimes import crime_load, backup_crimes, load_crime_and_status_lists
from sendcrimes import crime_send, list_locations, list_crimes, send_hourly
from image import generate_heatmap
from utils import bot_help, change_all_addresses
    
intents = discord.Intents.all()
client = commands.Bot(intents=intents, command_prefix = '!')
client.remove_command('help')

main_config = ConfigParser()
main_config.read('config.ini')

bot_channel_id = main_config.getint("DISCORD", "CRIME_CHANNEL_ID")

@client.event
async def on_ready():
    print("CrimeBot is online!")
    await client.wait_until_ready()

    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} commands")
    
    except Exception as e:
        print(f"Error syncing commands: {e}")

    time_checker.start()
        
@tasks.loop(seconds=60)
async def time_checker():
    t = datetime.now()
    orlando_minute = main_config.getint("DISCORD", "ORLANDO_MINUTE")
    ucf_hour = main_config.getint("DISCORD", "UCF_HOUR")
    ucf_minute = main_config.getint("DISCORD", "UCF_MINUTE")

    if t.minute == orlando_minute:
        date_hour = (datetime.now() - timedelta(hours=1)).strftime("%-m/%d/%Y %H")
        await send_hourly(None, date_hour, client, main_config, "orlando", 12)
        await send_hourly(None, date_hour, client, main_config, "orange", 11)

    if t.hour == ucf_hour and t.minute == ucf_minute:
        today = date.today()
        yesterday = (today - timedelta(days=1)).strftime("%m/%d/%y")
        await crime_send(None, client, yesterday, bot_channel_id, main_config)

@client.tree.command(name='ping', description="Ping the bot! (Just to test)")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{interaction.user.mention} pong!", ephemeral=True)

@client.tree.command(name='help', description="View all bot commands and their functionality.")
async def help(interaction: discord.Interaction):
    await bot_help(interaction)

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

@client.tree.command(name='orlando', description="List all orlando crime reports from the last hour.")
@commands.has_permissions(administrator=True)
async def orlando(interaction: discord.Interaction):
    date_hour = (datetime.now() - timedelta(hours=1)).strftime("%-m/%d/%Y %H")
    await send_orlando(interaction, date_hour, client, main_config)

@client.tree.command(name='servers', description="List all servers")
@commands.has_permissions(administrator=True)
async def servers(interaction: discord.Interaction):
    guild_str = ""
    for guild in client.guilds:
        guild_str += f"{guild.name}\n"
    await interaction.response.send_message(guild_str)

@client.event
async def on_message(message: discord.Message):
    try:
        print(f"User {message.author} just sent this message in {message.channel.name}: {message.content}")
    except AttributeError as e:
        print(f"Error displaying message sent by {message.author}: {e}")

    # if message.content.startswith('-loadcrimes') or message.content.startswith('-addcrimes'):
    #     if not message.author.guild_permissions.administrator:
    #         await message.reply('Sorry, you do not have permission to use this command!')
    #         return
    #     crime_load(message.content, main_config.get("DISCORD", "GMAPS_API_KEY"))

    if message.content.startswith('-backup'):
        if not message.author.guild_permissions.administrator:
            await message.reply('Sorry, you do not have permission to use this command!')
            return
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
