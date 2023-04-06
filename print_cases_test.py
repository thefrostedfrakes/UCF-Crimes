'''

UCF Crimes: sendcrimes.py
Written by Ethan Frakes
and Maverick Reynolds

'''

import json
from datetime import datetime
import string_adjustments as stradj

with open('crimes.json', 'r') as f:
    crimes = json.load(f)

for key, crime in crimes.items():
    # Reformat dates and times
    report_date_time = datetime.strptime(crime["Report Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    start_date_time = datetime.strptime(crime["Start Date/Time"], '%m/%d/%y %H:%M').strftime('%m/%d/%y %I:%M %p')
    end_date_time = datetime.strptime(crime["End Date/Time"], '%m/%d/%Y %H:%M').strftime('%m/%d/%y %I:%M %p')

    formatted_case_title = stradj.case_title_format(crime["Crime"])
    formatted_case_title = stradj.attach_emojis(formatted_case_title)
        
    # Compose message
    description = f"""Occurred at {stradj.gen_title(crime['Campus'])}, {crime['Location']}
Case: {key}
Reported on {report_date_time} {report_date_time}
Between {start_date_time} - {end_date_time}
Status: {crime['Disposition'].title()}"""

    print(formatted_case_title)
    print(description)
    print()