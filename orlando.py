'''

UCF Crimes: orlando.py

An extension to UCF Crimes that adds all orlando active calls to separate database table, will
be used for querying calls and displaying active call report each hour.

Written by Ethan Frakes

'''

import requests
from bs4 import BeautifulSoup
from utils import setup_db
import xmltodict
import pandas as pd
from time import sleep
import traceback
from configparser import ConfigParser
from sqlalchemy import text
from sqlalchemy.engine.base import Engine

def load_orlando_active_csv(csv_file: str) -> None:
    '''
    Load XML file from Orlando PD website with BeautifulSoup and parse the file to a CSV.
    '''

    active_req = requests.get('https://www1.cityoforlando.net/opd/activecalls/activecadpolice.xml')
    soup = BeautifulSoup(active_req.content, "lxml-xml")
    active_dict = xmltodict.parse(str(soup))

    crimes_csv = pd.read_csv(csv_file, index_col=0)
    new_rows = []
        
    for crime in active_dict["CALLS"]["CALL"]:
        if crime["@incident"] not in crimes_csv["incident"].values:
            crime_data = {
                'incident': crime["@incident"],
                'date': crime["DATE"],
                'desc': crime["DESC"],
                'location': crime["LOCATION"],
                'district': crime["DISTRICT"],
            }
            new_rows.append(crime_data)
           
    crimes_csv = pd.concat([pd.DataFrame(new_rows), crimes_csv], ignore_index=True)
    crimes_csv.to_csv(csv_file, index=True)   

    print("orlando.csv refreshed.")

def load_orlando_active_sql(engine: Engine) -> None:
    '''
    Load XML file from Orlando PD website with BeautifulSoup and parse the file to SQL table.
    '''
    
    connection = engine.connect()

    active_req = requests.get('https://www1.cityoforlando.net/opd/activecalls/activecadpolice.xml')
    soup = BeautifulSoup(active_req.content, "lxml-xml")
    active_dict = xmltodict.parse(str(soup))
        
    for crime in active_dict["CALLS"]["CALL"]:
        try:
            query = f"""SELECT * FROM orlando_crimes WHERE incident = '{crime["@incident"]}'"""
            result = connection.execute(text(query))

            if result.rowcount == 0:
                query = f"""INSERT INTO orlando_crimes (incident, date, description, location, district)""" \
                        f"""VALUES ('{crime['@incident']}', '{crime['DATE']}', '{crime['DESC']}', '{crime['LOCATION'].replace("'", "''")}', '{crime['DISTRICT']}')"""

            else:
                query = f"""UPDATE orlando_crimes SET date = '{crime['DATE']}', description = '{crime['DESC']}', """ \
                        f"""location = '{crime['LOCATION'].replace("'", "''")}', district = '{crime['DISTRICT']}' WHERE incident = '{crime['@incident']}'"""
                
            connection.execute(text(query))
            connection.commit()

        except Exception as e:
            print(f"Exception occurred: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    query = f"SELECT count(*) AS exact_count FROM orlando_crimes"
    result = connection.execute(text(query)).fetchone()
    print("Orlando crimes database updated.")
    print(f"Current number of entries in database: {result[0]}")
    connection.close()

def check_orlando_size_csv(csv_file: str) -> None:
    crimes_csv = pd.read_csv(csv_file)
    csv_size = crimes_csv.shape[0]

    print(f"Current number of entries in orlando.csv: {csv_size}")

if __name__ == '__main__':
    main_config = ConfigParser()
    main_config.read('config.ini')
    engine = setup_db(main_config)

    orlando_counter = 0

    print("Starting Orlando time counter (every 10 mins)")
    while True:
        if orlando_counter >= 600:
            orlando_counter = 0
            try:
                csv_file = "orlando.csv"
                load_orlando_active_sql(engine)
                load_orlando_active_csv(csv_file)
                check_orlando_size_csv(csv_file)
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {str(e)}")
                traceback.print_exc()

        orlando_counter += 1

        sleep(1)
