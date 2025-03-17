'''

UCF Crimes: orlando_orange.py

An extension to UCF Crimes that adds all Orlando PD & OSCO active calls to separate database 
tables, will be used for querying calls and displaying active call report each hour.

Written by Ethan Frakes

'''

import requests
from bs4 import BeautifulSoup
from utils import setup_db
import xmltodict
import pandas as pd
from time import sleep
from datetime import datetime
from configparser import ConfigParser
from sqlalchemy import text
from sqlalchemy.engine.base import Engine

def load_orlando_active(engine: Engine) -> None:
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
            # traceback.print_exc()

    query = f"SELECT count(*) AS exact_count FROM orlando_crimes"
    result = connection.execute(text(query)).fetchone()
    print("Orlando crimes database updated.")
    print(f"Current number of entries in database: {result[0]}")
    connection.close()

def load_orange_active(engine: Engine) -> None:
    '''
    Load XML file from OCSO website with BeautifulSoup and parse the file to SQL table.
    '''
    connection = engine.connect()

    r = requests.get('https://www.ocso.com/Portals/0/CFS_FEED/activecalls.xml')
    soup = BeautifulSoup(r.content, "lxml-xml")
    active_dict = xmltodict.parse(str(soup))

    for crime in active_dict["CALLS"]["CALL"]:
        try:
            year_date = datetime.strptime(crime["ENTRYTIME"], "%m/%d/%Y %I:%M:%S %p").strftime("%Y-%j")
            entrytime = datetime.strptime(crime["ENTRYTIME"], "%m/%d/%Y %I:%M:%S %p").strftime("%-m/%d/%Y %H:%M:%S")
            expanded_incident = f"{year_date}-{crime['@INCIDENT']}"
            query = f"""SELECT * FROM orange_crimes WHERE incident = '{expanded_incident}'"""
            result = connection.execute(text(query))
            if crime['LOCATION']:
                location = crime['LOCATION'].replace("'", "''")
            else:
                location = crime['LOCATION']

            if result.rowcount == 0:
                query = f"""INSERT INTO orange_crimes (incident, entrytime, description, location, sector, zone, rd)""" \
                        f"""VALUES ('{expanded_incident}', '{entrytime}', '{crime['DESC']}', '{location}', '{crime['SECTOR']}', '{crime["ZONE"]}', '{crime["RD"]}')"""

            else:
                query = f"""UPDATE orange_crimes SET entrytime = '{entrytime}', description = '{crime['DESC']}', """ \
                        f"""location = '{location}', sector = '{crime['SECTOR']}', zone = '{crime["ZONE"]}', rd = '{crime["RD"]}' WHERE incident = '{expanded_incident}'"""
                
            connection.execute(text(query))
            connection.commit()

        except Exception as e:
            print(f"Exception occurred: {type(e).__name__}: {str(e)}")
            # traceback.print_exc()

    query = f"SELECT count(*) AS exact_count FROM orange_crimes"
    result = connection.execute(text(query)).fetchone()
    print("Orange County crimes database updated.")
    print(f"Current number of entries in database: {result[0]}")
    connection.close()

def backup_tables(engine: Engine) -> None:
    orlando_list = pd.read_sql_table("orlando_crimes", engine)
    orlando_list['date'] = pd.to_datetime(orlando_list['date'], format='%m/%d/%Y %H:%M')
    orlando_list = orlando_list.sort_values(by='date')
    orlando_list = orlando_list.reset_index(drop=True)
    orlando_list.to_csv("./backups/orlando_backup.csv", index=True)

    orange_list = pd.read_sql_table("orange_crimes", engine)
    orange_list['entrytime'] = pd.to_datetime(orange_list['entrytime'], format='%m/%d/%Y %H:%M:%S')
    orange_list = orange_list.sort_values(by='entrytime')
    orange_list = orange_list.reset_index(drop=True)
    orange_list.to_csv("./backups/orange_backup.csv", index=True)

    print("OPD & OSCO tables backed up to CSV files.")

if __name__ == '__main__':
    main_config = ConfigParser()
    main_config.read('config.ini')
    engine = setup_db(main_config)

    counter = 0

    print("Starting OPD & OCSO time counter (every 10 mins)")
    while True:
        if counter >= 600:
            counter = 0
            try:
                load_orlando_active(engine)
                load_orange_active(engine)
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {str(e)}")
                # traceback.print_exc()
        
        counter += 1

        now = datetime.now()
        if now.hour == 1 and now.minute == 0 and now.second == 0:
            backup_tables(engine)

        sleep(1)
