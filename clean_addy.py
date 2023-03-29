'''

UCF Crimes: clean_addy.py
Written by Maverick Reynolds

'''

import re

def clean_address(txt):
    txt = ' ' + txt + ' '

    presubs = {
        ' W\.? ': ' WEST ',
        ' E\.? ': ' EAST ',
        ' N\.? ': ' NORTH ',
        ' S\.? ': ' SOUTH ',
        'BLD' : 'BLVD'
    }

    for key, value in presubs.items():
        txt = re.sub(key, value, txt)

    return txt.strip()