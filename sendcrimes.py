'''

UCF Crimes: sendcrimes.py
Written by Ethan Frakes

'''

import json
import discord
from datetime import datetime
from image import generate_image
from loadcrimes import is_valid_date

# Opens the json and sends all of the reported crimes from the previous day to the test
# discord server.
async def crime_send(client, command_arg, config):
    channel = client.get_channel(config["Crime Channel ID"])

    with open('crimes.json', 'r') as f:
        crimes = json.load(f)
    
    with open('locations.json', 'r') as f:
        locations = json.load(f)

    if (is_valid_date(command_arg)):
        date_str = datetime.strptime(command_arg, "%m/%d/%y").strftime("%A, %B %d, %Y")
        dict_key = "Report Date"
        command_arg = datetime.strptime(command_arg, "%m/%d/%y").strftime("%m/%d/%y")
        await channel.send("Reported Crimes for %s" % (date_str))

    else:
        locFlag = False
        for key, val in locations.items():
            if val == command_arg or key.lower().title() == command_arg or key == command_arg:
                dict_key = "Location"
                command_arg = key
                locFlag = True

        if (locFlag == False):
            await channel.send("Please specify a date, location, etc!")
            return
 
    crimeFlag = False
    for i, crime in enumerate(crimes["Crimes"]):
        if crime[dict_key] == command_arg:
            crimeFlag = True
            generate_image(crime, config["GMaps API Key"])
        
            try:
                location = locations[crime["Location"]]
            except KeyError:
                location = crime["Location"].lower().title()

            report_time = datetime.strptime(crime["Report Time"], '%H:%M').strftime('%I:%M %p')
            start_time = datetime.strptime(crime["Start Time"], '%H:%M').strftime('%I:%M %p')
            end_time = datetime.strptime(crime["End Time"], '%H:%M').strftime('%I:%M %p')
            
            embed = discord.Embed(
                title = crime["Crime"],
                description = "Occurred at " + crime["Campus"] + ", " + location + "\n"
                    + "Case # " + crime["Case #"] + "\n"
                    + "Reported on " + crime["Report Date"] + " " + report_time + "\n"
                    + "Between times " + crime["Start Date"] + " " + start_time
                    + " - " + crime["End Date"] + " " + end_time + "\n"
                    + "Status is " + crime["Disposition"] + "\n",
                    
                color = discord.Color.red()
            ).set_image(url='attachment://caseout.png')

            await channel.send(embed=embed, file=discord.File('caseout.png'))
    
    if (crimeFlag == False):
            await channel.send("No reported crimes.")

async def list_locations(message):
    with open ('locations.json', 'r') as f:
        locations = json.load(f)

    embed = discord.Embed(title="All Locations in Database:", color=discord.Color.blue())
    for key, val in locations.items():
        embed.add_field(name=val, value=key, inline=False)

    await message.channel.send(embed=embed)