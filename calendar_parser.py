import requests
from ics import Calendar

# To parse .ics files from a URL that was given
def parse_ics(url):
    try:
        response = requests.get(url) #Sends a GET request to the URL
        response.raise_for_status() #Just incase the HTTP request fails, it will raise an error like 404 or 500
        c = Calendar(response.text)

        #Goes through all the .ics file into a calendar object
        for event in c.events:
            print("📅 Event:")
            print(f"  Summary: {event.name}")
            print(f"  Begins:  {event.begin}")
            print(f"  Ends:    {event.end}")
            print(f"  Location:{event.location}")
            print("-" * 40)

    except Exception as e: #Prints an error messsage if the feteching fails or something
        print(f"❌ Failed to parse {url}: {e}")

# Example .ics URL
ics_url = "https://calendar.fiu.edu/event/summer-open-registration-for-degree-seeking-students.ics"
parse_ics(ics_url) #This will call the fucntion of the url given above
