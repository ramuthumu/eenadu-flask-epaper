from datetime import datetime
from flask import Flask, jsonify, request
from flask_caching import Cache
from flask_cors import CORS
import requests
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure cache
app.config['CACHE_TYPE'] = 'SimpleCache'
cache = Cache(app)
cache.init_app(app)

# Configure APScheduler
scheduler = BackgroundScheduler()


def clear_cache():
    with app.app_context():
        cache.clear()
        print("Cache cleared.")


scheduler.add_job(func=clear_cache, trigger='cron', hour='16,17,18')
scheduler.start()

atexit.register(lambda: scheduler.shutdown())


@cache.memoize(timeout=86400)
def get_max_date_from_url(url, json_key=None):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        if json_key:
            data = response.json()
            return data.get(json_key)
        else:
            return response.text.strip('\"')
    except Exception as e:
        print(f"Failed to fetch date from {url}: {e}")
        return None


def get_max_date_json():
    return get_max_date_from_url("https://epaper.eenadu.net/Home/GetMaxdateJson")


def get_max_date(name):
    return get_max_date_from_url(f"https://epaper.{name}.com/Login/GetMaxDate", "maxdate")


@cache.memoize(timeout=86400)
def get_edition_id(name, target_edition="Khammam"):
    url = f"https://epaper.{name}.com/Home/GetEditionsHierarchy"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        json_response = response.json()
        for entry in json_response:
            if "editionlocation" in entry:
                for edition in entry["editionlocation"]:
                    if "Editionlocation" in edition and edition["Editionlocation"].strip() == target_edition:
                        return edition.get("EditionId")
        return None
    except Exception as e:
        print(f"Error: Unable to fetch data from {url}. Error: {e}")
        return None


@cache.memoize(timeout=86400)
def get_khammam_edition(name, supplement=None, target_edition='Khammam'):
    try:
        max_date = get_max_date(name=name)
        if supplement:
            edition_id = str(int(get_edition_id(name=name)) + 1)
        else:
            edition_id = get_edition_id(name=name, target_edition=target_edition)
        pages = get_pages(name=name, edition_id=edition_id, max_date=max_date)
        edition = transform_entry(pages[0], name)
        return edition
    except Exception as e:
        print(f"Error occurred while fetching {name} edition: {e}")
        return None


@cache.memoize(timeout=86400)
def get_pages(name, edition_id, max_date):
    formatted_date = datetime.strptime(max_date, '%d/%m/%Y').strftime('%d/%m/%Y')
    url = f"https://epaper.{name}.com/Home/GetAllpages?editionid={edition_id}&editiondate={formatted_date}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        pages = response.json()
        return sorted(pages, key=lambda x: int(x['PageNo']))
    except Exception as e:
        print(f"Failed to fetch {name} pages: {e}")
        return []


def transform_entry(entry, papername):
    return {
        'Path': entry['HighResolution'].replace("\\", "/"),
        'EditionDate': entry['EditionDate'],
        'EditionName': f"{papername} {entry['EditionName']}",
        'MobEditionName': entry['EditionName'],
        'editionID': int(entry['EditionID']),
        'PageId': entry['PageId'],
        'Date': entry['EditionDate'].replace("/", "-"),
        'Source': papername
    }


@cache.memoize(timeout=86400)
def get_eenadu_pages(date, edition_id):
    url = f"https://epaper.eenadu.net/Home/GetAllpages?editionid={edition_id}&editiondate={date}&IsMag=0"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        pages = response.json()
        return sorted(pages, key=lambda x: int(x['PageNo']))
    except Exception as e:
        print(f"Failed to fetch Eenadu pages: {e}")
        return []


@cache.memoize(timeout=86400)
def get_eenadu_khammam_district_editions(date):
    url = f"https://epaper.eenadu.net/Login/GetDistrictEditionPages?DistrictEditionId=1&Date={date}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        district_editions = response.json()
        khammam_edition = next((edition for edition in district_editions if edition["EditionName"] == "KHAMMAM"), None)
        if khammam_edition:
            khammam_edition['Source'] = 'eenadu'
        return khammam_edition
    except Exception as e:
        print(f"Failed to fetch district editions: {e}")
        return None


@cache.memoize(timeout=86400)
def get_editions(date):
    url = f"https://epaper.eenadu.net/Login/GetMailEditionPages?Date={date}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        editions = response.json()
        for edition in editions:
            edition['Source'] = 'eenadu'
    except Exception as e:
        print(f"Failed to fetch main editions: {e}")
        editions = []

    khammam_edition = get_eenadu_khammam_district_editions(date)
    aj_khammam_edition = get_khammam_edition(name='andhrajyothy', target_edition="Khammam")
    v_khammam_edition = get_khammam_edition(name='vaartha', target_edition="Khammam")
    aprabha_khammam_edition = get_khammam_edition(name='prabhanews', target_edition="Khammam")
    aprabha_telangana_edition = get_khammam_edition(name='prabhanews', target_edition='Telangana')
    v_khammam_zilla_edition = get_khammam_edition(name='vaartha', supplement=True)
    a_khammam_zilla_edition = get_khammam_edition(name='andhrajyothy', supplement=True)

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


@app.route('/editions', methods=['GET'])
def get_all_editions():
    max_date = get_max_date_json()
    editions = get_editions(max_date)
    return jsonify(editions)


@app.route('/edition/<string:edition_name>/<int:edition_id>', methods=['GET'])
def get_edition_pages(edition_name, edition_id):
    max_date = get_max_date_json()
    if edition_name == 'eenadu':
        pages = get_eenadu_pages(max_date, edition_id)
    else:
        pages = get_pages(name=edition_name, edition_id=edition_id, max_date=get_max_date(name=edition_name))
    if not pages:
        return jsonify({"error": "No pages found"}), 404

    return jsonify(pages)


@app.route('/', methods=['GET'])
def landing():
    return jsonify({"message": "Welcome to the ePaper API"})


if __name__ == '__main__':
    app.run(debug=True)
