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

# Configure APScheduler
scheduler = BackgroundScheduler()

def clear_cache():
    with app.app_context():
        cache.clear()
        print("Cache cleared.")

# Schedule cache to be cleared every day at 5 PM and 6 PM
scheduler.add_job(func=clear_cache, trigger='cron', hour='17,18')
scheduler.start()

# Ensure the scheduler is shut down when the app exits
atexit.register(lambda: scheduler.shutdown())

@cache.memoize(timeout=86400)  # Cache for one day
def get_max_date():
    url = "https://epaper.eenadu.net/Home/GetMaxdateJson"
    response = requests.get(url)
    return response.text.strip('\"')

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
    # If Khammam edition is found, add it to the main editions list
    if khammam_edition:
        editions.append(khammam_edition)
    return editions

@app.route('/', methods=['GET'])
def landing():
    max_date = get_max_date()
    editions = get_editions(max_date)
    return render_template('landing.html', editions=editions)

@app.route('/edition/<int:edition_id>', methods=['GET', 'POST'])
def edition(edition_id):
    max_date = get_max_date()
    pages = get_pages(max_date, edition_id)
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
