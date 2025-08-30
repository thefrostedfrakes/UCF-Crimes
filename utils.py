'''
UCF Crimes: utils.py
Various functions to assist with backend & discord bot functionality.
Written by Ethan Frakes and Maverick Reynolds

'''

import discord
import json
import re
import pandas as pd
import requests
import editdistance
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy import text
from configparser import ConfigParser

async def bot_help(interaction: discord.Interaction):
    '''
    Help command for discord bot with embed showing all possible commands.
    '''
    embed = discord.Embed(
        title = "UCF Crimes Help",
        description = "Available bot commands:\n\n"
            + "/crimes {MM/DD/YY} or {location} or {address} or {crime title} or {disposition} \n"
            + "   - View all crime reports searched with the given parameter. \n"
            + "   - Ex: /crimes 3/30/24 OR /crimes Nike 106 \n\n"
            + "/heatmap {main} or {downtown} or {rosen} \n"
            + "   - View heatmap of all crime reports in database within the area of the selected campus. \n"
            + "   - Ex: /crimes main \n\n"
            + "/locations \n"
            + "   - List all available locations and addresses available to query. \n\n"
            + "/ping \n"
            + "   - Test if bot is online by pinging.",
        color = discord.Color.red()
    )

    await interaction.response.send_message(embed=embed)

def setup_db(main_config: ConfigParser) -> Engine:
    '''
    Connect to the PostgreSQL database
    '''
    host = main_config.get('POSTGRESQL', 'host')
    database = main_config.get('POSTGRESQL', 'database')
    user = main_config.get('POSTGRESQL', 'user')
    password = main_config.get('POSTGRESQL', 'password')

    db_uri = f'postgresql://{user}:{password}@{host}/{database}'
    engine = create_engine(db_uri)

    return engine

def is_valid_date(date_string: str) -> bool:
    '''
    Returns if date string token passed is valid.
    '''
    # First is for mm/dd/yy and second is for mm/dd/yyyy
    valid_formats = ['%m/%d/%y', '%m/%d/%Y']
    for date_format in valid_formats:
        try:
            datetime.strptime(date_string, date_format)
            return True
        except ValueError:
            pass
    return False

def is_valid_time_label(time_str: str) -> bool:
    '''
    Returns if time string token passed is valid.
    '''
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False

def is_valid_case_id(case_id_str: str) -> bool:
    '''
    Checks if input string is or is not a case id.
    Used in tokenizer to make sure that delimiter is indeed the disposition and not word in crime title.
    '''
    id_patterns = [r'^\d{4}-\d{4}$', r'^\d{4}-[A-Za-z]{3}\d{2}$']
    for pattern in id_patterns:
        if re.match(pattern, case_id_str):
            return True
        
    return False

def titlize(title: str) -> str:
    '''
    Returns title function applied to string with exceptions found in title_exceptions.json
    '''
    with open('title_exceptions.json') as f:
        exceptions: dict = json.load(f)

    new_title = ''
    for token in title.split():
        if token in exceptions.keys():
            new_title += exceptions[token]
        else:
            new_title += token.title()
        new_title += ' '

    return new_title.strip()

def get_emojis(title: str) -> str:
    '''
    Because emojis are fun
    '''
    with open('emojis.json', 'r', encoding="utf-8") as f:
        emojis: dict = json.load(f)

    emojis_suffix = ''

    for emoji_txt in emojis.keys():
        if re.search(emoji_txt, title, re.IGNORECASE):
            # If a match, go through each emoji in the value and add it to the suffix
            for emoji in emojis[emoji_txt]:
                if emoji not in emojis_suffix:
                    # Must use += and not .join() to preserve unicode
                    emojis_suffix += f'{emoji}'

    return emojis_suffix

def better_geocoder(address: str, google_maps_api_key: str) -> tuple[float, float] | tuple[None, None]:
    '''
    Uses a lookup table with the addrerss in the database that has addres, plaxe name, lat, and long
    
    '''

    #address lookup right here
    address_query = f'SELECT * FROM address WHERE address = {address}}'
    #select * from addresses where addressname = @address
    address_result = connection.execute(text(address_query))

    #if the address is not found in the database then we can call the google decoder
    if address_query.rowcount == 0:
        lat_long_google = google_geocoder(address,google_maps_api_key)
        return lat_long_google
    else:
        print('pull from database')


        



def osm_geocoder(address: str, OSM_USER_AGENT: str) -> tuple[float, float] | tuple[None, None]:
    '''
    Uses OpenStreetMap’s Nominatim geocoder to get latitude and longitude from an address.
    It prefers locations within a bounding box (roughly covering UCF and Downtown).
    If the address includes predetermined keyword(s), it returns preset coordinates.
    '''

    BL_BOUND = (28.0, -82.0)  # (lat, lon) bottom-left
    TR_BOUND = (29.0, -80.9)  # (lat, lon) top-right
    KEY_PHRASES = {
        'B8': (28.5939606, -81.2014182),
        '36 PINE ST W': (28.5412345, -81.3797360),
        'ON CAMPUS': (28.6024367, -81.2000568),
        'PLAZA DR E': (28.6069698, -81.1967868),
        'PLAZA DR W': (28.6074074, -81.1980356),
        'GEMINI/SCORPIUS': (28.6018854, -81.1944728),
        'KINGS KNIGHT': (28.6104158, -81.2154757),
        'KROSSING': (28.6113891, -81.2113697),
        '410 TERRY AVE N': (28.537944, -81.386917)
    }

    # Return preset coordinates if a key phrase is found in the address
    for phrase in KEY_PHRASES:
        if phrase in address:
            return KEY_PHRASES[phrase]

    # Nominatim API endpoint
    endpoint = 'https://nominatim.openstreetmap.org/search'
    
    # Construct the viewbox.
    # Nominatim expects the viewbox as: left (min lon), top (max lat), right (max lon), bottom (min lat)
    viewbox = f"{BL_BOUND[1]},{TR_BOUND[0]},{TR_BOUND[1]},{BL_BOUND[0]}"

    params = {
        'q': address,
        'format': 'json',
        'limit': 1,
        'viewbox': viewbox,
        'bounded': 1
    }
    
    # Nominatim requires a valid User-Agent header
    headers = {
        'User-Agent': OSM_USER_AGENT
    }

    response = requests.get(endpoint, params=params, headers=headers)

    if response.status_code not in range(200, 299):
        return None, None

    data = response.json()
    if not data:
        return None, None

    try:
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
    except (KeyError, ValueError):
        return None, None

    return round(lat, 7), round(lon, 7)

def google_geocoder(address: str, google_maps_api_key: str) -> tuple[float, float] | tuple[None, None]:
    '''
    Uses Google geocoding endpoint to get lat, lng from address.
    Will prefer locations within box containing UCF and Downtown
    (Does not totally restrict results to this box).
    If address includes predetermined keyword(s), it will use given results
    '''

    BL_BOUND = (28.522318, -81.407249)
    TR_BOUND = (28.644500, -81.155722)
    KEY_PHRASES = {
        'B8': (28.5939606, -81.2014182),
        '36 PINE ST W': (28.5412345, -81.3797360),
        'ON CAMPUS': (28.6024367, -81.2000568),
        'PLAZA DR E':(28.6069698, -81.1967868),
        'PLAZA DR W': (28.6074074, -81.1980356),
        'GEMINI/SCORPIUS': (28.6018854, -81.1944728),
        'KINGS KNIGHT': (28.6104158, -81.2154757),
        'KROSSING': (28.6113891, -81.2113697),
        '410 TERRY AVE N': (28.537944, -81.386917)
    }

    endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': address,
        'key': google_maps_api_key,
        'bounds': f'{BL_BOUND[0]},{BL_BOUND[1]}|{TR_BOUND[0]},{TR_BOUND[1]}'
    }

    # Use key phrases if they are in address
    for phrase in KEY_PHRASES.keys():
        if phrase in address:
            return KEY_PHRASES[phrase]

    result = requests.get(endpoint, params=params)

    if result.status_code not in range(200, 299) or result.json()['status'] == 'ZERO_RESULTS':
        # Request failed or no results found
        return None, None
    else:
        # Return lat, lng
        lat, lng = result.json()['results'][0]['geometry']['location'].values()
        return round(lat, 7), round(lng, 7)

def haversine_form(latitude_center: float, longitude_center: float, latitude_place: float, longitude_place: float) -> float:
    lat1 = radians(latitude_center)
    lon1 = radians(longitude_center)
    lat2 = radians(latitude_place)
    lon2 = radians(longitude_place)

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = 6371 * c  # Radius of the Earth in kilometers

    return distance

def get_place_name(lat: float, lng: float, GMAPS_API_KEY: str, radius: int=100) -> str | None:
    '''
    Sends request to Google Places API for all place markers within 100 meters
    of address coordinates; finds closest that is not a road or transit station.
    '''
    
    url = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius={radius}&key={GMAPS_API_KEY}'

    r = requests.get(url)
    # print(r.text)
    json_r = json.loads(r.text)

    places_dict = {}

    for result in json_r["results"]:
        if "route" not in result["types"] and "transit_station" not in result["types"]:
            lat_place = result["geometry"]["location"]["lat"]
            lon_place = result["geometry"]["location"]["lng"]

            distance = haversine_form(lat, lng, lat_place, lon_place)
            # print(f"Distance for {result['name']} = {distance}")

            places_dict[distance] = result['name']

    if len(places_dict.keys()) > 0:
        return places_dict[min(places_dict.keys())]
    else:
        return None

def change_all_addresses(GMAPS_API_KEY: str) -> None:
    crimes = pd.read_csv('crimes.csv', index_col=0)

    for idx, row in crimes.iterrows():
        if row["address"] == row["place"].upper():
            lat, lng = osm_geocoder(row["address"], GMAPS_API_KEY)
            if place_name := get_place_name(lat, lng, GMAPS_API_KEY):
                crimes.at[idx, "place"] = f"near {place_name}"
                print(place_name)

    crimes.to_csv('crimes.csv')

def address_to_place(address: str, 
                     lat: float, lng: float, 
                     GMAPS_API_KEY: str, 
                     typo_tolerance=1) -> str | None:
    '''
    Takes address and compares it to the locations.json file
    Robust against varying word positions and typo errors
    If selenium scraping is enabled and a path is given, the function will use that as a backup
    Otherwise, returns the titled version of the address
    '''

    # Make proper substitutions to change cardinal directions and other syntax
    address = ' ' + address + ' '
    address = re.sub('\.', '', address)   # Remove periods

    subs = {
        ' W ': ' WEST ',
        ' E ': ' EAST ',
        ' N ': ' NORTH ',
        ' S ': ' SOUTH ',
        'BLD' : 'BLVD',
        ' ?(?: and |\/) ?': ' & '     # Change intersection of streets to &
    }
    for key, value in subs.items():
        address = re.sub(key, value, address, flags=re.IGNORECASE)
    address = address.strip()

    # Tokenize address
    txt_tokens = address.split()

    # Start by looking through the address
    with open('locations.json') as f:
        locations: dict[str] = json.load(f)

    # Do this with every key
    for key in locations.keys():
        key_tokens = key.split()
        is_match = True

        # If numerical start, make sure it matches exactly
        if re.match('\d', txt_tokens[0]) and re.match('\d', key_tokens[0]) and txt_tokens[0] != key_tokens[0]:
            is_match = False
            continue

        # Go through each token in key
        for key_token in key_tokens:
            token_distances = [editdistance.eval(key_token, txt_token) for txt_token in txt_tokens]
            # Fail if no token is within tokerance for all key tokens
            if min(token_distances) > typo_tolerance:
                is_match = False
                break

        # If all tokens are within tolerance, locations is found
        if is_match:
            return locations[key]
    
    if (place_name := get_place_name(lat, lng, GMAPS_API_KEY)):
            print(place_name)
            return f"near {place_name}"
    
    return titlize(address)
