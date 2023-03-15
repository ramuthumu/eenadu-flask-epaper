from flask import Flask, render_template, request
import requests
import json

app = Flask(__name__)

def get_max_date():
    url = "https://epaper.eenadu.net/Home/GetMaxdateJson"
    response = requests.get(url)
    print(response.text)
    return response.text

def get_pages(date):
    date = date.strip('\"')
    url = f"https://epaper.eenadu.net/Home/GetAllpages?editionid=3&editiondate={date}&IsMag=0"
    print(url)
    response = requests.get(url)
    pages = json.loads(response.text)
    return sorted(pages, key=lambda x: int(x['PageNo']))

@app.route('/', methods=['GET', 'POST'])
def index():
    max_date = get_max_date()
    pages = get_pages(max_date)

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

    return render_template('index.html', overlay_image_url=overlay_image_url, xhighres_image_url=xhighres_image_url, current_page_index=current_page_index, total_pages=len(pages))

if __name__ == '__main__':
    app.run(debug=True)

