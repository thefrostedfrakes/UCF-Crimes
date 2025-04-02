'''

UCF Crimes: loadcrimes.py
Written by Ethan Frakes

'''

import utils
from PyPDF2 import PdfReader
from PyPDF2._page import PageObject
import pandas as pd
import requests
import re
from datetime import datetime, date
import json
from datetime import datetime
from configparser import ConfigParser
from sqlalchemy import text

class UCFCrimeLogLoader:
    def __init__(self, config: ConfigParser):
        self.valid_campus_names = ["MAIN", "UCF", "ROSEN"]
        self.valid_dispos = ["UNFOUNDED", "EXC", "ARREST", "INACTIVE", 
                "CLOSED", "OPEN", "ACTIVE", "REPORT"]
        self.crimes_list = []
        self.engine = utils.setup_db(config)
        self.GMAPS_API_KEY = config.get('DISCORD', 'GMAPS_API_KEY')

    # Tokenizes each crime into separate elements of a 2D string array, where each 1st dimension
    # element is each crime and each 2nd dimension element is each space/newline delimited string.
    def tokenizer(self, page: PageObject) -> list:
        # Text extracted from page and split between spaces and newlines.
        crime_list = []
        text = page.extract_text()
        rosen_delims = ["HOSPITALITY", "MANAGEMENT"]
        patterns = [f'(?<=\S)(?:({"|".join(self.valid_campus_names + self.valid_dispos)}))',
                    f'(?:({"|".join(rosen_delims)}))(?<=\S)']
        
        text = re.sub(patterns[0], r' \1', text)
        text = re.sub(patterns[1], r'\1 ', text)

        textToken = text.split()
        buffer_list = []

        # For each string in the textToken, if the string is one of the valid delimiters above
        # (end of one crime and beginning of another), buffer list is added to the crime list.
        for elem in textToken:
            if utils.is_valid_case_id(elem):
                crime_list.append(buffer_list)
                buffer_list = []
                
            buffer_list.append(elem)
        
        crime_list.append(buffer_list)
        return crime_list

    # Parses each crime element by grouping unjoined tokens together that correspond to the same
    # dictionary key.
    def parser(self, crime_list: list) -> list:
        INCIDENT_INDEX = 1
        CAMPUS_INDEX = 2
        DISPOSITION_INDEX = 3
        REP_DATE_INDEX = 4
        REP_TIME_INDEX = 5
        START_DATE_INDEX = 6
        START_TIME_INDEX = 7
        END_DATE_INDEX = 8
        END_TIME_INDEX = 9
        ADDRESS_INDEX = 10

        invalid_prelims = ["TRAFFIC", "TRESPASSING", "DRUG", "LAW", "WARRANT"]
        pattern = r'\b(?:' + '|'.join(invalid_prelims) + r')\b'
        crime_list_len = len(crime_list)

        for i in range(crime_list_len):
            try:
                # Group incident title elements together until campus name is reached; or disposition if unspecified campus.
                while crime_list[i][CAMPUS_INDEX] not in self.valid_campus_names and (crime_list[i][CAMPUS_INDEX] not in self.valid_dispos or re.search(pattern, crime_list[i][INCIDENT_INDEX])):
                    crime_list[i][INCIDENT_INDEX] += " " + crime_list[i][INCIDENT_INDEX+1]
                    crime_list[i].remove(crime_list[i][INCIDENT_INDEX+1])

                # If the element in campus index contains disposition, then insert unspecified campus at campus index.
                if crime_list[i][CAMPUS_INDEX] in self.valid_dispos:
                    crime_list[i].insert(CAMPUS_INDEX, "UNSPECIFIED CAMPUS")

                # Else, then group campus name elements together until first disposition element is reached.
                else:
                    while crime_list[i][DISPOSITION_INDEX] not in self.valid_dispos:
                        crime_list[i][CAMPUS_INDEX] += " " + crime_list[i][CAMPUS_INDEX+1]
                        crime_list[i].remove(crime_list[i][CAMPUS_INDEX+1])

                # Group disposition elements together until report date is reached (indicated if element at rep date index is a valid date)
                while not utils.is_valid_date(crime_list[i][REP_DATE_INDEX]):
                    crime_list[i][DISPOSITION_INDEX] += " " + crime_list[i][DISPOSITION_INDEX+1]
                    crime_list[i].remove(crime_list[i][DISPOSITION_INDEX+1])

                # Join all address elements together (everything from address index onwards is address element), then slice list.
                crime_list[i][ADDRESS_INDEX] = ' '.join(crime_list[i][ADDRESS_INDEX:]) 
                crime_list[i] = crime_list[i][0:ADDRESS_INDEX+1]

                # Group corresponding date and time elements together for report, start, and end datetimes.
                crime_list[i][REP_DATE_INDEX] += " " + crime_list[i][REP_TIME_INDEX]
                crime_list[i][START_DATE_INDEX] += " " + crime_list[i][START_TIME_INDEX]
                crime_list[i][END_DATE_INDEX] += " " + crime_list[i][END_TIME_INDEX]
                del crime_list[i][REP_TIME_INDEX]
                del crime_list[i][START_TIME_INDEX - 1]
                del crime_list[i][END_TIME_INDEX - 2]
            except IndexError: continue

        return crime_list

    def update_db(self) -> None:
        # Columns dict to save key names and list indices.
        columns = {"case_id": 0, "title": 1, "campus": 2, 
                    "disposition": 3, "report_dt": 4, "start_dt": 5, 
                    "end_dt": 6, "address": 7}
        
        connection = self.engine.connect()

        for crime in self.crimes_list:
            if len(crime) == 8:
                case_id = crime[columns['case_id']]
                query = f"SELECT * FROM crimes WHERE case_id = '{case_id}'"
                result = connection.execute(text(query))

                address = crime[columns['address']].replace("'", "''")
                title = crime[columns['title']].replace("'", "''")

                try:
                    report_dt = datetime.strptime(crime[columns['report_dt']], "%m/%d/%y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")
                    start_dt = datetime.strptime(crime[columns['start_dt']], "%m/%d/%y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")
                    end_dt = datetime.strptime(crime[columns['end_dt']], "%m/%d/%Y %H:%M").strftime("%Y-%m-%dT%H:%M:%SZ")

                except ValueError:
                    print(crime)
                    continue
                
                # If crime is not already in database (indicated by case ID), get_lat_lng_from_address() and address_to_place() 
                # are called to generate lat, lng, and place name from address. If the crime's already present, they are not updated
                # when the crime is updated instead of inserted.
                if result.rowcount == 0:
                    lat, lng = utils.google_geocoder(f"{crime[columns['address']]}, ORLANDO, FL", self.GMAPS_API_KEY)
                    place = utils.address_to_place(crime[columns['address']], lat, lng, self.GMAPS_API_KEY).replace("'", "''")

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

        print("Crime database updated.")
        connection.close()

    # Simple function to copy current database to pandas DataFrame, then insert that DataFrame to a
    # backup CSV file.
    def backup_crimes(self) -> None:
        crimes_df = pd.read_sql_table("crimes", self.engine)

        today = date.today().strftime("%m-%d-%Y")
        backup_csv_name = f"crimes-{today}.csv"
        
        crimes_df.to_csv(f"./backups/{backup_csv_name}")
        print("Crime CSV backed up.")

    # Load list of crimes by crime type and status
    def load_crime_and_status_lists(self) -> None:
        crimes_df = pd.read_sql_table("crimes", self.engine)

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
    def __call__(self) -> None:
        pdf_filename = 'AllDailyCrimeLog.pdf'
        crime_url = 'https://police.ucf.edu/wp-content/uploads/clery/ALL%20DAILY%20crime%20log.pdf'

        # Requests the url of the crime log from UCF PD's website and writes the pdf to the local
        # machine as 'AllDailyCrimeLog.pdf'. Then opens a PdfReader instance to read the pdf.
        rsp = requests.get(crime_url, timeout=30)

        with open(pdf_filename, 'wb') as f:
            f.write(rsp.content)
            
        reader = PdfReader(pdf_filename)

        # Each page in the pdf is tokenized and parsed.
        for i in range(len(reader.pages)):
            crime_list = self.tokenizer(reader.pages[i])
            crime_list = self.parser(crime_list)
            for crime in crime_list:
                self.crimes_list.append(crime)

        # Just to test each list element to ensure it was properly parsed.
        for crime in self.crimes_list:
            if len(crime) == 8: print("CORRECT FORMAT")
            print(crime, '\n')

        self.update_db()
        self.backup_crimes()
        self.load_crime_and_status_lists()

 
if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')

    crimeLogLoader = UCFCrimeLogLoader(config)
    crimeLogLoader()
