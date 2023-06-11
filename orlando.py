'''

UCF Crimes: orlando.py

An extension to UCF Crimes that allows for quick query of all currently active calls posted by
Orlando PD and heatmap generation of all calls.

Written by Ethan Frakes

'''

import requests
from bs4 import BeautifulSoup
import json
import xmltodict
import discord
import googlemaps
import folium
from folium.plugins import HeatMap
from PIL import Image
import io

# Load XML file from Orlando PD website with BeautifulSoup and parse the file to a JSON file.
def load_orlando_active() -> None:
    active_req = requests.get('https://www1.cityoforlando.net/opd/activecalls/activecadpolice.xml')

    soup = BeautifulSoup(active_req.content, "lxml-xml")

    active_dict = xmltodict.parse(str(soup))

    try:
        with open('orlando.json', 'r') as f:
            crimes_dict = json.load(f)
            
        for crime in active_dict["CALLS"]["CALL"]:
            if crime not in crimes_dict["CALLS"]["CALL"]:
                crimes_dict["CALLS"]["CALL"].insert(0, crime)

    except FileNotFoundError:
        crimes_dict = active_dict

    with open('orlando.json', 'w') as f:
        json.dump(crimes_dict, f, indent=4)

    print("orlando.json refreshed.")
    
# Send contents of JSON and heatmap to UCF Crimes Discord bot channel.
async def send_orlando_active(client, channel_id: str, API_key: str) -> None:
    load_orlando_active()

    channel = client.get_channel(int(channel_id))

    with open('orlando.json', 'r') as f:
        active_dict = json.load(f)

    fieldCount = 0
    embed = discord.Embed(title="All Active Crimes In Orlando", color=discord.Color.blue())

    for call in active_dict["CALLS"]["CALL"]:
        fieldCount += 1
        if (fieldCount > 25):
            await channel.send(embed=embed)
            embed = discord.Embed(title="All Active Crimes In Orlando", color=discord.Color.blue())
            fieldCount = 0

        embed.add_field(name=call['DESC'].title(), value=f"""ID: {call['@incident']}
DATE: {call['DATE']}
LOCATION: {call['LOCATION']} - {call['DISTRICT']} District""", inline=False)

    await channel.send(embed=embed)
    await channel.send("Generating Active Crime Heatmap... This May Take a Moment...")

    gmaps_key = googlemaps.Client(key=API_key)
    m = folium.Map(location=[28.5384, -81.3789], zoom_start=14)
    heat_map_data = []

    for call in active_dict["CALLS"]["CALL"]:
        address = f'{call["LOCATION"].replace("/", "")} Orlando FL, US.'
    
        g = gmaps_key.geocode(address)
        lat = g[0]["geometry"]["location"]["lat"]
        long = g[0]["geometry"]["location"]["lng"]

        heat_map_data.append([lat, long, 0.6])

    HeatMap(heat_map_data).add_to(m)
    img_data = m._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.crop()
    img.save('orlando_heatmap.png')

    await channel.send(file=discord.File("./orlando_heatmap.png"))

def check_orlando_size() -> None:
    with open('orlando.json', 'r') as f:
        crime_dict = json.load(f)

    print("Current number of entries in orlando.json:", len(crime_dict["CALLS"]["CALL"]))

if __name__ == '__main__':
    check_orlando_size()