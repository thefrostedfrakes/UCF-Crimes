import json

# Modification to Jack's title_except function
def gen_title(str_upper: str):
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