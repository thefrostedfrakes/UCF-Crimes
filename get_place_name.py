'''
UCF Crimes: get_place_name.py
Written by Ethan Frakes

Sends request to Google Places API for all place markers within 100 meters
of address coordinates; finds closest that is not a road or transit station.
'''

import pandas as pd
import requests
import json
from math import radians, sin, cos, sqrt, atan2
from get_lat_lng import get_lat_lng_from_address

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
            lat, lng = get_lat_lng_from_address(row["address"], GMAPS_API_KEY)
            if place_name := get_place_name(lat, lng, GMAPS_API_KEY):
                crimes.at[idx, "place"] = f"near {place_name}"
                print(place_name)

    crimes.to_csv('crimes.csv')
