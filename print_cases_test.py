'''

UCF Crimes: sendcrimes.py
Written by Ethan Frakes
and Maverick Reynolds

'''

import json
from datetime import datetime
import string_adjustments as stradj
import gpt_expand

USE_GPT = True
NUM_TO_TEST = 5


with open('crimes.json', 'r') as f:
    crimes = json.load(f)

test_list = crimes.items()
if USE_GPT:
    # Only do a few since it takes some time (and $)
    test_list = list(crimes.items())[-NUM_TO_TEST:]

for key, crime in test_list:
    # Reformat dates and times
    report_date_time = datetime.strptime(crime["Report Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["Start Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["End Date/Time"], '%m/%d/%Y %H:%M').strftime('%m/%d/%y %I:%M %p')

    case_title = stradj.case_title_format(crime["Crime"])
    if USE_GPT:
        case_title = gpt_expand.gpt_title_expand(case_title)
    case_title = stradj.attach_emojis(case_title)

    disp_addr = stradj.replace_address(stradj.expand_address(crime['Location']))
        
    # Compose message
    description = f"""Occurred at {stradj.gen_title(crime['Campus'])}, {disp_addr}
Case: {key}
Reported on {report_date_time} {report_date_time}
Between {start_date_time} - {end_date_time}
Status: {crime['Disposition'].title()}"""

    print(case_title)
    print(description)
    print()