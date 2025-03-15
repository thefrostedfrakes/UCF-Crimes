import requests
from bs4 import BeautifulSoup
import xmltodict
from configparser import ConfigParser
from sqlalchemy import text
from sqlalchemy.engine.base import Engine
from datetime import datetime
from time import sleep
from utils import setup_db

def load_orange_active(engine: Engine) -> None:
    connection = engine.connect()

    r = requests.get('https://www.ocso.com/Portals/0/CFS_FEED/activecalls.xml')
    soup = BeautifulSoup(r.content, "lxml-xml")
    active_dict = xmltodict.parse(str(soup))

    for crime in active_dict["CALLS"]["CALL"]:
        try:
            year_date = datetime.now().strftime("%Y-%j")
            expanded_incident = f"{year_date}-{crime['@INCIDENT']}"
            query = f"""SELECT * FROM orange_crimes WHERE incident = '{expanded_incident}'"""
            result = connection.execute(text(query))
            entrytime = datetime.strptime(crime["ENTRYTIME"], "%m/%d/%Y %I:%M:%S %p").strftime("%-m/%d/%Y %H:%M:%S")
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

if __name__ == '__main__':
    main_config = ConfigParser()
    main_config.read('config.ini')
    engine = setup_db(main_config)

    orange_counter = 0

    print("Starting Orange County time counter (every 10 mins)")
    while True:
        if orange_counter >= 600:
            orange_counter = 0
            try:
                load_orange_active(engine)
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {str(e)}")
                # traceback.print_exc()

        orange_counter += 1

        sleep(1)
