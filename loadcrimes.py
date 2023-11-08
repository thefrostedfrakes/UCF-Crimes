'''

UCF Crimes: loadcrimes.py
Written by Ethan Frakes

'''

from PyPDF2 import PdfReader
from PyPDF2._page import PageObject
import pandas as pd
import requests
import re
from datetime import datetime, date
import json
from address_to_place import address_to_place
from get_lat_lng import get_lat_lng_from_address
from datetime import datetime
from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine

# Connect to the PostgreSQL database
def setup_db(main_config) -> Engine:
    host = main_config.get('POSTGRESQL', 'host')
    database = main_config.get('POSTGRESQL', 'database')
    user = main_config.get('POSTGRESQL', 'user')
    password = main_config.get('POSTGRESQL', 'password')

    db_uri = f'postgresql://{user}:{password}@{host}/{database}'
    engine = create_engine(db_uri)

    return engine

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

# Checks if input string is or is not a case id.
# Used in tokenizer to make sure that delimiter is indeed the disposition and not word in crime title.
def is_valid_case_id(case_id_str: str) -> bool:
    id_patterns = [r'^\d{4}-\d{4}$', r'^\d{4}-[A-Za-z]{3}\d{2}$']
    for pattern in id_patterns:
        if re.match(pattern, case_id_str):
            return True
        
    return False

# Tokenizes each crime into separate elements of a 2D string array, where each 1st dimension
# element is each crime and each 2nd dimension element is each space/newline delimited string.
def tokenizer(page: PageObject) -> list:

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
            if textToken[elem] == delimiter:
                if delimiter == "ARREST" and textToken[elem+1] == "-":
                    crime_list.append(buffer_list)
                    buffer_list = []
                
                elif delimiter == "EXC" and textToken[elem+1] == "CLR":
                    crime_list.append(buffer_list)
                    buffer_list = []

                elif delimiter != "ARREST" and is_valid_case_id(textToken[elem+1]):
                    crime_list.append(buffer_list)
                    buffer_list = []
            
        buffer_list.append(textToken[elem])
    
    crime_list.append(buffer_list)
    return crime_list

# Parses each crime element by grouping unjoined tokens together that correspond to the same
# dictionary key.
def parser(crime_list: list) -> list:
    REP_DATE_INDEX = 2
    REP_TIME_INDEX = 3
    START_DATE_INDEX = 5
    START_TIME_INDEX = 6
    END_DATE_INDEX = 8
    END_TIME_INDEX = 9

    crime_list_len = len(crime_list)

    for i in range(crime_list_len):
        try:
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
        except IndexError: continue

        try:
            if is_valid_date(crime_list[i][4][-8:]):
                    crime_list[i].insert(5, crime_list[i][4][-8:])
                    crime_list[i][4] = crime_list[i][4][:-8].strip()
        except IndexError: pass

        if len(crime_list[i]) == 10 and is_valid_time_label(crime_list[i][-1]):
            crime_list[i].append("UNSPECIFIED CAMPUS")

        if len(crime_list[i]) == 11:
            crime_list[i][REP_DATE_INDEX] += " " + crime_list[i][REP_TIME_INDEX]
            crime_list[i][START_DATE_INDEX] += " " + crime_list[i][START_TIME_INDEX]
            crime_list[i][END_DATE_INDEX] += " " + crime_list[i][END_TIME_INDEX]
            del crime_list[i][REP_TIME_INDEX]
            del crime_list[i][START_TIME_INDEX - 1]
            del crime_list[i][END_TIME_INDEX - 2]

    return crime_list

# Converts crimes list to a Pandas DataFrame, then saves to a csv file.
def dump_to_sql_csv(crime_list: list, command_str: str, engine: Engine, GMaps_API_KEY: str) -> None:
    # Columns dict to save key names and list indices.
    columns = {"disposition": 0, "case_id": 1, "report_dt": 2, 
            "title": 3, "start_dt": 4, "address": 5, 
            "end_dt": 6, "campus": 7}
    
    # If loadcrimes, new df is generated. If addcrimes, previous df from csv is loaded.
    if command_str == '-loadcrimes':
        crimes_df = pd.DataFrame(columns=columns.keys())

    elif command_str == '-addcrimes':
        crimes_df = pd.read_csv('crimes.csv', index_col=0)

    for crime in crime_list:
        if len(crime) == 8:
            # If crime is not already in df (indicated by case ID), address_to_place() is called to
            # generate place name from address. If the crime's already present, old place name is used;
            # no need to regenerate it.
            # Latitude and longitude generated from address. Dates and times reformatted to database format.
            if crime[columns["case_id"]] not in crimes_df["case_id"].values:
                lat, lng = get_lat_lng_from_address(crime[columns["address"]], GMaps_API_KEY)
                place = address_to_place(crime[columns["address"]], lat, lng, GMaps_API_KEY)
            else:
                place = crimes_df.loc[crimes_df["case_id"] == crime[columns["case_id"]], "place"].values[0]
                lat = crimes_df.loc[crimes_df["case_id"] == crime[columns["case_id"]], "lat"].values[0]
                lng = crimes_df.loc[crimes_df["case_id"] == crime[columns["case_id"]], "lng"].values[0]

            try:
                report_dt = datetime.strptime(crime[columns["report_dt"]], "%m/%d/%y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")
                start_dt = datetime.strptime(crime[columns["start_dt"]], "%m/%d/%y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")
                end_dt = datetime.strptime(crime[columns["end_dt"]], "%m/%d/%Y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")

            except ValueError:
                print(crime)
                continue

            # Index is at bottom of df if crime is new; index of crime is used if it's already present 
            # to update it.
            index = len(crimes_df) + 1 if crime[columns["case_id"]] not in crimes_df["case_id"].values else crimes_df.loc[crimes_df["case_id"] == crime[columns["case_id"]]].index.values[0]

            crime_data = {
                "case_id": crime[columns["case_id"]],
                "disposition": crime[columns["disposition"]],
                "title": crime[columns["title"]],
                "campus": crime[columns["campus"]],
                "address": crime[columns["address"]],
                "place": place,
                "lat": lat,
                "lng": lng,
                "report_dt": report_dt,
                "start_dt": start_dt,
                "end_dt": end_dt
            }
            
            # Crime list is added to df in proper order.
            crimes_df.loc[index] = crime_data

    # df written to csv file.
    crimes_df.to_csv('crimes.csv')
    print("Crime CSV updated.")

    crimes_df.to_sql('crimes', engine, if_exists='replace', index=False)
    print("Crime database updated.")

# Requests the url of the daily crime log, opens the file, calls PdfReader to read the pdf's
# contents, calls the tokenizer and parser, then adds the parsed list to a csv.
def crime_load(command_str: str, engine: Engine, GMaps_API_KEY: str) -> None:
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

    dump_to_sql_csv(crimes_list, command_str, engine, GMaps_API_KEY)

# Simple function to copy current crimes.csv file to backups folder with added date.
def backup_crimes() -> None:
    crimes_df = pd.read_csv('crimes.csv', index_col=0)

    today = date.today().strftime("%m-%d-%Y")
    backup_csv_name = f"crimes-{today}.csv"
    
    crimes_df.to_csv(f"./backups/{backup_csv_name}")
    print("Crime CSV backed up.")

# Load list of crimes by crime type and status
def load_crime_and_status_lists() -> None:
    crimes_df = pd.read_csv('crimes.csv', index_col=0)

    crime_list = {}
    status_list = {}
    for index, crime in crimes_df.iterrows():
        if crime["title"] not in crime_list.keys():
            crime_list[crime["title"]] = 1
        else:
            crime_list[crime["title"]] += 1

        if crime["disposition"] not in status_list.keys():
            status_list[crime["disposition"]] = 1
        else:
            status_list[crime["disposition"]] += 1

    with open('crime_list.json', 'w') as f:
        json.dump(crime_list, f, indent=4)

    with open('status_list.json', 'w') as f:
        json.dump(status_list, f, indent=4)

    print("Crime and status lists loaded.")
 
if __name__ == "__main__":
    command_str = '-addcrimes'

    config = ConfigParser()
    config.read('config.ini')

    engine = setup_db(config)

    GMAPS_API_KEY = config.get('DISCORD', 'GMAPS_API_KEY')

    crime_load(command_str, engine, GMAPS_API_KEY)
    backup_crimes()
    load_crime_and_status_lists()
