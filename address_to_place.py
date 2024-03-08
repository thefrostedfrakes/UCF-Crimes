'''
Returns title given address

Maverick Reynolds
UCF Crimes

'''

import re
import editdistance
import json
from get_place_name import get_place_name
from titlize import titlize


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
