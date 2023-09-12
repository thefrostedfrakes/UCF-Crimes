import json
from datetime import datetime
from string_adjustments import replace_address

with open('crimes.json', 'r') as f:
        crimes = json.load(f)

def add_address_key():
    reference_date = datetime.strptime("05/06/23 00:00", "%m/%d/%y %H:%M")
    for key, val in crimes.items():
        date = datetime.strptime(val["Report Date/Time"], "%m/%d/%y %H:%M")
        if date < reference_date:
            val["Address"] = val["Location"]
            val["Location"] = replace_address(val["Address"])
            print(val["Address"])
            print(val["Location"])

    with open('crimes_modded.json', 'w') as f:
        json.dump(crimes, f, indent=4)

def find_address_keys():
    start_date = datetime.strptime("05/06/23 00:00", "%m/%d/%y %H:%M")
    end_date = datetime.strptime("06/07/23 00:00", "%m/%d/%y %H:%M")
    found_flag = False
    with open('locations.json', 'r') as f:
            locations = json.load(f)

    for key, crime in crimes.items():
        date = datetime.strptime(crime["Report Date/Time"], "%m/%d/%y %H:%M")
        if date > start_date and date < end_date:
            for key, val in locations.items():
                if val == crime["Location"]:
                    crime["Address"] = key
                    found_flag = True
            
            if not found_flag:
                crime["Address"] = None

            found_flag = False

    with open('crimes.json', 'w') as f:
        json.dump(crimes, f, indent=4)

def fix_all_addresses():
    for key, crime in crimes.items():
        if crime.get("Address") is not None:
            crime["Address"] = replace_address(crime["Address"], location_name=False)

    with open('crimes.json', 'w') as f:
        json.dump(crimes, f, indent=4)

if __name__ == "__main__":
    #add_address_key()
    fix_all_addresses()