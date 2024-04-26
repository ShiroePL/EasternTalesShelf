import app.download_covers as download_covers
from app.functions import sqlalchemy_fns as sqlalchemy_fns
from flask import Flask, render_template, jsonify, request, url_for, redirect
from flask_login import LoginManager, login_user, login_required, logout_user
import json
from app.config import is_development_mode, fastapi_updater_server_IP
import os
import requests
from app.config import Config
from app.functions import class_mangalist
from datetime import timedelta, datetime
from app.functions.class_mangalist import  db_session
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote  # To decode URL-encoded characters


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

    
    # Pass the entries to the template.
    return render_template('index.html', manga_entries=manga_entries)


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


ALLOWED_DOMAINS = {
    "bato.to", "dto.to", "fto.to", "jto.to", "hto.to", "mto.to", "wto.to",
    "batotoo.com", "battwo.com", "comiko.net", "mangatoto.com", "mangatoto.net",
    "mangatoto.org", "batotwo.com", "comiko.org", "batocomic.com", "batocomic.net",
    "batocomic.org", "readtoto.com", "readtoto.net", "readtoto.org",
    "xbato.com", "xbato.net", "xbato.org", "zbato.com", "zbato.net", "zbato.org"
}

@app.route('/add_bato', methods=['POST'])
@login_required
def add_bato_link_route():
def add_bato_link_route():
    try:
        data = request.get_json()
        anilist_id = data.get('anilistId')
        bato_link = data.get('batoLink')

        # Validate the URL
        parsed_url = urlparse(bato_link)
        domain = parsed_url.netloc

        if not any(
            domain == valid_domain or domain.endswith(f'.{valid_domain}')
            for valid_domain in ALLOWED_DOMAINS
        ):
            return jsonify({"status": "error", "message": "Invalid domain."}), 400

        # Scrape the Batoto page
        response = requests.get(bato_link)
        if response.status_code != 200:
            return jsonify({"status": "error", "message": "Failed to fetch data."}), 500

        soup = BeautifulSoup(response.text, 'html.parser')
        astro_islands = soup.find_all('astro-island')
        extracted_links = []
        for island in astro_islands:
            if 'Display_Text_ResInfo' in island['opts']:
                props = json.loads(island['props'].replace('&quot;', '"'))
                if links_str := props.get('code', [None, None])[1]:
                    # Split links and clean them
                    links = links_str.split('\n')
                    cleaned_links = [link.split('] ')[-1].strip() for link in links if '] ' in link]
                    # Decode any percent-encoded characters in the URL
                    cleaned_links = [unquote(link) for link in cleaned_links]
                    # Filter out non-ASCII links
                    ascii_links = [link for link in cleaned_links if link.isascii()]
                    extracted_links.extend(ascii_links)

        # Update the database with the new links
        sqlalchemy_fns.update_manga_links(anilist_id, bato_link, extracted_links)
        return jsonify({"message": "Manga links updated successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

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