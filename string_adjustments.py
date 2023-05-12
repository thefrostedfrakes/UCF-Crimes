'''
Functions to adjust the title, location, and other fields for front/back end

Maverick Reynolds
UCF Crimes

'''

import re
import editdistance
import json

TYPO_TOLERANCE = 1


# Sometimes spacing isn't quite correct, or words spelled differently
def case_title_format(case_title: str) -> str:
    case_title = case_title.replace('PETIT', 'PETTY')   # Change spelling
    case_title = re.sub(' ?, ?', ', ', case_title)      # Ensure commas have spaces following
    case_title = re.sub('  ', ' ', case_title)          # Remove double spaces
    return case_title


# Because emojis are fun
# Reads from emojis.json (supports regex!)
def attach_emojis(formatted_case_title: str) -> str:
    with open('emojis.json', 'r', encoding="utf-8") as f:
        emojis: dict = json.load(f)

    emoji_suffix = ''
    for emoji_txt in emojis.keys():
        if re.search(emoji_txt, formatted_case_title.lower()):
            emoji_suffix += f' {emojis[emoji_txt]}' # Must use += and not .join() to preserve unicode

    return formatted_case_title + emoji_suffix


# Returns title function applied to string with exceptions found in title_exceptions.json
def gen_title(str_upper: str) -> str:
    with open('title_exceptions.json') as f:
        exceptions: dict = json.load(f)

    title = ''
    for token in str_upper.split():
        if token in exceptions.keys():
            title += exceptions[token]
        else:
            title += token.title()
        title += ' '

    return title.strip()


# Takes raw address and primes it for comparison
def expand_address(address: str) -> str:
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

    return address.strip()


# Takes address and compares it to the locations.json file
# Robust against varying word positions and typo errors
# Returns gen_title() of address if no match is found
def replace_address(addr: str) -> str:
    expanded_addr = expand_address(addr)
    txt_tokens = expanded_addr.split()

    with open('locations.json') as f:
        locs: dict[str] = json.load(f)

    # Do this with every key
    for key in locs.keys():
        key_tokens = key.split()
        is_match = True

        # If numerical start, make sure it matches exactly
        if re.match('\d+', txt_tokens[0]) and re.match('\d+', key_tokens[0]) and txt_tokens[0] != key_tokens[0]:
            is_match = False
            continue

        # Go through each token in key
        for key_token in key_tokens:
            token_distances = [editdistance.eval(key_token, txt_token) for txt_token in txt_tokens]
            # Fail if no token is within tokerance for all key tokens
            if min(token_distances) > TYPO_TOLERANCE:
                is_match = False
                break

        # If all tokens are within tolerance, locations is found
        if is_match:
            return key
    
    # Otherwise return original
    return expanded_addr


