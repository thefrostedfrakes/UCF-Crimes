'''

UCF Crimes: image.py
Written by Jack Sweeney, Ethan Frakes

'''

import staticmaps
from PIL import Image, ImageDraw
import pandas as pd
import folium
from folium.plugins import HeatMap
import io
import discord
import math

def generate_image(crime: pd.Series) -> None:
    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    lat = crime["lat"]
    lng = crime["lng"]
    loc = staticmaps.create_latlng(lat, lng)
    context.add_object(staticmaps.Marker(loc, color=staticmaps.RED, size=12))

    # render anti-aliased png (this only works if pycairo is installed)
    image = context.render_cairo(380, 380)
    image.write_to_png("case.png")

    # render anti-aliased png (this only works if pycairo is installed)
    context.set_zoom(18)
    image = context.render_cairo(1080, 1080)
    image.write_to_png("casez.png")
    
    im1 = Image.open('casez.png')
    im2 = Image.open('case.png')
    im1.paste(im2, (700, 700))
    draw = ImageDraw.Draw(im1)
    draw.line((700, 700, 700, 1080), fill=(0, 0, 0), width=10)
    draw.line((696, 700, 1080, 700), fill=(0, 0, 0), width=10)
    im1.save('caseout.png', quality=100)

async def generate_heatmap(interaction: discord.Interaction, command_arg: str) -> None:
    await interaction.response.defer()
    await interaction.followup.send("Generating Heatmap... This May Take a Moment...")
    
    crimes = pd.read_csv('crimes.csv')
    
    if command_arg.title().startswith('Main'):
        coords = [28.60, -81.20]
    elif command_arg.title().startswith('Downtown'):
        coords = [28.55, -81.39]
    elif command_arg.title().startswith('Rosen'):
        coords = [28.43, -81.44]
    else:
        return await interaction.followup.edit("Please choose from one of these campuses: Main, Downtown, or Rosen.")

    m = folium.Map(location=coords, zoom_start=15)
    heat_map_data = []

    for row, crime in crimes.iterrows():
        if "4000 CENTRAL FLORIDA BLVD" not in crime["place"]:
            if not math.isnan(crime["lat"]) and not math.isnan(crime["lng"]):
                lat = float(crime["lat"])
                lng = float(crime["lng"])

                heat_map_data.append([lat, lng, 0.3])

    HeatMap(heat_map_data).add_to(m)
    img_data = m._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.crop()
    img.save('heatmap.png')

    await interaction.followup.send(file=discord.File("./heatmap.png"))