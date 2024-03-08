from configparser import ConfigParser
from meta_toolkit import post_to_meta_both
from datetime import date, datetime, timedelta
from send_telegram import sendTeleg
from titlize import titlize
from image import generate_image
from get_emojis import get_emojis
from loadcrimes import setup_db
import pandas as pd

def notify_crime(crime, main_config):
    # Reformat dates and times
    report_date_time = datetime.strptime(crime["report_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["start_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["end_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')

    # Get the emojis from the formatted title
    # This should already have stradj.crime_title_format applied to it
    crime_emojis = get_emojis(crime['title'])

    # Append the emojis to the title (includes space already)
    crime_title = crime['title'] + crime_emojis

    # Compose message
    message = f"{crime_title} \n" \
              f"Occurred at {titlize(crime['campus'])}, {crime['place']} \n" \
              f"Case: {crime['case_id']} \n" \
              f"Reported on {report_date_time} \n" \
              f"Between {start_date_time} - {end_date_time} \n" \
              f"Status: {crime['disposition'].title()}" 

    print(message)
    
    # Create the image
    generate_image(crime)
    # Post to socials
    photo = open('caseout.png', "rb")
    if main_config.getboolean("META", "ENABLE"):
        post_to_meta_both(main_config.get("META", "FB_PAGE_ID"), main_config.get("META", "IG_USER_ID"), 'caseout.png', message, main_config.get("META", "ACCESS_TOKEN"))
    if main_config.getboolean("TELEGRAM", "ENABLE"):
        sendTeleg(message, main_config, photo)
    return None


if __name__ == "__main__":
    # Read the config
    main_config = ConfigParser()
    main_config.read('config.ini')

    engine = setup_db(main_config)
    yesterday = (date.today() - timedelta(days=1)).strftime("%m/%d/%y")

    query = f"SELECT * FROM crimes WHERE report_dt::date = '{yesterday}';"
    query_matches = pd.read_sql_query(query, engine)
    for index, crime in query_matches.iterrows():
        notify_crime(crime, main_config)
