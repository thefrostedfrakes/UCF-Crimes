'''
Function to get lat, lng from address using google geocoding API.

Maverick Reynolds
08.11.2023

'''

import requests

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
    'KROSSING': (28.6113891, -81.2113697)
}


def get_lat_lng_from_address(address, google_maps_api_key) -> tuple[float, float] | tuple[None, None]:
    '''
    Uses google geocoding endpoint to get lat, lng from address.
    Will prefer locations within box containing UCF and Downtown
    (Does not totally restrict results to this box).
    If address includes predetermined keyword(s), it will use given results
    '''

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

