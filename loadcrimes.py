'''

UCF Crimes: loadcrimes.py
Written by Ethan Frakes

'''

from PyPDF2 import PdfReader
import requests
from datetime import datetime, date
import json
import string_adjustments as stradj

# Returns if date string token passed is valid.
def is_valid_date(date_string: str) -> bool:
    # First is for mm/dd/yy and second is for mm/dd/yyyy
    valid_formats = ['%m/%d/%y', '%m/%d/%Y']
    for date_format in valid_formats:
        try:
            datetime.strptime(date_string, date_format)
            return True
        except ValueError:
            pass
    return False

# Returns if time string token passed is valid.
def is_valid_time_label(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False

# Tokenizes each crime into separate elements of a 2D string array, where each 1st dimension
# element is each crime and each 2nd dimension element is each space/newline delimited string.
def tokenizer(page) -> list:

    # Text extracted from page and split between spaces and newlines.
    crime_list = []
    text = page.extract_text()
    textToken = text.split()
    buffer_list = []
    valid_delimiters = ["Incident", "UNFOUNDED", "EXC", "ARREST", "INACTIVE", 
                        "CLOSED", "OPEN", "ACTIVE", "REPORT"]

    # For each string in the textToken, if the string is one of the valid delimiters above
    # (end of one crime and beginning of another), buffer list is added to the crime list.
    for elem in range(len(textToken)):
        for delimiter in valid_delimiters:
            if delimiter == "ARREST" and textToken[elem] == delimiter and textToken[elem+1] == "-":
                crime_list.append(buffer_list)
                buffer_list = []

            elif delimiter != "ARREST" and textToken[elem] == delimiter:
                crime_list.append(buffer_list)
                buffer_list = []
            
        buffer_list.append(textToken[elem])
    
    crime_list.append(buffer_list)
    return crime_list

# Parses each crime element by grouping unjoined tokens together that correspond to the same
# dictionary key.
def parser(crime_list: list) -> list:
    crime_list_len = len(crime_list)

    for i in range(crime_list_len):
        for j, elem in enumerate(crime_list[i]):
            if elem == "ARREST":
                crime_list[i][j] += " " + crime_list[i][j+1] + " " + crime_list[i][j+2]
                crime_list[i].remove(crime_list[i][j+1])
                crime_list[i].remove(crime_list[i][j+1])
            
            elif elem == "EXC":
                crime_list[i][j] += " " + crime_list[i][j+1] + " " + crime_list[i][j+2] + " " + crime_list[i][j+3]
                crime_list[i].remove(crime_list[i][j+1])
                crime_list[i].remove(crime_list[i][j+1])
                crime_list[i].remove(crime_list[i][j+1])

            elif is_valid_time_label(crime_list[i][j]):
                j += 1
                while j + 1 < len(crime_list[i]) and not is_valid_date(crime_list[i][j+1]) and not is_valid_time_label(crime_list[i][j+1]):
                    crime_list[i][j] += " " + crime_list[i][j+1]
                    crime_list[i].remove(crime_list[i][j+1])

        try:
            if is_valid_date(crime_list[i][4][-8:]):
                    crime_list[i].insert(5, crime_list[i][4][-8:])
                    crime_list[i][4] = crime_list[i][4][:-8].strip()
        except IndexError: pass

        if len(crime_list[i]) == 10 and is_valid_time_label(crime_list[i][-1]):
            crime_list[i].append("UNSPECIFIED CAMPUS")

        if len(crime_list[i]) == 11:
            # Replace address before pushing
            crime_list[i][7] = stradj.replace_address(crime_list[i][7])

            crime_list[i][2] += " " + crime_list[i][3]
            crime_list[i][5] += " " + crime_list[i][6]
            crime_list[i][8] += " " + crime_list[i][9]
            del crime_list[i][3]
            del crime_list[i][5]
            del crime_list[i][7]

    return crime_list

# Converts crimes list to a dictionary, then dumps to a json file.
def load_to_json(crime_list: list, command_str: str) -> None:
    keys = ["Disposition", "Case #", "Report Date/Time",
            "Crime", "Start Date/Time", "Location", 
            "End Date/Time", "Campus"]
    
    if command_str == '-loadcrimes':
        crimes_dict = {"Crimes":[]}

    elif command_str == '-addcrimes':
        with open('crimes.json', 'r') as f:
            crimes_dict = json.load(f)
    
    for crime in crime_list:
        if len(crime) == 8:
            crime_dict = {}
            for i, key in enumerate(keys):
                crime_dict[key] = crime[i]

            if command_str == '-loadcrimes':
                crimes_dict["Crimes"].append(crime_dict)
            elif command_str == '-addcrimes' and crime_dict not in crimes_dict["Crimes"]:
                crimes_dict["Crimes"].append(crime_dict)

    with open('crimes.json', 'w') as f:
        json.dump(crimes_dict, f, indent=4)

# Requests the url of the daily crime log, opens the file, calls PdfReader to read the pdf's
# contents, calls the tokenizer and parser, then adds the parsed list to a json.
def crime_load(command_str: str) -> None:
    pdf_filename = 'AllDailyCrimeLog.pdf'
    crime_url = 'https://police.ucf.edu/sites/default/files/logs/ALL%20DAILY%20crime%20log.pdf'

    # Requests the url of the crime log from UCF PD's website and writes the pdf to the local
    # machine as 'AllDailyCrimeLog.pdf'. Then opens a PdfReader instance to read the pdf.
    rsp = requests.get(crime_url, timeout=30)
    open(pdf_filename, 'wb').write(rsp.content)
    reader = PdfReader(pdf_filename)

    # Each page in the pdf is tokenized and parsed.
    crimes_list = []
    for i in range(len(reader.pages)):
        crime_list = tokenizer(reader.pages[i])
        crime_list = parser(crime_list)
        for crime in crime_list:
            crimes_list.append(crime)

    # Just to test each list element to ensure it was properly parsed.
    for crime in crimes_list:
        if len(crime) == 8: print("CORRECT FORMAT")
        print(crime, '\n')

    # load_to_json called to convert the list of crimes to a dictionary, then to a json file.
    load_to_json(crimes_list, command_str)

# Simple function to copy current crimes.json file to backups folder with added date.
def backup_crimes() -> None:
    with open('crimes.json', 'r') as f:
        crime_dict = json.load(f)

    today = date.today().strftime("%m-%d-%Y")
    backup_json_name = "crimes-" + today + ".json"
    
    with open(('./backups/' + backup_json_name), 'w') as f:
        json.dump(crime_dict, f, indent=4)