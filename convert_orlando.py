'''

UCF Crimes: convert_orlando.py

Helper functions for orlando calls, including converting csv file to SQL table if needed
and filtering duplicates from csv.

Written by Ethan Frakes

'''

import pandas as pd
from utils import setup_db
from sqlalchemy import Engine
from sqlalchemy import text
from configparser import ConfigParser

def convert_csv_to_db(engine: Engine):
    connection = engine.connect()

    crimes_csv = pd.read_csv('orlando.csv')
    for idx, crime in crimes_csv.iterrows():
        query = f"SELECT * FROM orlando_crimes WHERE incident = '{crime['incident']}'"
        result = connection.execute(text(query))

        if result.rowcount == 0:
            print(idx)
            query = f"""INSERT INTO orlando_crimes (incident, date, description, location, district)""" \
                    f"""VALUES ('{crime['incident']}', '{crime['date']}', '{crime['desc']}', '{crime['location'].replace("'", "''")}', '{crime['district']}')"""
            connection.execute(text(query))
            connection.commit()
        
        else:
            break

    connection.close()

    print("Orlando crimes database updated.")

def list_csv_data():
    pd.set_option("display.max_rows", None)
    csv_df = pd.read_csv('orlando.csv')
    print(len(csv_df))
    print(csv_df['district'].value_counts())

def filter_duplicates():
    crimes_csv = pd.read_csv('orlando.csv', index_col=0)
    crimes_csv_filtered = crimes_csv[~crimes_csv.duplicated(subset='incident', keep='first')]
    crimes_csv_filtered = crimes_csv_filtered.reset_index(drop=True)
    crimes_csv_filtered.to_csv('orlando_filtered.csv', index=True)

if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')

    engine = setup_db(config)
    convert_csv_to_db(engine)
    #filter_duplicates()

