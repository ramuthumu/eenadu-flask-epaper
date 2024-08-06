from datetime import datetime
from flask import Flask, render_template, request
from flask_caching import Cache
import requests
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'content-type': 'application/json; charset=utf-8',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://epaper.eenadu.net/',
    'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'x-requested-with': 'XMLHttpRequest'
}

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
def get_max_date_from_url(url, json_key=None):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # This will raise an exception for 4XX and 5XX responses

        if json_key:
            # If a JSON key is provided, parse the JSON and return the value associated with the key
            data = response.json()
            return data.get(json_key)
        else:
            # If no JSON key is provided, return the raw text response
            return response.text.strip('\"')
    except Exception as e:
        print(f"Failed to fetch date from {url}: {e}")
        return None


# Usage examples
def get_max_date_json():
    return get_max_date_from_url("https://epaper.eenadu.net/Home/GetMaxdateJson")


def get_max_date(name):
    return get_max_date_from_url(f"https://epaper.{name}.com/Login/GetMaxDate", "maxdate")


@cache.memoize(timeout=86400)  # Cache for one day
def get_edition_id(name, target_edition="Khammam"):
    url = f"https://epaper.{name}.com/Home/GetEditionsHierarchy"
    response = requests.get(url,timeout=10)
    if response.status_code == 200:
        json_response = response.json()

        for entry in json_response:
            if "editionlocation" in entry:
                for edition in entry["editionlocation"]:
                    if "Editionlocation" in edition and edition["Editionlocation"].strip() == target_edition:
                        return edition.get("EditionId")
        return None
    else:
        print(f"Error: Unable to fetch data from the URL. Status code: {response.status_code}")
        return None


@cache.memoize(timeout=86400)
def get_khammam_edition(name, supplement=None, target_edition='Khammam'):
    try:
        # Fetch the max date for Andhra Jyothy or use the current date as fallback
        max_date = get_max_date(name=name)
        print(max_date)
        if supplement:
            edition_id = str(int(get_edition_id(name=name)) + 1)
        else:
            edition_id = get_edition_id(name=name, target_edition=target_edition)
        print(name, edition_id, target_edition)
        pages = get_pages(name=name, edition_id=edition_id, max_date=max_date)
        edition = transform_entry(pages[0], name)
        return edition
    except Exception as e:
        print(f"Error occurred while fetching {name} edition: {e}")
        return None


@cache.memoize(timeout=86400)  # Cache for one day
def get_pages(name, edition_id, max_date):
    # Adjust the date format if necessary
    formatted_date = datetime.strptime(max_date, '%d/%m/%Y').strftime('%d/%m/%Y')
    url = f"https://epaper.{name}.com/Home/GetAllpages?editionid={edition_id}&editiondate={formatted_date}"
    response = requests.get(url,timeout=10)
    if response.status_code == 200:
        pages = json.loads(response.text)
        return sorted(pages, key=lambda x: int(x['PageNo']))
    else:
        print("Failed to fetch Andhrajyothy pages")
        return []


def transform_entry(entry, papername):
    transformed_entry = {
        'Path': entry['HighResolution'].replace("\\", "/"),  # Adjust the path format
        'EditionDate': entry['EditionDate'],  # Use the same edition date
        'EditionName': papername + ' ' + entry['EditionName'],  # Use the edition name directly
        'MobEditionName': entry['EditionName'],  # Assuming the same name for mobile edition name
        'editionID': int(entry['EditionID']),  # Convert EditionID to integer and use it
        'PageId': entry['PageId'],  # Use the same page ID
        'Date': entry['EditionDate'].replace("/", "-"),
        'Source': papername  # Adjust date format if necessary
    }

    return transformed_entry


@cache.memoize(timeout=86400)  # Cache for one day
def get_eenadu_pages(date, edition_id):
    url = f"https://epaper.eenadu.net/Home/GetAllpages?editionid={edition_id}&editiondate={date}&IsMag=0"
    response = requests.get(url,timeout=10)
    pages = json.loads(response.text)
    return sorted(pages, key=lambda x: int(x['PageNo']))


@cache.memoize(timeout=86400)  # Cache for one day
def get_eenadu_khammam_district_editions(date):
    url = f"https://epaper.eenadu.net/Login/GetDistrictEditionPages?DistrictEditionId=1&Date={date}"
    response = requests.get(url,timeout=10)
    if response.status_code == 200:
        district_editions = json.loads(response.text)
        khammam_edition = next((edition for edition in district_editions if edition["EditionName"] == "KHAMMAM"), None)
        khammam_edition['Source'] = 'eenadu'
        return khammam_edition
    else:
        print("Failed to fetch district editions")
        return []


@cache.memoize(timeout=86400)  # Cache for one day
def get_editions(date):
    # Get the main editions
    url = f"https://epaper.eenadu.net/Login/GetMailEditionPages?Date={date}"
    response = requests.get(url,timeout=10)
    if response.status_code == 200:
        editions = json.loads(response.text)
        for edition in editions:
            edition['Source'] = 'eenadu'
    else:
        print("Failed to fetch main editions")
        return []

    # Get the district editions
    khammam_edition = get_eenadu_khammam_district_editions(date)
    aj_khammam_edition = get_khammam_edition(name='andhrajyothy', target_edition="Khammam")
    v_khammam_edition = get_khammam_edition(name='vaartha', target_edition="Khammam")

    aprabha_khammam_edition = get_khammam_edition(name='prabhanews', target_edition="Khammam")
    aprabha_telangana_edition = get_khammam_edition(name='prabhanews', target_edition='Telangana')

    v_khammam_zilla_edition = get_khammam_edition(name='vaartha', supplement=True)
    a_khammam_zilla_edition = get_khammam_edition(name='andhrajyothy', supplement=True)

    # If Khammam edition is found, add it to the main editions list
    if khammam_edition:
        editions.append(khammam_edition)

    if aj_khammam_edition:
        editions.append(aj_khammam_edition)
        editions.append(a_khammam_zilla_edition)

    if v_khammam_edition:
        editions.append(v_khammam_edition)
        editions.append(v_khammam_zilla_edition)

    if aprabha_khammam_edition:
        editions.append(aprabha_khammam_edition)
        editions.append(aprabha_telangana_edition)

    return editions


@app.route('/', methods=['GET'])
def landing():
    max_date = get_max_date_json()
    editions = get_editions(max_date)
    return render_template('landing.html', editions=editions)


@app.route('/edition/<string:edition_name>/<int:edition_id>', methods=['GET', 'POST'])
def edition(edition_name, edition_id):
    max_date = get_max_date_json()
    if not all_editions:
        get_editions(max_date)
    if edition_name == 'eenadu':
        pages = get_eenadu_pages(max_date, edition_id)
    else:
        pages = get_pages(name=edition_name, edition_id=edition_id, max_date=get_max_date(name=edition_name))
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
    return render_template('edition.html', overlay_image_url=overlay_image_url, xhighres_image_url=xhighres_image_url,
                           current_page_index=current_page_index, total_pages=len(pages))


if __name__ == '__main__':
    app.run(debug=True)
