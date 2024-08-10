'''

UCF Crimes: sendcrimes.py
Written by Ethan Frakes
and Maverick Reynolds

'''

import utils
import json
import pandas as pd
from typing import Optional
import discord
from discord.ext import commands
from datetime import datetime
from image import generate_image, orlando_hourly_heatmap
from sqlalchemy.engine.base import Engine
from sqlalchemy import text
from discord import TextChannel
from configparser import ConfigParser

async def is_channel(interaction: discord.Interaction, client: commands.Bot, channel_id: str) -> bool:
    '''
    Check if the channel is the permitted bot channel. Returns a message to user asking to use channel if false.
    '''

    channel = client.get_channel(int(channel_id))

    if interaction.channel == channel:
        return True
    
    await interaction.response.send_message(f"Please post in the {channel.mention} channel to use this command!",
                                            ephemeral=True)
    return False

async def crime_sender(channel: TextChannel, crime: pd.Series) -> None:
    '''
    Wrapper for formatting Discord embed containing queried crime info to send to channel.
    '''

    generate_image(crime)

    # Reformat dates and times
    report_date_time = datetime.strptime(crime["report_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["start_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["end_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')

    # Format title
    case_title = crime["title"][0:255]
    # Get emojis
    case_emojis = utils.get_emojis(case_title)
    # Use language model AFTER formatting if enabled and AFTER emojis are retrieved
    # Append emojis to title
    case_title += case_emojis

    place = crime["place"] # replace_address already called in loadcrimes.py
    
    # Compose message
    description = f"Occurred at {utils.titlize(crime['campus'])}, {place} \n" \
                  f"Case: {crime['case_id']} \n" \
                  f"Reported on {report_date_time} \n" \
                  f"Between {start_date_time} - {end_date_time} \n" \
                  f"Status: {crime['disposition'].title()}" 

    # Insert case title & description into discord bot channel.
    embed = discord.Embed(
        title=case_title,
        description=description,
            
        color = discord.Color.red()
    ).set_image(url='attachment://caseout.png')

    await channel.send(embed=embed, file=discord.File('caseout.png'))

async def crime_send_sql(interaction: Optional[discord.Interaction], 
                        client: commands.Bot, 
                        command_arg: str, 
                        channel: TextChannel, 
                        engine: Engine,
                        ) -> None:
    
    # Open necessary json files.
    with open('locations.json', 'r') as f:
        locations = json.load(f)

    with open('crime_list.json', 'r') as f:
        crime_list = json.load(f)

    with open('status_list.json', 'r') as f:
        status_list = json.load(f)
    
    command_arg = command_arg.upper()
    if utils.is_valid_date(command_arg):
        try:
            date_str = datetime.strptime(command_arg, "%m/%d/%y").strftime("%A, %B %d, %Y")
            command_arg = datetime.strptime(command_arg, "%m/%d/%y").strftime("%Y-%m-%d")
        except ValueError:
            date_str = datetime.strptime(command_arg, "%m/%d/%Y").strftime("%A, %B %d, %Y")
            command_arg = datetime.strptime(command_arg, "%m/%d/%Y").strftime("%Y-%m-%d")

        # Respond to interaction if the command was triggered by user. If not, then the command was
        # executed automatically for daily crime listing.
        if interaction:
            await interaction.response.send_message(f"Reported Crimes for {date_str}")
        else:
            await channel.send(f"Reported Crimes for {date_str}")

        query_param = "report_dt::date"
    
    # If command argument is a crime title or disposition, dataframe key is set to either title or
    # disposition accordingly.
    elif crime_list.get(command_arg):
        query_param = "title"
        await interaction.response.send_message(f"Reported Crimes for {command_arg.title()}")

    elif status_list.get(command_arg):
        query_param = "disposition"
        await interaction.response.send_message(f"Reported Crimes with status {command_arg.title()}")

    elif command_arg.upper() in locations.keys():
        query_param = "address"
        await interaction.response.send_message(f"Reported Crimes at {command_arg.title()}")

    elif place_name := next((place for place in locations.values() if place.lower() == command_arg.lower()), None):
        query_param = "place"
        command_arg = place_name
        await interaction.response.send_message(f"Reported Crimes at {command_arg.title()}")

    else:
        return await interaction.response.send_message("Please search for a crime by type, valid date, or valid location.",
                                                        ephemeral=True)

    query = f"SELECT * FROM crimes WHERE {query_param} = '{command_arg}';"
    query_matches = pd.read_sql_query(query, engine)
    crimeCount = len(query_matches)

    # For all crimes in matches, crime_sender sends as Discord embed.
    for index, crime in query_matches.iterrows():
        await crime_sender(channel, crime)

    # If number of crimes in query dataframe is 0, no reported crimes message is sent.
    # Number of reported crimes is sent otherwise.
    if (crimeCount == 0):
        await channel.send("No reported crimes.")
    else:
        await channel.send(f"{crimeCount} reported crimes.")

    print("Crimes retrieved.")

async def crime_send(interaction: Optional[discord.Interaction], 
                    client: commands.Bot, 
                    command_arg: str, 
                    channel_id: str, 
                    main_config: ConfigParser,
                    ) -> None:

    engine = utils.setup_db(main_config)
    # Check if command was sent to bot channel.
    if interaction is not None and not await is_channel(interaction, client, channel_id):
        return

    # Get bot channel from id to send to channel. Sent after interaction response.
    channel = client.get_channel(int(channel_id))

    await crime_send_sql(interaction, client, command_arg, channel, engine)
    
async def list_locations(interaction: discord.Interaction, client: commands.Bot, channel_id: str) -> None:
    '''
    Locations json is listed as Discord embed pages.
    '''
    if not await is_channel(interaction, client, channel_id):
        return
    
    with open('locations.json', 'r') as f:
        locations = json.load(f)

    fieldCount = 0
    page = 1
    embeds = []
    embed = discord.Embed(title="All Locations in Database (Page " + str(page) + "):", color=discord.Color.blue())
    for key, val in locations.items():
        fieldCount += 1
        if (fieldCount >= 25):
            page += 1
            embeds.append(embed)
            embed = discord.Embed(title="All Locations in Database (Page " + str(page) + "):", color=discord.Color.blue())
            fieldCount = 0
            
        embed.add_field(name=val, value=key, inline=False)

    embeds.append(embed)
    await interaction.response.send_message(embeds=embeds)

async def list_crimes(interaction: discord.Interaction, client: commands.Bot, channel_id: str) -> None:
    '''
    Crimes json is listed as Discord embed pages.
    '''

    if not await is_channel(interaction, client, channel_id):
        return
    
    await interaction.response.defer()
    with open('crime_list.json', 'r') as f:
        crime_list = json.load(f)
        
    fieldCount = 0
    page = 1
    color = discord.Color.blue()

    embed = discord.Embed(title=f"All Crime Names in Database (Page {page}):", color=color)
    for key, value in crime_list.items():
        fieldCount += 1
        if (fieldCount >= 25):
            page += 1
            await interaction.followup.send(embed=embed)
            embed = discord.Embed(title=f"All Crime Names in Database (Page {page}):", color=color)
            fieldCount = 0
            
        embed.add_field(name=key, value=f"Number of crimes in database: {value}", inline=False)

    await interaction.followup.send(embed=embed)

async def send_orlando(interaction: discord.Interaction | None, date_hour: str, client: commands.Bot, main_config: ConfigParser) -> None:
    '''
    Send all Orlando PD active calls within the last hour.
    '''

    if interaction:
        await interaction.response.defer()

    engine = utils.setup_db(main_config)

    channel_id = main_config.get("DISCORD", "ORLANDO_CHANNEL_ID")
    channel = client.get_channel(int(channel_id))

    query = text("SELECT * FROM orlando_crimes WHERE date LIKE :date_hour ORDER BY date ASC")
    calls = pd.read_sql_query(query, engine, params={"date_hour": f"{date_hour}%"})
    
    fieldCount = 0
    page = 1
    color = discord.Color.blue()
    title = "ALL ORLANDO PD ACTIVE CALLS WITHIN PAST HOUR"

    embed = discord.Embed(title=title, color=color)
    for _, call in calls.iterrows():
        fieldCount += 1
        if (fieldCount >= 25):
            page += 1
            await channel.send(embed=embed)
            embed = discord.Embed(title=title, color=color)
            fieldCount = 0
            
        embed.add_field(name=call['description'], value=f"Date: {call['date']}\nAddress: {call['location']}", inline=False)

    await channel.send(embed=embed)
    await orlando_hourly_heatmap(calls, channel, main_config)

    if interaction:
        await interaction.followup.send("Hour report sent.", ephemeral=True)
