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
 
for i, crime in enumerate(crimes["Crimes"]):
    # Reformat dates and times
    report_time = datetime.strptime(crime["Report Time"], '%H:%M').strftime('%I:%M %p')
    start_time = datetime.strptime(crime["Start Time"], '%H:%M').strftime('%I:%M %p')
    end_time = datetime.strptime(crime["End Time"], '%H:%M').strftime('%I:%M %p')
    end_date = datetime.strptime(crime["End Date"], '%m/%d/%Y').strftime('%m/%d/%y')

    case_title = stradj.case_title_format(crime["Crime"])
    case_title = stradj.attach_emojis(case_title)
        
    # Compose message
    description = f"""Occurred at {stradj.gen_title(crime['Campus'])}, {crime['Location']}
Case: {crime['Case #']}
Reported on {crime['Report Date']} {report_time}
Between {crime['Start Date']} {start_time} - {end_date} {end_time}
Status: {crime['Disposition'].title()}"""

    print(case_title)
    print(description)
    print()