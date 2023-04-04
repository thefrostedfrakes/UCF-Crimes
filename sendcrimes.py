'''

UCF Crimes: sendcrimes.py
Written by Ethan Frakes
and Maverick Reynolds

'''

import json
import discord
from datetime import datetime
from image import generate_image
from loadcrimes import is_valid_date
import string_adjustments as stradj

# Opens the json and sends all of the reported crimes from the previous day to the test
# discord server.
async def crime_send(client, command_arg, channel_id, GMaps_Key):
    channel = client.get_channel(int(channel_id))

    with open('crimes.json', 'r') as f:
        crimes = json.load(f)
    
    with open('locations.json', 'r') as f:
        locations = json.load(f)

    if is_valid_date(command_arg):
        date_str = datetime.strptime(command_arg, "%m/%d/%y").strftime("%A, %B %d, %Y")
        dict_key = "Report Date"
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
 
    crimeFlag = False
    for i, crime in enumerate(crimes["Crimes"]):
        if crime[dict_key] == command_arg:
            crimeFlag = True
            generate_image(crime, GMaps_Key)

            # Reformat dates and times
            report_time = datetime.strptime(crime["Report Time"], '%H:%M').strftime('%I:%M %p')
            start_time = datetime.strptime(crime["Start Time"], '%H:%M').strftime('%I:%M %p')
            end_time = datetime.strptime(crime["End Time"], '%H:%M').strftime('%I:%M %p')
            end_date = datetime.strptime(crime["End Date"], '%m/%d/%Y').strftime('%m/%d/%y')

            # Format title
            case_title = stradj.case_title_format(crime["Crime"])
            # Attach emojis for front end display
            case_title = stradj.attach_emojis(case_title)
            
            # Compose message
            description = f"""Occurred at {stradj.gen_title(crime['Campus'])}, {crime['Location']}
Case: {crime['Case #']}
Reported on {crime['Report Date']} {report_time}
Between {crime['Start Date']} {start_time} - {end_date} {end_time}
Status: {crime['Disposition'].title()}"""

            embed = discord.Embed(
                title=case_title,
                description=description,
                    
                color = discord.Color.red()
            ).set_image(url='attachment://caseout.png')

            await channel.send(embed=embed, file=discord.File('caseout.png'))
    
    if (crimeFlag == False):
            await channel.send("No reported crimes.")

async def list_locations(message):
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