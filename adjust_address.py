'''

UCF Crimes
Maverick Reynolds
03.30.2023
adjust_address.py

'''

import re
import json
import editdistance
from Title import gen_title

def expand_address(raw_addr):
    raw_addr = ' ' + raw_addr + ' '
    raw_addr = re.sub('\.', '', raw_addr)   # Remove periods

    presubs = {
        ' W ': ' WEST ',
        ' E ': ' EAST ',
        ' N ': ' NORTH ',
        ' S ': ' SOUTH ',
        'BLD' : 'BLVD',
        ' ?(?:and|\/) ?': ' & '     # Change intersection of streets to &
    }

    for key, value in presubs.items():
        raw_addr = re.sub(key, value, raw_addr, flags=re.IGNORECASE)

    return raw_addr.strip()

# Will work despite differing word positions and typo errors
# Needs to be robust string matching function
def replace_address(expanded_addr):
    TYPO_TOLERANCE = 1

    expanded_addr = expand_address(expanded_addr)
    txt_tokens = expanded_addr.split()

    with open('locations.json') as f:
        locs = json.load(f)

        # Do this with every key
        for key in locs.keys():
            key_tokens = key.split()

            # Assume true until proven false
            is_match = True

            # If numerical start, make sure it matches exactly
            if re.match('\d+', txt_tokens[0]) and re.match('\d+', key_tokens[0]) and txt_tokens[0] != key_tokens[0]:
                is_match = False
                continue

            # Go through each token in key
            for key_token in key_tokens:
                token_distances = [editdistance.eval(key_token, txt_token) for txt_token in txt_tokens]
                if min(token_distances) > TYPO_TOLERANCE:
                    is_match = False
                    break

                # if key_token not in txt_tokens:
                #     is_match = False
                #     break

            # If all tokens match, locations is found
            if is_match:
                return locs[key]
        
        # Otherwise return original
        return gen_title(expanded_addr)