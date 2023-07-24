'''

UCF Crimes: sendcrimes.py
Written by Ethan Frakes
and Maverick Reynolds

'''

import json
import discord
from discord.ext import commands
from datetime import datetime
from image import generate_image
from loadcrimes import is_valid_date
import string_adjustments as stradj
import gpt_expand

async def crime_sender(channel, key: str, crime: dict, GMaps_Key: str, crimeCount: int, locations: dict) -> int:
    USE_GPT = True # Need key as well

    generate_image(crime, GMaps_Key)

    # Reformat dates and times
    report_date_time = datetime.strptime(crime["Report Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["Start Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["End Date/Time"], '%m/%d/%Y %H:%M').strftime('%m/%d/%y %I:%M %p')

    # Format title
    case_title = stradj.case_title_format(crime["Crime"])
    # Get emojis
    case_emojis = stradj.get_emojis(case_title)
    # Use language model AFTER formatting if enabled and AFTER emojis are retrieved
    if USE_GPT:
        case_title = gpt_expand.gpt_title_expand(case_title, provide_examples=True)
    # Append emojis to title
    case_title += case_emojis

    location = crime["Location"] # replace_address already called in loadcrimes.py
    
    # Compose message
    description = f"""Occurred at {stradj.gen_title(crime['Campus'])}, {location}
Case: {key}
Reported on {report_date_time}
Between {start_date_time} - {end_date_time}
Status: {crime['Disposition'].title()}"""

    embed = discord.Embed(
        title=case_title,
        description=description,
            
        color = discord.Color.red()
    ).set_image(url='attachment://caseout.png')

    await channel.send(embed=embed, file=discord.File('caseout.png'))
    return crimeCount + 1

# Opens the json and sends all of the reported crimes from the previous day to the test
# discord server.
async def crime_send(client: commands.Bot, command_arg: str, channel_id: str, GMaps_Key: str) -> None:
    channel = client.get_channel(int(channel_id))

    with open('crimes.json', 'r') as f:
        crimes = json.load(f)
    
    with open('locations.json', 'r') as f:
        locations = json.load(f)

    if is_valid_date(command_arg):
        try:
            date_str = datetime.strptime(command_arg, "%m/%d/%y").strftime("%A, %B %d, %Y")

        except ValueError:
            date_str = datetime.strptime(command_arg, "%m/%d/%Y").strftime("%A, %B %d, %Y")
        dict_key = "Report Date/Time"
        command_arg = datetime.strptime(command_arg, "%m/%d/%y").strftime("%m/%d/%y")
        await channel.send("Reported Crimes for %s" % (date_str))

    else:
        address_list = []
        for key, val in locations.items():
            if val == command_arg or key.lower().title() == command_arg or key == command_arg:
                dict_key = "Location"
                address_list.append(key)

        if len(address_list) == 0:
            dict_key = "Crime"
 
    crimeCount = 0
    for key, crime in crimes.items():
        if dict_key == "Location":
            for address in address_list:
                if address in crime.get(dict_key):
                    crimeCount = await crime_sender(channel, key, crime, GMaps_Key, crimeCount, locations)

        elif dict_key == "Report Date/Time":
            if datetime.strptime(crime.get(dict_key), '%m/%d/%y %H:%M').strftime('%m/%d/%y') == command_arg:
                crimeCount = await crime_sender(channel, key, crime, GMaps_Key, crimeCount, locations)

        elif dict_key == "Crime":
            if crime.get(dict_key).lower() == command_arg.lower():
                crimeCount = await crime_sender(channel, key, crime, GMaps_Key, crimeCount, locations)
    
    if (crimeCount == 0):
        await channel.send("No reported crimes.")
    else:
        await channel.send(str(crimeCount) + " reported crimes.")

async def list_locations(message) -> None:
    with open('locations.json', 'r') as f:
        locations = json.load(f)

    fieldCount = 0
    page = 1
    embed = discord.Embed(title="All Locations in Database (Page " + str(page) + "):", color=discord.Color.blue())
    for key, val in locations.items():
        fieldCount += 1
        if (fieldCount > 25):
            page += 1
            await message.channel.send(embed=embed)
            embed = discord.Embed(title="All Locations in Database (Page " + str(page) + "):", color=discord.Color.blue())
            fieldCount = 0
            
        embed.add_field(name=val, value=key, inline=False)

    await message.channel.send(embed=embed)

async def list_crimes(message):
    with open('crimes.json', 'r') as f:
        crimes = json.load(f)

    crime_list = {}
    for key, crime in crimes.items():
        if crime["Crime"] not in crime_list.keys():
            crime_list[crime["Crime"]] = 1
        else:
            crime_list[crime["Crime"]] += 1
        
    fieldCount = 0
    page = 1
    embed = discord.Embed(title="All Crime Names in Database (Page " + str(page) + "):", color=discord.Color.blue())
    for key, value in crime_list.items():
        fieldCount += 1
        if (fieldCount > 25):
            page += 1
            await message.channel.send(embed=embed)
            embed = discord.Embed(title="All Crime Names in Database (Page " + str(page) + "):", color=discord.Color.blue())
            fieldCount = 0
            
        embed.add_field(name=key, value=f"Number of crimes in database: {value}", inline=False)

    await message.channel.send(embed=embed)

async def help_menu(message):
    embed = discord.Embed(
        title = "UCF CRIMES HELP MENU",
        description = "Available commands:\n\n"
            + "-crimes (date, location, crime)\n"
            + "Provides user with all found crimes from their query command\n"
            + "Example: '-crimes 7/22/23' or '-crimes Garage A'\n\n"
            + "-locations\n"
            + "Gives a list of all available locations in the database\n",
        color = discord.Color.red()
    )

    message_embed = await message.channel.send(embed=embed)
