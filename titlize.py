'''
Working with the titles of the cases

Maverick Reynolds
08.13.2023

'''

import json

# Returns title function applied to string with exceptions found in title_exceptions.json
def titlize(title: str) -> str:
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

