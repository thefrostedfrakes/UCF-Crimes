'''

UCF Crimes: loadcrimes.py
Written by Ethan Frakes

'''

import utils
from PyPDF2 import PdfReader
from PyPDF2._page import PageObject
import pandas as pd
import requests
from datetime import datetime, date
import json
from datetime import datetime
from configparser import ConfigParser
from sqlalchemy import text
from sqlalchemy.engine.base import Engine

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

                elif delimiter != "ARREST" and utils.is_valid_case_id(textToken[elem+1]):
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

                elif utils.is_valid_time_label(crime_list[i][j]):
                    j += 1
                    while j + 1 < len(crime_list[i]) and not utils.is_valid_date(crime_list[i][j+1]) and not utils.is_valid_time_label(crime_list[i][j+1]):
                        crime_list[i][j] += " " + crime_list[i][j+1]
                        crime_list[i].remove(crime_list[i][j+1])
        except IndexError: continue

        try:
            if utils.is_valid_date(crime_list[i][4][-8:]):
                    crime_list[i].insert(5, crime_list[i][4][-8:])
                    crime_list[i][4] = crime_list[i][4][:-8].strip()
        except IndexError: pass

        if len(crime_list[i]) == 10 and utils.is_valid_time_label(crime_list[i][-1]):
            crime_list[i].append("UNSPECIFIED CAMPUS")

        if len(crime_list[i]) == 11:
            crime_list[i][REP_DATE_INDEX] += " " + crime_list[i][REP_TIME_INDEX]
            crime_list[i][START_DATE_INDEX] += " " + crime_list[i][START_TIME_INDEX]
            crime_list[i][END_DATE_INDEX] += " " + crime_list[i][END_TIME_INDEX]
            del crime_list[i][REP_TIME_INDEX]
            del crime_list[i][START_TIME_INDEX - 1]
            del crime_list[i][END_TIME_INDEX - 2]

    return crime_list

def update_db(crime_list: list, engine: Engine, GMaps_API_KEY: str) -> None:
    # Columns dict to save key names and list indices.
    columns = {"disposition": 0, "case_id": 1, "report_dt": 2, 
                "title": 3, "start_dt": 4, "address": 5, 
                "end_dt": 6, "campus": 7}

    for crime in crime_list:
        if len(crime) == 8:
            connection = engine.connect()
            case_id = crime[columns['case_id']]
            query = f"SELECT * FROM crimes WHERE case_id = '{case_id}'"
            result = connection.execute(text(query))

            address = crime[columns['address']].replace("'", "''")
            title = crime[columns['title']].replace("'", "''")

            try:
                report_dt = datetime.strptime(crime[columns["report_dt"]], "%m/%d/%y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")
                start_dt = datetime.strptime(crime[columns["start_dt"]], "%m/%d/%y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")
                end_dt = datetime.strptime(crime[columns["end_dt"]], "%m/%d/%Y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")

            except ValueError:
                print(crime)
                continue
            
            # If crime is not already in database (indicated by case ID), get_lat_lng_from_address() and address_to_place() 
            # are called to generate lat, lng, and place name from address. If the crime's already present, they are not updated
            # when the crime is updated instead of inserted.
            if result.rowcount == 0:
                lat, lng = utils.get_lat_lng_from_address(crime[columns["address"]], GMaps_API_KEY)
                place = utils.address_to_place(crime[columns["address"]], lat, lng, GMaps_API_KEY).replace("'", "''")

                lat_lng_header = f", lat, lng" if lat and lng else ""
                lat_lng_insert = f", {lat}, {lng}" if lat and lng else ""
                query = f"INSERT INTO crimes (case_id, disposition, title, campus, address, place{lat_lng_header}, report_dt, start_dt, end_dt) " \
                        f"VALUES ('{case_id}', '{crime[columns['disposition']]}', '{title}', '{crime[columns['campus']]}', '{address}', " \
                        f"'{place}'{lat_lng_insert}, '{report_dt}', '{start_dt}', '{end_dt}')"
            else:
                query = f"UPDATE crimes SET report_dt = '{report_dt}', title = '{title}', " \
                        f"start_dt = '{start_dt}', end_dt = '{end_dt}', address = '{address}', " \
                        f"disposition = '{crime[columns['disposition']]}', campus = '{crime[columns['campus']]}' WHERE case_id = '{case_id}'"

            connection.execute(text(query))
            connection.commit()
            connection.close()

    print("Crime database updated.")

# Simple function to copy current database to pandas DataFrame, then insert that DataFrame to a
# backup CSV file.
def backup_crimes(engine: Engine) -> None:
    crimes_df = pd.read_sql_table("crimes", engine)

    today = date.today().strftime("%m-%d-%Y")
    backup_csv_name = f"crimes-{today}.csv"
    
    crimes_df.to_csv(f"./backups/{backup_csv_name}")
    print("Crime CSV backed up.")

# Load list of crimes by crime type and status
def load_crime_and_status_lists(engine: Engine) -> None:
    crimes_df = pd.read_sql_table("crimes", engine)

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

# Requests the url of the daily crime log, opens the file, calls PdfReader to read the pdf's
# contents, calls the tokenizer and parser, then adds the parsed list to the database.
def crime_load(engine: Engine, GMaps_API_KEY: str) -> None:
    pdf_filename = 'AllDailyCrimeLog.pdf'
    #crime_url = 'https://police.ucf.edu/sites/default/files/logs/ALL%20DAILY%20crime%20log.pdf'
    crime_url = 'https://police.ucf.edu/wp-content/uploads/clery/ALL%20DAILY%20crime%20log.pdf'

    # Requests the url of the crime log from UCF PD's website and writes the pdf to the local
    # machine as 'AllDailyCrimeLog.pdf'. Then opens a PdfReader instance to read the pdf.
    rsp = requests.get(crime_url, timeout=30)

    with open(pdf_filename, 'wb') as f:
        f.write(rsp.content)
        
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

    update_db(crimes_list, engine, GMaps_API_KEY)
    backup_crimes(engine)
    load_crime_and_status_lists(engine)
 
if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')

    engine = utils.setup_db(config)

    GMAPS_API_KEY = config.get('DISCORD', 'GMAPS_API_KEY')

    crime_load(engine, GMAPS_API_KEY)
