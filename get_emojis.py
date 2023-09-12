'''
function to get emojis from a string
Uses the emojis.json file to get emojis
Will not return duplicates

Maverick Reynolds
08.13.2023

'''

import re
import json

# Because emojis are fun
def get_emojis(title: str) -> str:
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

