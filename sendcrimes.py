'''

UCF Crimes: sendcrimes.py
Written by Ethan Frakes
and Maverick Reynolds

'''

import json
import pandas as pd
from typing import Optional
import discord
from discord.ext import commands
from datetime import datetime
from image import generate_image
from loadcrimes import is_valid_date
from titlize import titlize
from get_emojis import get_emojis
import gpt_expand
from sqlalchemy.engine.base import Engine
from discord import TextChannel

# Check if the channel is the permitted bot channel. Returns a message to user asking to use channel if false.
async def is_channel(interaction: discord.Interaction, client: commands.Bot, channel_id: str) -> bool:
    channel = client.get_channel(int(channel_id))

    if interaction.channel == channel:
        return True
    
    await interaction.response.send_message(f"Please post in the {channel.mention} channel to use this command!",
                                            ephemeral=True)
    return False

# Wrapper for formatting Discord embed containing queried crime info to send to channel.
async def crime_sender(channel: discord.TextChannel, crime: pd.Series) -> None:
    USE_GPT = False # Need key as well

    generate_image(crime)

    # Reformat dates and times
    report_date_time = datetime.strptime(crime["report_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["start_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["end_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')

    # Format title
    case_title = crime["title"]
    # Get emojis
    case_emojis = get_emojis(case_title)
    # Use language model AFTER formatting if enabled and AFTER emojis are retrieved
    if USE_GPT:
        case_title = gpt_expand.gpt_title_expand(case_title, provide_examples=True)
    # Append emojis to title
    case_title += case_emojis

    place = crime["place"] # replace_address already called in loadcrimes.py
    
    # Compose message
    description = f"Occurred at {titlize(crime['campus'])}, {place} \n" \
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
    if is_valid_date(command_arg):
        try:
            date_str = datetime.strptime(command_arg, "%m/%d/%y").strftime("%A, %B %d, %Y")
            command_arg = datetime.strptime(command_arg, "%m/%d/%y").strftime("%Y-%m-%d")
        except ValueError:
            date_str = datetime.strptime(command_arg, "%m/%d/%Y").strftime("%A, %B %d, %Y")
            command_arg = datetime.strptime(command_arg, "%m/%d/%Y").strftime("%Y-%m-%d")

        # Respond to interaction if the command was triggered by user. If not, then the command was
        # executed automatically for daily crime listing.
        if interaction is not None:
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

    elif place_name := next(place for place in locations.values() if place.lower() == command_arg.lower()):
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

# Opens crime database and searches for all crimes that match queried date, crime title, disposition,
# address, or place.
async def crime_send_csv(interaction: Optional[discord.Interaction], 
                        client: commands.Bot, 
                        command_arg: str, 
                        channel: TextChannel,
                        ) -> None:

    # Read crimes csv file loaded by crime_load()
    crimes = pd.read_csv('crimes.csv', index_col=0)
    
    # Open necessary json files.
    with open('locations.json', 'r') as f:
        locations = json.load(f)

    with open('crime_list.json', 'r') as f:
        crime_list = json.load(f)

    with open('status_list.json', 'r') as f:
        status_list = json.load(f)

    # Check if command argument is a valid date. If so, the dataframe key is set to report date/time,
    # and date strings are reformatted to match CSV formatting.
    if is_valid_date(command_arg):
        # Reformat datetime strings for both M/D/YY & M/D/YYYY
        try:
            date_str = datetime.strptime(command_arg, "%m/%d/%y").strftime("%A, %B %d, %Y")
            command_arg = datetime.strptime(command_arg, "%m/%d/%y").strftime("%Y-%m-%dT%H:%M:%SZ")

        except ValueError:
            date_str = datetime.strptime(command_arg, "%m/%d/%Y").strftime("%A, %B %d, %Y")
            command_arg = datetime.strptime(command_arg, "%m/%d/%Y").strftime("%Y-%m-%dT%H:%M:%SZ")

        df_key = "report_dt"
        
        # Respond to interaction if the command was triggered by user. If not, then the command was
        # executed automatically for daily crime listing.
        if interaction is not None:
            await interaction.response.send_message(f"Reported Crimes for {date_str}")
        else:
            await channel.send(f"Reported Crimes for {date_str}")

    # If command argument is a crime title or disposition, dataframe key is set to either title or
    # disposition accordingly.
    elif crime_list.get(command_arg.upper()) is not None:
        df_key = "title"
        await interaction.response.send_message(f"Reported Crimes for {command_arg.title()}")

    elif status_list.get(command_arg.upper()) is not None:
        df_key = "disposition"
        await interaction.response.send_message(f"Reported Crimes with status {command_arg.title()}")

    # If not any of the above, then argument is either place/address or invalid. Locations dict key/vals
    # are searched to find a match.
    else:
        found_addr = False
        for key, val in locations.items():
            if val.lower() == command_arg.lower():
                df_key = "place"
                found_addr = True

            elif key.lower() == command_arg.lower():
                df_key = "address"
                found_addr = True

        # If not match found, function is returned with invalid argument message (private to user).
        if not found_addr:
            return await interaction.response.send_message("Please search for a crime by type, valid date, or valid location.",
                                                           ephemeral=True)
        
        # Interaction is responded with titilized command argument.
        else:
            await interaction.response.send_message(f"Reported Crimes at {titlize(command_arg.upper())}")
 
    # Crimes are searched in dataframe to find query matches. Resulting matches list is converted to
    # dataframe.
    if df_key == "report_dt":
        crime_date = pd.to_datetime(crimes[df_key])
        command_arg = datetime.strptime(command_arg, "%Y-%m-%dT%H:%M:%SZ")

        query_matches = crimes[crime_date.dt.date == command_arg.date()]

    elif df_key == "title" or df_key == "disposition":    
        query_matches = crimes.loc[crimes[df_key] == command_arg.upper()]

    elif df_key == "place" or df_key == "address":
        query_matches = crimes.loc[crimes[df_key].str.lower() == command_arg.lower()]

    query_matches = pd.DataFrame(query_matches, columns=crimes.columns)
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

async def crime_send(interaction: Optional[discord.Interaction], 
                    client: commands.Bot, 
                    command_arg: str, 
                    channel_id: str, 
                    engine: Engine | None,
                    ) -> None:
    # Check if command was sent to bot channel.
    if interaction is not None and not await is_channel(interaction, client, channel_id):
        return

    # Get bot channel from id to send to channel. Sent after interaction response.
    channel = client.get_channel(int(channel_id))

    if engine:
        await crime_send_sql(interaction, client, command_arg, channel, engine)
    else:
        await crime_send_csv(interaction, client, command_arg, channel)
    

# Locations json is listed as Discord embed pages.
async def list_locations(interaction: discord.Interaction, client: commands.Bot, channel_id: str) -> None:
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
        if (fieldCount > 25):
            page += 1
            embeds.append(embed)
            embed = discord.Embed(title="All Locations in Database (Page " + str(page) + "):", color=discord.Color.blue())
            fieldCount = 0
            
        embed.add_field(name=val, value=key, inline=False)

    embeds.append(embed)
    await interaction.response.send_message(embeds=embeds)

# Crimes json is listed as Discord embed pages.
async def list_crimes(interaction: discord.Interaction, client: commands.Bot, channel_id: str) -> None:
    if not await is_channel(interaction, client, channel_id):
        return
    
    await interaction.response.defer()
    with open('crime_list.json', 'r') as f:
        crime_list = json.load(f)
        
    fieldCount = 0
    page = 1
    embed = discord.Embed(title="All Crime Names in Database (Page " + str(page) + "):", color=discord.Color.blue())
    for key, value in crime_list.items():
        fieldCount += 1
        if (fieldCount > 25):
            page += 1
            await interaction.followup.send(embed=embed)
            embed = discord.Embed(title="All Crime Names in Database (Page " + str(page) + "):", color=discord.Color.blue())
            fieldCount = 0
            
        embed.add_field(name=key, value=f"Number of crimes in database: {value}", inline=False)

    await interaction.followup.send(embed=embed)
