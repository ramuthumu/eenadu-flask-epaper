from flask import Flask, render_template, request
import requests
import json

app = Flask(__name__)

def get_max_date():
    url = "https://epaper.eenadu.net/Home/GetMaxdateJson"
    response = requests.get(url)
    return response.text.strip('\"')

def get_pages(date, edition_id):
    url = f"https://epaper.eenadu.net/Home/GetAllpages?editionid={edition_id}&editiondate={date}&IsMag=0"
    response = requests.get(url)
    pages = json.loads(response.text)
    return sorted(pages, key=lambda x: int(x['PageNo']))

def get_khammam_district_editions(date):
    url = f"https://epaper.eenadu.net/Login/GetDistrictEditionPages?DistrictEditionId=1&Date={date}"
    response = requests.get(url)
    if response.status_code == 200:
        district_editions = json.loads(response.text)
        # Find the Khammam edition in the district editions
        khammam_edition = next((edition for edition in district_editions if edition["EditionName"] == "KHAMMAM"), None)
        return khammam_edition
    else:
        print("Failed to fetch district editions")
        return []

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