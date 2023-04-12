import json
import pandas as pd
import googlemaps
import folium
from folium.plugins import HeatMap
from PIL import Image
import io
import discord

async def send_heatmap(message, API_key: str) -> None:
    with open('crimes.json', 'r') as f:
        crimes = json.load(f)

    locations = pd.DataFrame(columns=["Lat", "Lon"])
    gmaps_key = googlemaps.Client(key=API_key)

    for key, crime in crimes.items():
        address = f'{crime["Location"].replace("/", "")} Orlando FL, US.'
        
        g = gmaps_key.geocode(address)
        lat = g[0]["geometry"]["location"]["lat"]
        long = g[0]["geometry"]["location"]["lng"]

        locations = locations.append({'Lat':lat, 'Lon':long}, ignore_index=True)

    m = folium.Map(location=[28.6, -81.2], zoom_start=15)
    for i, row in locations.iterrows():
        HeatMap([[row['Lat'], row['Lon'], 0.3]]).add_to(m)

    print(locations)

    img_data = m._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.crop()
    img.save('heatmap.png')

    await message.channel.send(file=discord.File("./heatmap.png"))
        