'''
An easy way to look at what is happening with the case locations
'''

import json
import string_adjustments as stradj
import re

ACCEPTABLES = [
    'MEMORY MALL',
    'B8 LOT',
    'ON CAMPUS',
    '14552 LAKE PRICE DR', # Random house somewhere
    'NON CAMPUS LOCATION',
    'ANDROMEDA LOOP',
    'LIBRA DRIVE',
    'UNIVERSITY BLVD',
    'GREEK PARK DR NORTH',
]

NEEDS_GMAPS = [
    '2418 COLONIAL DR EAST',
    '609 LIVINGSTON ST WEST',
    '4498 ALAFAYA TRAIL NORTH',
]

TYPOS = [
    '12805F PEGASUS DR',    # Make a script to fix this (or ask GPT)
    'ALFAYA TRAIL NORTH'
]

# ======================================== #

with open('crimes.json', 'r') as f:
    crimes = json.load(f)

unreplaced = []

for key, crime in crimes.items():
    reg_addr = crime['Location']
    expanded_addr = stradj.expand_address(reg_addr)
    disp_addr = stradj.replace_address(expanded_addr)

    if disp_addr.upper() == expanded_addr and not re.search('\&', disp_addr):
        unreplaced.append(expanded_addr)

    print(f'REG : {reg_addr}')
    print(f'EXP : {expanded_addr}')
    print(f'DISP: {disp_addr}')
    print()

print(f"\nUNREPLACED ADDRESSES:\n")
for addr in unreplaced:
    if addr in ACCEPTABLES or addr in NEEDS_GMAPS or addr in TYPOS:
        continue
    else:
        print(addr)