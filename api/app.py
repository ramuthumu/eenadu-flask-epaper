from datetime import datetime
from flask import Flask, render_template, request
from flask_caching import Cache
import requests
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

# Configure cache
app.config['CACHE_TYPE'] = 'SimpleCache'  # Simple in-memory cache, suitable for single-state apps
cache = Cache(app)
cache.init_app(app)


all_editions = {}

# Configure APScheduler
scheduler = BackgroundScheduler()

def clear_cache():
    with app.app_context():
        cache.clear()
        print("Cache cleared.")

# Schedule cache to be cleared every day at 5 PM and 6 PM
scheduler.add_job(func=clear_cache, trigger='cron', hour='16,17,18')
scheduler.start()

# Ensure the scheduler is shut down when the app exits
atexit.register(lambda: scheduler.shutdown())

eenadu_editions = []

@cache.memoize(timeout=86400)  # Cache for one day
def get_max_date():
    url = "https://epaper.eenadu.net/Home/GetMaxdateJson"
    response = requests.get(url)
    return response.text.strip('\"')

@cache.memoize(timeout=86400)  # Cache for one day
def get_andhrajyothy_max_date():
    url = "https://epaper.andhrajyothy.com/Login/GetMaxDate"
    response = requests.get(url)
    if response.status_code == 200:
        data = json.loads(response.text)
        return data['maxdate']  # Assuming the date format is suitable for your needs
    else:
        print("Failed to fetch Andhrajyothy max date")
        return None

@cache.memoize(timeout=86400)  # Cache for one day
def get_vaartha_max_date():
    url = "https://epaper.vaartha.com/Login/GetMaxDate"
    response = requests.get(url)
    if response.status_code == 200:
        data = json.loads(response.text)
        return data['maxdate']  # Assuming the date format is suitable for your needs
    else:
        print("Failed to fetch Andhrajyothy max date")
        return None
    

@cache.memoize(timeout=86400)  # Cache for one day
def get_vaartha_edition_id(target_edition = "Khammam"):
    url = "https://epaper.vaartha.com/Home/GetEditionsHierarchy"
    response = requests.get(url)
    if response.status_code == 200:
        json_response = response.json()
        
        for entry in json_response:
            if "editionlocation" in entry:
                for edition in entry["editionlocation"]:
                    if "Editionlocation" in edition and edition["Editionlocation"] == target_edition:
                        return edition.get("EditionId")
        return None
    else:
        print(f"Error: Unable to fetch data from the URL. Status code: {response.status_code}")
        return None
    
@cache.memoize(timeout=86400)  # Cache for one day
def get_andhrajyothy_khammam_edition_id():
    url = "https://epaper.andhrajyothy.com/Home/GetEditionsForSearch"
    response = requests.get(url)
    if response.status_code == 200:
        editions = response.json()
        for edition in editions:
            if edition['EditionDisplayName'].lower() == "khammam":
                return edition['EditionId']
        print("Khammam edition not found")
    else:
        print("Failed to fetch editions")
    return None

@cache.memoize(timeout=86400)  # Cache for one day
def get_vaartha_pages(edition_id, date):
    # Adjust the date format if necessary
    formatted_date = datetime.strptime(date, '%d/%m/%Y').strftime('%d/%m/%Y')
    url = f"https://epaper.vaartha.com/Home/GetAllpages?editionid={edition_id}&editiondate={formatted_date}"
    response = requests.get(url)
    if response.status_code == 200:
        pages = json.loads(response.text)
        return sorted(pages, key=lambda x: int(x['PageNo']))
    else:
        print("Failed to fetch Andhrajyothy pages")
        return []
    
@cache.memoize(timeout=86400)
def vaartha_khammam_edition():
    # Fetch the max date for Andhra Jyothy or use the current date as fallback
    max_date = get_vaartha_max_date()
    print(max_date)
    edition_id = get_vaartha_edition_id()
    pages = get_vaartha_pages(edition_id,max_date)
    edition = transform_entry(pages[0])
    return edition

@cache.memoize(timeout=86400)  # Cache for one day
def get_andhrajyothy_pages(edition_id, date):
    # Adjust the date format if necessary
    formatted_date = datetime.strptime(date, '%d/%m/%Y').strftime('%d/%m/%Y')
    url = f"https://epaper.andhrajyothy.com/Home/GetAllpages?editionid={edition_id}&editiondate={formatted_date}"
    response = requests.get(url)
    if response.status_code == 200:
        pages = json.loads(response.text)
        return sorted(pages, key=lambda x: int(x['PageNo']))
    else:
        print("Failed to fetch Andhrajyothy pages")
        return []

def transform_entry(entry):
    transformed_entry = {
        'Path': entry['HighResolution'].replace("\\", "/"),  # Adjust the path format
        'EditionDate': entry['EditionDate'],  # Use the same edition date
        'EditionName': "Andhara Jyothi " + entry['EditionName'],  # Use the edition name directly
        'MobEditionName': entry['EditionName'],  # Assuming the same name for mobile edition name
        'editionID': int(entry['EditionID']),  # Convert EditionID to integer and use it
        'PageId': entry['PageId'],  # Use the same page ID
        'Date': entry['EditionDate'].replace("/", "-"),
        'Source': 'AndhraJyothi' # Adjust date format if necessary
    }
    
    return transformed_entry


@cache.memoize(timeout=86400)
def andhrajyothy_khammam_edition():
    # Fetch the max date for Andhra Jyothy or use the current date as fallback
    max_date = get_andhrajyothy_max_date()
    print(max_date)
    edition_id = get_andhrajyothy_khammam_edition_id()
    pages = get_andhrajyothy_pages(edition_id,max_date)
    edition = transform_entry(pages[0])
    return edition


@cache.memoize(timeout=86400)  # Cache for one day
def get_pages(date, edition_id):
    url = f"https://epaper.eenadu.net/Home/GetAllpages?editionid={edition_id}&editiondate={date}&IsMag=0"
    response = requests.get(url)
    pages = json.loads(response.text)
    return sorted(pages, key=lambda x: int(x['PageNo']))

@cache.memoize(timeout=86400)  # Cache for one day
def get_khammam_district_editions(date):
    url = f"https://epaper.eenadu.net/Login/GetDistrictEditionPages?DistrictEditionId=1&Date={date}"
    response = requests.get(url)
    if response.status_code == 200:
        district_editions = json.loads(response.text)
        khammam_edition = next((edition for edition in district_editions if edition["EditionName"] == "KHAMMAM"), None)
        return khammam_edition
    else:
        print("Failed to fetch district editions")
        return []

@cache.memoize(timeout=86400)  # Cache for one day
def get_editions(date):
    # Get the main editions
    url = f"https://epaper.eenadu.net/Login/GetMailEditionPages?Date={date}"
    response = requests.get(url)
    if response.status_code == 200:
        editions = json.loads(response.text)
    else:
        print("Failed to fetch main editions")
        return []

    # Get the district editions
    khammam_edition = get_khammam_district_editions(date)
    aj_khammam_edition = andhrajyothy_khammam_edition()
    v_khammam_edition = vaartha_khammam_edition()

    # If Khammam edition is found, add it to the main editions list
    if khammam_edition:
        editions.append(khammam_edition)

    eenadu_editions = [edition['editionID'] for edition in editions]  # Store only the editionID

    global all_editions
    all_editions = {'eenadu': eenadu_editions}
    

    if aj_khammam_edition:
        all_editions['andhrajyothy'] = aj_khammam_edition['editionID']
        editions.append(aj_khammam_edition)

    if v_khammam_edition:
        all_editions['vaartha'] = v_khammam_edition['editionID']
        editions.append(v_khammam_edition)
    return editions

@app.route('/', methods=['GET'])
def landing():
    max_date = get_max_date()
    editions = get_editions(max_date)
    return render_template('landing.html', editions=editions)

@app.route('/edition/<int:edition_id>', methods=['GET', 'POST'])
def edition(edition_id):
    max_date = get_max_date()
    if edition_id in all_editions['eenadu']:
        pages = get_pages(max_date, edition_id)
    elif edition_id == all_editions['andhrajyothy']:
        pages = get_andhrajyothy_pages(edition_id, max_date)
    elif edition_id == all_editions['vaartha']:
        pages = get_vaartha_pages(edition_id, max_date)
    if not pages:
        return "No pages found."
    current_page_index = 0
    if request.method == 'POST':
        if 'next' in request.form:
            current_page_index = int(request.form['current_page_index']) + 1
        elif 'previous' in request.form:
            current_page_index = int(request.form['current_page_index']) - 1
    current_page_index = max(0, min(current_page_index, len(pages) - 1))
    current_page = pages[current_page_index]
    xhighres_image_url = current_page['XHighResolution']
    overlay_image_url = xhighres_image_url.replace('.jpg', '.png')
    return render_template('edition.html', overlay_image_url=overlay_image_url, xhighres_image_url=xhighres_image_url, current_page_index=current_page_index, total_pages=len(pages))

if __name__ == '__main__':
    app.run(debug=True)