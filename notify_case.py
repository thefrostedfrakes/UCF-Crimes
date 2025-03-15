from configparser import ConfigParser
from meta_toolkit import post_to_meta_both
from datetime import date, datetime, timedelta
import telegram
import utils
from image import generate_image
import pandas as pd
from xed import XED
from requests.exceptions import HTTPError

def sendTeleg(message, config, photo=None):
    sent = False
    retry_c = 0
    while sent == False:
        try:
            bot = telegram.Bot(token=config.get('TELEGRAM', 'BOT_TOKEN'))
            if photo:
                sent = bot.send_photo(chat_id=config.get('TELEGRAM', 'ROOM_ID'), photo=photo, caption=message, timeout=20, )
            else:
                sent = bot.send_message(chat_id=config.get('TELEGRAM', 'ROOM_ID'), text=message, timeout=20)
        except Exception as err:
            print('err.args:')
            print(err.args)
            print(f"Unexpected {err=}, {type(err)=}")
            print("\nString err:\n"+str(err))
            if retry_c > 4:
                print('Telegram attempts exceeded. Message not sent.')
                break
            elif str(err) == 'Unauthorized':
                print('Invalid Telegram bot token, message not sent.')
                break
            elif str(err) == 'Timed out':
                retry_c += 1
                print('Telegram timeout count: '+str(retry_c))
                pass
            elif str(err) == 'Chat not found':
                print('Invalid Telegram Chat ID, message not sent.')
                break
            elif str(err)[:35] == '[Errno 2] No such file or directory':
                print('Telegram module couldn\'t find an image to send.')
                break
            elif str(err) == 'Media_caption_too_long':
                print('Telegram image caption lenght exceeds 1024 characters. Message not send.')
                break
            else:
                print('[X] Unknown Telegram error. Message not sent.')
                break
        else:
            print("Telegram message successfully sent.")
    return sent

def notify_crime(crime, main_config):
    # Reformat dates and times
    report_date_time = datetime.strptime(crime["report_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["start_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["end_dt"], "%Y-%m-%dT%H:%M:%SZ").strftime('%m/%d/%y %I:%M %p')

    # Get the emojis from the formatted title
    # This should already have stradj.crime_title_format applied to it
    crime_emojis = utils.get_emojis(crime['title'])

    # Append the emojis to the title (includes space already)
    crime_title = crime['title'] + crime_emojis

    # Compose message
    message = f"{crime_title} \n" \
              f"Occurred at {utils.titlize(crime['campus'])}, {crime['place']} \n" \
              f"Case: {crime['case_id']} \n" \
              f"Reported on {report_date_time} \n" \
              f"Between {start_date_time} - {end_date_time} \n" \
              f"Status: {crime['disposition'].title()}" 

    print(message)
    
    # Create the image
    generate_image(crime)
    # Post to socials
    photo_name = "caseout.png"
    if main_config.getboolean("META", "ENABLE"):
        try:
            post_to_meta_both(main_config.get("META", "FB_PAGE_ID"), 
                            main_config.get("META", "IG_USER_ID"), photo_name, 
                            message, main_config.get("META", "ACCESS_TOKEN"))
        except HTTPError as e:
            print(f"HTTP Error: {e}")
        
    if main_config.getboolean("TELEGRAM", "ENABLE"):
        try:
            photo = open(photo_name, "rb")
            sendTeleg(message, main_config, photo)
        except HTTPError as e:
            print(f"HTTP Error: {e}")

    if main_config.getboolean("TWITTER", "ENABLE"):
        try:
            x_client = XED(main_config.get("TWITTER", "CONSUMER_KEY"), 
                        main_config.get("TWITTER", "CONSUMER_SECRET"), 
                        main_config.get("TWITTER", "ACCESS_TOKEN"), 
                        main_config.get("TWITTER", "ACCESS_TOKEN_SECRET"))
            x_client.post(message=message, media_list=[(photo_name, f"Map image over {crime['place']}")])
        except HTTPError as e:
            print(f"HTTP Error: {e}")

    return None

if __name__ == "__main__":
    # Read the config
    main_config = ConfigParser()
    main_config.read('config.ini')

    engine = utils.setup_db(main_config)
    yesterday = (date.today() - timedelta(days=1)).strftime("%m/%d/%y")

    query = f"SELECT * FROM crimes WHERE report_dt::date = '{yesterday}';"
    query_matches = pd.read_sql_query(query, engine)
    for index, crime in query_matches.iterrows():
        notify_crime(crime, main_config)
