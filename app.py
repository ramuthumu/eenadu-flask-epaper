from flask import Flask, render_template, request
from flask_caching import Cache
import requests
import json
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Set up caching
app.config['CACHE_TYPE'] = 'filesystem'
app.config['CACHE_DIR'] = 'cache_directory'
cache = Cache(app)


@cache.memoize(60 * 60 * 24)  # Cache the results for 24 hours
def get_max_date():
    url = "https://epaper.eenadu.net/Home/GetMaxdateJson"
    response = requests.get(url)
    return response.text.strip('\"')


def fetch_data(url):
    response = requests.get(url)
    return json.loads(response.text)


@cache.cached(timeout=60 * 60 * 24, cache_none=False,
              key_prefix=lambda: f"pages_{request.args.get('date', '')}_{request.view_args['edition_id']}")
def get_pages(date, edition_id):
    url = f"https://epaper.eenadu.net/Home/GetAllpages?editionid={edition_id}&editiondate={date}&IsMag=0"

    with ThreadPoolExecutor() as executor:
        pages = executor.submit(fetch_data, url).result()

    return sorted(pages, key=lambda x: int(x['PageNo']))


@cache.cached(timeout=60 * 60 * 24, cache_none=False, key_prefix=lambda: f"editions_{request.args.get('date', '')}")
def get_editions(date):
    url = f"https://epaper.eenadu.net/Login/GetMailEditionPages?Date={date}"

    with ThreadPoolExecutor() as executor:
        editions = executor.submit(fetch_data, url).result()

    return editions


@app.route('/', methods=['GET'])
def landing():
    max_date = get_max_date()
    editions = get_editions(max_date)
    editions_json = json.dumps(editions)
    return render_template('landing.html', editions_json=editions_json)


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
        elif 'go_to_page' in request.form:
            current_page_index = int(request.form['page_select'])

    current_page_index = max(0, min(current_page_index, len(pages) - 1))
    current_page = pages[current_page_index]
    xhighres_image_url = current_page['XHighResolution']
    overlay_image_url = xhighres_image_url.replace('.jpg', '.png')

    return render_template('edition.html', overlay_image_url=overlay_image_url, xhighres_image_url=xhighres_image_url,
                           current_page_index=current_page_index, total_pages=len(pages))


if __name__ == '__main__':
    app.run(debug=False)