import json
import googlemaps
import folium
from folium.plugins import HeatMap
from PIL import Image
import io
import discord

async def send_heatmap(message, API_key: str) -> None:
    with open('crimes.json', 'r') as f:
        crimes = json.load(f)

    gmaps_key = googlemaps.Client(key=API_key)
    m = folium.Map(location=[28.6, -81.2], zoom_start=15)

    for key, crime in crimes.items():
        address = f'{crime["Location"].replace("/", "")} Orlando FL, US.'
        
        g = gmaps_key.geocode(address)
        lat = g[0]["geometry"]["location"]["lat"]
        long = g[0]["geometry"]["location"]["lng"]

        HeatMap([[lat, long, 0.3]]).add_to(m)

    img_data = m._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.crop()
    img.save('heatmap.png')

    await message.channel.send(file=discord.File("./heatmap.png"))
        