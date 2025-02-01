import app.download_covers as download_covers
from app.functions import sqlalchemy_fns as sqlalchemy_fns
from flask import Flask, render_template, jsonify, request, url_for, redirect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import json
from app.config import is_development_mode, fastapi_updater_server_IP
import os
import requests
from app.config import Config
from app.functions import class_mangalist
from datetime import timedelta, datetime
from app.functions.class_mangalist import db_session
from bs4 import BeautifulSoup
from urllib.parse import unquote  # To decode URL-encoded characters
import logging
from app.functions.manga_updates_fns import MangaUpdatesAPI
from app.functions.sqlalchemy_fns import save_manga_details
from scrapy.crawler import CrawlerRunner
from crochet import setup, wait_for, run_in_reactor
from app.functions.sqlalchemy_fns import update_manga_links, save_manga_details
from app.functions.manga_updates_spider import MangaUpdatesSpider
import re


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Setup for Scrapy to work asynchronously with Flask
setup()

app = Flask(__name__)
app.secret_key = Config.flask_secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # Or 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

Users = class_mangalist.Users

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized_callback():
    return jsonify({'error': 'Unauthorized access'}), 401

@app.route('/login', methods=['POST'])
def login():
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = Users.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=True)
                db_session.commit()
                return jsonify({'success': True}), 200
            else:
                return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    except Exception as e:
        db_session.rollback()
        raise e



@app.route('/logout')
def logout():
    logout_user()  # Flask-Login's logout function
    return redirect(url_for('home'))

@app.context_processor
def inject_debug():
    # Directly print out the FLASK_ENV variable
    print("FLASK_ENV: ", os.getenv('FLASK_ENV'))
    # Get the current time
    now = datetime.now()
    # Subtract one hour
    if is_development_mode == "production":
        time_of_load = now - timedelta(hours=1) # my vps is -1 hour to my local time
    else:
        time_of_load = now
    # Print the time
    print("Time of the page load: ", time_of_load)
    # printing in what mode the program is runned
    #print("isDevelopment?: ", is_development_mode.DEBUG)
    return dict(isDevelopment=is_development_mode.DEBUG)

# Ensure this is only set for development
app.config['DEBUG'] = bool(is_development_mode.DEBUG)

@app.after_request
def set_security_headers(response):
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com https://cdn.jsdelivr.net/npm; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdnjs.cloudflare.com;"
    )

    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = csp_policy
    return response



# Route for your home page
@app.route('/')
def home():  
   
    manga_entries = sqlalchemy_fns.get_manga_list_alchemy()
    mangaupdates_details = sqlalchemy_fns.get_manga_details_alchemy()
    
    
    # Identify entries with missing covers and download them
    ids_to_download = [entry['id_anilist'] for entry in manga_entries if not entry['is_cover_downloaded']]
    
    if ids_to_download:
        try:
            successful_ids = download_covers.download_covers_concurrently(ids_to_download, manga_entries)
            # Bulk update the database to mark the covers as downloaded only for successful ones
            if successful_ids:
                sqlalchemy_fns.update_cover_download_status_bulk(successful_ids, True)
        except Exception as e:
            print(f"Error during download or database update: {e}")


    #print(manga_entries)
    for entry in manga_entries:
        links = entry.get('external_links', '[]')  # Default to an empty JSON array as a string
        genres = entry.get('genres', '[]')
        # Check if links is a valid JSON array
        title_english = entry.get('title_english')
        title_romaji = entry.get('title_romaji')
       
        try:
            json.loads(links)
            json.loads(genres)
        except json.JSONDecodeError:
            entry['external_links'] = []  # Replace with an empty list or another suitable default
            entry['genres'] = []
        if title_english == "None":
            title_english = title_romaji
            entry['title_english'] = title_romaji  # Don't forget to update the entry dict as well

    # Load user-specific color settings
    color_settings = load_color_settings()
    
    # Pass the entries and color settings to the template.
    return render_template('index.html', manga_entries=manga_entries, mangaupdates_details=mangaupdates_details, color_settings=color_settings)


# Route for handling the log sync functionality
@app.route('/log_sync', methods=['POST'])
def log_sync():
    print('Sync successful')  # Print message to console
    return '', 204  # Return an empty response


@app.route('/sync', methods=['POST'])
@login_required
def sync_with_fastapi():
    try:
        # Replace the URL with your actual FastAPI server address
        url = f"http://{fastapi_updater_server_IP}:8057/sync"
        print(f"Connecting to FastAPI at: {url}")
        response = requests.post(url, timeout=10)

        if response.status_code == 200:
            # Assuming the FastAPI response is JSON and includes a status
            return jsonify({
                "status": "success",
                "message": "Synced successfully with FastAPI",
                "fastapi_response": response.json()  # Include FastAPI response if needed
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to sync with FastAPI"
            }), 500
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"An error occurred while connecting to FastAPI: {str(e)}",
                }
            ),
            500,
        )


#  anilist_id = data.get('anilistId')
# (MangaUpdatesSpider, bato_link=bato_link, anilist_id=anilist_id)

def extract_links_from_bato(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_links = []
    
    # Try multiple potential locations for links
    # 1. Try finding all limit-html-p divs
    limit_html_p_divs = soup.find_all('div', class_='limit-html-p')
    for div in limit_html_p_divs:
        # Get all links in this div
        links = div.find_all('a', attrs={'data-trust': '0'})
        for link in links:
            url = link.text.strip()
            if url.startswith('http'):
                extracted_links.append(url)
                logging.info(f"Found link in limit-html-p div: {url}")

    # 2. Try finding links in any div with class containing 'limit-html'
    if not extracted_links:
        limit_html_divs = soup.find_all('div', class_=lambda x: x and 'limit-html' in x)
        for div in limit_html_divs:
            links = div.find_all('a')
            for link in links:
                url = link.get('href') or link.text.strip()
                if url and url.startswith('http'):
                    extracted_links.append(url)
                    logging.info(f"Found link in limit-html div: {url}")

    # 3. Look for any text that contains mangaupdates.com
    text_nodes = soup.find_all(text=True)
    for text in text_nodes:
        if 'mangaupdates.com' in text:
            # Try to extract URL using regex
            urls = re.findall(r'https?://(?:www\.)?mangaupdates\.com[^\s<>"\']+', text)
            for url in urls:
                if url not in extracted_links:  # Prevent duplicates
                    extracted_links.append(url)
                    logging.info(f"Found MangaUpdates link in text: {url}")

    # Log the results
    if extracted_links:
        logging.info(f"Successfully extracted {len(extracted_links)} links")
    else:
        logging.warning("No links were extracted from the Bato page")
        logging.debug("Page structure:")
        logging.debug(soup.prettify()[:1000])  # Log first 1000 chars of the HTML structure

    return extracted_links

@app.route('/add_bato', methods=['POST'])
@login_required
def add_bato_link_route():
    try:
        data = request.get_json()
        anilist_id = data.get('anilistId')
        input_link = data.get('batoLink')
        series_name = data.get('seriesname')

        logging.info(f"Processing link for {series_name} (AniList ID: {anilist_id})")
        logging.info(f"Input Link: {input_link}")

        # Check if it's a MangaUpdates link
        if 'mangaupdates' in input_link.lower():
            logging.info("MangaUpdates link detected, processing directly")
            # Store the MangaUpdates link in external_links
            sqlalchemy_fns.update_manga_links(anilist_id, None, [input_link])
            
            # Run the spider directly
            result = run_crawl(input_link, anilist_id)
            if not result:
                logging.warning("Failed to complete MangaUpdates crawl")
                return jsonify({
                    "status": "partial_success",
                    "message": "MangaUpdates link saved but failed to retrieve data",
                }), 200

            return jsonify({
                "status": "success",
                "message": "MangaUpdates link added and data retrieved successfully",
                "extractedLinks": [input_link]
            }), 200

        # If it's not a MangaUpdates link, process as Bato link
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Fetch the Bato page
        response = requests.get(input_link, headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to fetch page, status code: {response.status_code}")
            return jsonify({"status": "error", "message": "Failed to fetch data."}), 500

        # Log the response content type and length
        logging.info(f"Response Content-Type: {response.headers.get('content-type')}")
        logging.info(f"Response Length: {len(response.text)} bytes")

        # Extract links from Bato page
        extracted_links = extract_links_from_bato(response.text)
        logging.info(f"Extracted Links: {extracted_links}")

        # Update the database with the Bato link and any extracted links
        sqlalchemy_fns.update_manga_links(anilist_id, input_link, extracted_links)

        # Look for the MangaUpdates link
        mangaupdates_link = None
        for link in extracted_links:
            if 'mangaupdates.com' in link.lower():
                mangaupdates_link = link
                logging.info(f"Found MangaUpdates link: {link}")
                break

        # If MangaUpdates link is found, run the spider
        if mangaupdates_link:
            logging.info(f"Running crawler for MangaUpdates link: {mangaupdates_link}")
            result = run_crawl(mangaupdates_link, anilist_id)
            if not result:
                logging.warning("Failed to complete MangaUpdates crawl, but continuing...")

        return jsonify({
            "status": "success",
            "message": "Bato link added successfully" + 
                      (" and MangaUpdates data retrieved" if mangaupdates_link else ", but no MangaUpdates link found"),
            "extractedLinks": extracted_links
        }), 200

    except Exception as e:
        logging.exception("An error occurred during the link extraction process:")
        return jsonify({"status": "error", "message": str(e)}), 500


@run_in_reactor
def run_crawl(start_url, anilist_id):
    runner = CrawlerRunner()
    deferred = runner.crawl(MangaUpdatesSpider, start_url=start_url, anilist_id=anilist_id)
    
    def on_success(result):
        logging.info("Crawl completed successfully.")
        return result

    def on_failure(failure):
        logging.error(f"Crawl failed: {failure.getErrorMessage()}")
        return None

    deferred.addCallback(on_success)
    deferred.addErrback(on_failure)
    
    return deferred

@app.route('/save_color_settings', methods=['POST'])
@login_required
def save_color_settings():
    try:
        data = request.get_json()
        user_id = current_user.id

        # Load current settings
        current_settings = load_color_settings()

        # Update current settings with new values, keeping others intact
        color_settings = {
            'background_color': data.get('backgroundColor', current_settings.get('background_color')),
            'primary_color': data.get('primaryColor', current_settings.get('primary_color')),
            'secondary_color': data.get('secondaryColor', current_settings.get('secondary_color')),
            'text_color': data.get('textColor', current_settings.get('text_color')),
            'border_color': data.get('borderColor', current_settings.get('border_color'))
        }

        save_user_color_settings(user_id, color_settings)
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.exception("An error occurred while saving color settings.")
        return jsonify({'success': False, 'message': 'Failed to save color settings.'}), 500

def save_user_color_settings(user_id, color_settings):
    # Create directory if it doesn't exist
    settings_dir = os.path.join('app', 'user_settings')
    os.makedirs(settings_dir, exist_ok=True)
    
    # Save the color settings to a file or database
    settings_path = os.path.join(settings_dir, f'user_color_settings_{user_id}.json')
    with open(settings_path, 'w') as f:
        json.dump(color_settings, f)

def load_color_settings():
    user_id = current_user.id if current_user.is_authenticated else 'default'
    settings_dir = os.path.join('app', 'user_settings')
    settings_path = os.path.join(settings_dir, f'user_color_settings_{user_id}.json')
    
    try:
        with open(settings_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Use default color settings if the file is missing
        default_settings = {
            'background_color': '#24282d',
            'primary_color': '#007bff',
            'secondary_color': '#343a40',
            'text_color': '#ffffff',
            'border_color': '#3e3e3e'
        }
        # Save these defaults if no settings file exists
        save_user_color_settings(user_id, default_settings)
        return default_settings

@app.route('/get_color_settings', methods=['GET'])
@login_required
def get_color_settings():
    settings = load_color_settings()
    print("Loaded color settings from JSON:", settings)  # Debug statement
    response_settings = {
        'backgroundColor': settings.get('background_color'),
        'primaryColor': settings.get('primary_color'),
        'secondaryColor': settings.get('secondary_color'),
        'textColor': settings.get('text_color'),
        'borderColor': settings.get('border_color')
    }
    print("Sending color settings to frontend:", response_settings)  # Debug statement
    return jsonify(response_settings)




@app.teardown_appcontext
def cleanup(resp_or_exc):
    db_session.remove()



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




# Ensure this function is accessible in your templates

# THEN IN HTML: 
#<div class="score-icon" style="background-color: {{ score_to_color(entry.score) }}" title="Score: {{ entry.score }}">
  #      {{ entry.score }}
#  <div>

# def count_stats(counting_element):
#     """'counting_element' can be user status, entry detailes lile chapters volumes etc. ."""
#     user_completed = 0
#     user_planning = 0 
#     user_current = 0 
#     user_paused = 0 
#     manga_entries = mariadb_functions.get_manga_list(current_app.config)
#     for entry in manga_entries:
#         if entry.get('on_list_status') == "COMPLETED":
#             user_completed += 1
#         elif entry.get('on_list_status') == "PLANNING":
#             user_planning += 1
#         elif entry.get('on_list_status') == "CURRENT":
#             user_current += 1
#         elif entry.get('on_list_status') == "PAUSED":
#             user_paused += 1
#     return user_completed, user_planning, user_current, user_paused


# @app.context_processor
# def utility_processor():
#     return dict(count_stats=count_stats)
