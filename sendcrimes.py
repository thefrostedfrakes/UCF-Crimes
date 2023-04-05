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

async def crime_sender(channel, key: str, crime: dict, GMaps_Key: str, crimeCount: int) -> int:
    generate_image(crime, GMaps_Key)

    # Reformat dates and times
    report_date_time = datetime.strptime(crime["Report Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["Start Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["End Date/Time"], '%m/%d/%Y %H:%M').strftime('%m/%d/%y %I:%M %p')

    # Format title
    case_title = stradj.case_title_format(crime["Crime"])
    # Attach emojis for front end display
    case_title = stradj.attach_emojis(case_title)
    
    # Compose message
    description = f"""Occurred at {stradj.gen_title(crime['Campus'])}, {crime['Location']}
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
        date_str = datetime.strptime(command_arg, "%m/%d/%y").strftime("%A, %B %d, %Y")
        dict_key = "Report Date/Time"
        command_arg = datetime.strptime(command_arg, "%m/%d/%y").strftime("%m/%d/%y")
        await channel.send("Reported Crimes for %s" % (date_str))

    else:
        locFlag = False
        for key, val in locations.items():
            if val == command_arg or key.lower().title() == command_arg or key == command_arg:
                dict_key = "Location"
                command_arg = val
                locFlag = True

        if not locFlag:
            await channel.send("Please specify a date, location, etc.")
            return
 
    crimeCount = 0
    for key, val in crimes.items():
        if val[dict_key] == command_arg:
            crimeCount = await crime_sender(channel, key, val, GMaps_Key, crimeCount)

        try:
            if datetime.strptime(val[dict_key], '%m/%d/%y %H:%M').strftime('%m/%d/%y') == command_arg:
                crimeCount = await crime_sender(channel, key, val, GMaps_Key, crimeCount)

        except ValueError: pass
    
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