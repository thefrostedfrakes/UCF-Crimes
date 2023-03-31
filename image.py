'''

UCF Crimes: image.py
Written by Jack Sweeney

'''

import googlemaps
import staticmaps
from PIL import Image, ImageDraw, ImageFilter

def generate_image(crime, API_key):
    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)
#
    gmaps_key = googlemaps.Client(key=API_key)
    g = gmaps_key.geocode(f'{crime["Location"].replace("/", "")} Orlando FL, US.')
    lat = g[0]["geometry"]["location"]["lat"]
    long = g[0]["geometry"]["location"]["lng"]
    loc = staticmaps.create_latlng(lat, long)
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