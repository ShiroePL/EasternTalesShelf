import app.download_covers as download_covers
from app.functions import sqlalchemy_fns as sqlalchemy_fns
from flask import Flask, render_template, jsonify, request, url_for, redirect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import json
from app.config import fastapi_updater_server_IP
import os
import requests
from app.config import Config
from app.functions import class_mangalist
from datetime import timedelta, datetime
from app.functions.class_mangalist import db_session, MangaList, MangaUpdatesDetails
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
from threading import Thread, Lock
from app.services.mangaupdates_update_service import start_update_service
from app.functions.class_mangalist import MangaStatusNotification
from dataclasses import dataclass
from typing import Optional
import time
from app.models.scraper_models import ScrapeQueue
from flask_socketio import SocketIO
from engineio.async_drivers import gevent
import secrets
import hashlib
from app.background_tasks import BackgroundTaskManager
from app.services.anilist_notification import AnilistNotificationManager
import asyncio
from app.functions.class_mangalist import MangaStatusNotification, AnilistNotification
from sqlalchemy import text


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Setup for Scrapy to work asynchronously with Flask
setup()

async def handle_new_notifications(notifications):
    """Handle new notifications from AniList"""
    print(f"Got {len(notifications)} new notifications!")
    # Here you could emit via websocket, store in database, etc.

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.secret_key = Config.flask_secret_key
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
    
    

    with app.app_context():
        # Initialize notification manager and background tasks
        global notification_manager, background_manager
        notification_manager = AnilistNotificationManager()
        background_manager = BackgroundTaskManager()
        
        # Create a thread to run the background tasks
        def run_background_tasks():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start the background polling
            background_manager.start_polling(
                notification_manager,
                interval=3600,  # Check every hour
                callback=handle_new_notifications
            )
            
            # Run the event loop
            loop.run_forever()
        
        # Start background tasks in a separate thread
        background_thread = Thread(target=run_background_tasks, daemon=True)
        background_thread.start()
    
    return app

# Create the app
app = create_app()
# Set webhook URL based on environment

is_development_mode = os.getenv('FLASK_ENV') == 'development'
if is_development_mode:
    WEBHOOK_SERVER_URL = "http://localhost:5000"
else:
    # Use container name and port for production
    WEBHOOK_SERVER_URL = "http://manhwa_reader:80"


# Webhook related globals

webhook_connection = None
last_heartbeat = 0
heartbeat_lock = Lock()
heartbeat_thread = None

@dataclass
class WebhookStatus:
    is_connected: bool = False
    last_heartbeat: float = 0
    connection_time: Optional[float] = None

webhook_status = WebhookStatus()

app.secret_key = Config.flask_secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # Or 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

Users = class_mangalist.Users


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
    if os.getenv('FLASK_ENV') == 'production':
        time_of_load = now - timedelta(hours=1) # my vps is -1 hour to my local time
    else:
        time_of_load = now
    # Print the time
    print("Time of the page load: ", time_of_load)
    # printing in what mode the program is runned
    return dict(isDevelopment=(os.getenv('FLASK_ENV') == 'development'))

# Ensure this is only set for development
app.config['DEBUG'] = (os.getenv('FLASK_ENV') == 'development')

@app.after_request
def set_security_headers(response):
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com https://cdn.jsdelivr.net/npm https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "connect-src 'self' ws://localhost:* wss://localhost:* ws://*.shirosplayground.space wss://*.shirosplayground.space;"
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
    download_statuses = {status['anilist_id']: status['status'] 
                        for status in sqlalchemy_fns.get_download_statuses()}
    
    # Add download status to each manga entry
    for entry in manga_entries:
        entry['download_status'] = download_statuses.get(entry['id_anilist'], 'not_downloaded')
    
    # Identify entries with missing covers and download them in a background thread
    ids_to_download = [entry['id_anilist'] for entry in manga_entries if not entry['is_cover_downloaded']]
    
    if ids_to_download:
        # Start a background thread to download covers instead of blocking the page load
        def download_covers_background():
            try:
                successful_ids = download_covers.download_covers_concurrently(ids_to_download, manga_entries)
                # Bulk update the database to mark the covers as downloaded only for successful ones
                if successful_ids:
                    sqlalchemy_fns.update_cover_download_status_bulk(successful_ids, True)
            except Exception as e:
                print(f"Error during download or database update: {e}")
        
        # Start the download thread
        download_thread = Thread(target=download_covers_background, daemon=True)
        download_thread.start()

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
            try:
                # Store the MangaUpdates link in external_links
                sqlalchemy_fns.update_manga_links(anilist_id, None, [input_link])
                
                # Run the spider directly
                result = run_crawl(input_link, anilist_id)
                if result:
                    try:
                        # Emit WebSocket event with updated MangaUpdates data
                        manga_updates = db_session.query(MangaUpdatesDetails)\
                            .filter(MangaUpdatesDetails.anilist_id == anilist_id)\
                            .first()
                        if manga_updates:
                            socketio.emit('mangaupdates_data_update', {
                                'anilist_id': anilist_id,
                                'data': {
                                    'status': manga_updates.status,
                                    'licensed': manga_updates.licensed,
                                    'completed': manga_updates.completed,
                                    'last_updated': manga_updates.last_updated_timestamp
                                }
                            })
                    except Exception as e:
                        logging.error(f"Error emitting WebSocket update: {e}")
                        # Continue execution even if WebSocket update fails

                return jsonify({
                    "status": "success",
                    "message": "MangaUpdates link added and data retrieved successfully",
                    "extractedLinks": [input_link]
                }), 200
            except Exception as e:
                logging.error(f"Error processing MangaUpdates link: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"Error processing MangaUpdates link: {str(e)}"
                }), 500

        # If it's not a MangaUpdates link, process as Bato link
        # If webhook is connected, send to webhook server
        if webhook_status.is_connected:
            try:
                webhook_data = {
                    "title": series_name,
                    "bato_link": input_link
                }
                webhook_response = requests.post(
                    "http://localhost:8000/webhook/manhwa",
                    json=webhook_data
                )
                if webhook_response.status_code != 200:
                    logging.warning(f"Webhook server returned error: {webhook_response.text}")
            except Exception as webhook_error:
                logging.error(f"Failed to send to webhook: {webhook_error}")

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

        # After successful processing and finding MangaUpdates link:
        if mangaupdates_link and result:
            try:
                manga_updates = db_session.query(MangaUpdatesDetails)\
                    .filter(MangaUpdatesDetails.anilist_id == anilist_id)\
                    .first()
                if manga_updates:
                    socketio.emit('mangaupdates_data_update', {
                        'anilist_id': anilist_id,
                        'data': {
                            'status': manga_updates.status,
                            'licensed': manga_updates.licensed,
                            'completed': manga_updates.completed,
                            'last_updated': manga_updates.last_updated_timestamp
                        }
                    })
            except Exception as e:
                logging.error(f"Error emitting WebSocket update: {e}")
                # Continue execution even if WebSocket update fails

        return jsonify({
            "status": "success",
            "message": "Bato link added successfully" + 
                      (" and MangaUpdates data retrieved" if mangaupdates_link else ", but no MangaUpdates link found"),
            "extractedLinks": extracted_links
        }), 200

    except Exception as e:
        logging.exception("An error occurred during the link extraction process:")
        # Return a more detailed error message
        error_msg = f"Error processing link: {str(e)}"
        logging.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500


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

def start_background_services():
    """Start background services in separate threads"""
    update_service_thread = Thread(target=start_update_service, daemon=True)
    update_service_thread.start()

@app.route('/api/mangaupdates/<int:anilist_id>')
@login_required
def get_mangaupdates_info(anilist_id):
    # Get manga updates info from database
    try:
        manga_updates = db_session.query(MangaUpdatesDetails)\
            .filter(MangaUpdatesDetails.anilist_id == anilist_id)\
            .first()
        
        if manga_updates:
            return jsonify({
                'mangaupdates_status': manga_updates.status,
                'mangaupdates_licensed': manga_updates.licensed,
                'mangaupdates_completed': manga_updates.completed,
                'mangaupdates_last_updated': manga_updates.last_updated_timestamp
            })
        return jsonify({'error': 'No MangaUpdates info found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications')
@login_required
def get_notifications():
    """Get unread notifications from both MangaUpdates and AniList"""
    try:
        # Get MangaUpdates notifications
        manga_notifications = db_session.query(MangaStatusNotification)\
            .filter(MangaStatusNotification.is_read == False)\
            .order_by(MangaStatusNotification.importance.desc(),
                     MangaStatusNotification.created_at.desc())\
            .all()
        
        # Get AniList notifications
        anilist_notifications = db_session.query(AnilistNotification)\
            .filter(AnilistNotification.is_read == False)\
            .order_by(AnilistNotification.created_at.desc())\
            .all()
        
        # Get all manga entries for title mapping
        manga_entries = db_session.query(MangaList).all()
        title_map = {
            entry.title_romaji: entry.title_english 
            for entry in manga_entries 
            if entry.title_english and entry.title_romaji
        }
        
        notifications = []
        
        # Format MangaUpdates notifications
        for n in manga_notifications:
            notifications.append({
                'id': n.id,
                'source': 'mangaupdates',
                'title': n.title,
                'type': n.notification_type,
                'message': n.message,
                'importance': n.importance,
                'created_at': n.created_at.isoformat() if n.created_at else None,
                'url': n.url,
                'anilist_id': n.anilist_id
            })
        
        # Format AniList notifications
        for n in anilist_notifications:
            # Try to get English title if available
            title = n.media_title
            if title in title_map:
                title = title_map[title]
            
            # Check if it's an anime notification by looking for animeId in extra_data
            is_anime = n.extra_data and 'animeId' in n.extra_data
            media_id = n.extra_data.get('animeId') if is_anime else n.media_id
            media_type = 'anime' if is_anime else 'manga'
            
            notifications.append({
                'id': n.notification_id,
                'source': 'anilist',
                'title': title,  # Use mapped title
                'original_title': n.media_title,  # Keep original title for reference
                'type': n.type,
                'message': n.reason or n.context or f"New {n.type.lower().replace('_', ' ')}",
                'importance': 1,
                'created_at': n.created_at.isoformat() if n.created_at else None,
                'url': f"https://anilist.co/{media_type}/{media_id}" if media_id else None,
                'anilist_id': n.media_id,
                'is_anime': is_anime
            })
        
        # Sort all notifications by creation date
        notifications.sort(key=lambda x: x['created_at'] if x['created_at'] else '', reverse=True)
        
        return jsonify({'notifications': notifications})
        
    except Exception as e:
        print(f"Error in get_notifications: {e}")
        return jsonify({'error': str(e), 'notifications': []}), 500

@app.route('/api/notifications/<string:source>/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(source, notification_id):
    """Mark a notification as read"""
    try:
        if source == 'mangaupdates':
            notification = db_session.query(MangaStatusNotification)\
                .filter(MangaStatusNotification.id == notification_id)\
                .first()
            if notification:
                notification.is_read = True
                db_session.commit()
                return jsonify({'success': True})
        elif source == 'anilist':
            notification = db_session.query(AnilistNotification)\
                .filter(AnilistNotification.notification_id == notification_id)\
                .first()
            if notification:
                notification.is_read = True
                db_session.commit()
                return jsonify({'success': True})
        return jsonify({'error': 'Notification not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Webhook routes
@app.route('/webhook/status', methods=['GET'])
@login_required
def get_webhook_status():
    """Get webhook server status"""
    global webhook_connection, last_heartbeat
    try:
        # Add debug logging
        logging.debug(f"Checking webhook status. Connection: {webhook_connection is not None}")
        
        # First check if we have a local connection
        if not webhook_connection:
            logging.info("No webhook connection established")
            return jsonify({
                'active': False,
                'uptime': 0,
                'message': 'Not connected',
                'last_heartbeat': None,
                'connection_time': None
            })

        # Check if we've received a heartbeat recently
        with heartbeat_lock:
            current_time = time.time()
            time_since_heartbeat = current_time - last_heartbeat if last_heartbeat > 0 else None
            is_alive = time_since_heartbeat is not None and time_since_heartbeat < 45

        logging.info(f"Status check - Last heartbeat: {last_heartbeat}, Time since: {time_since_heartbeat}")

        if is_alive:
            uptime = int(current_time - webhook_connection['connected_at'])
            logging.info(f"Connection alive. Uptime: {uptime}s")
            return jsonify({
                'active': True,
                'uptime': int(current_time - webhook_connection['connected_at']),  # Use connection time
                'message': 'Connected',
                'last_heartbeat': last_heartbeat,
                'connection_time': webhook_connection['connected_at']
            })
        else:
            message = 'Waiting for first heartbeat...' if time_since_heartbeat is None else \
                     f'Connection lost (no heartbeat for {int(time_since_heartbeat)}s)'
            logging.warning(f"Connection status: {message}")
            return jsonify({
                'active': False,
                'uptime': 0,
                'message': message,
                'last_heartbeat': last_heartbeat if last_heartbeat > 0 else None,
                'connection_time': webhook_connection['connected_at']
            })

    except Exception as e:
        logging.error(f"Failed to get webhook status: {e}")
        return jsonify({
            'active': False,
            'uptime': 0,
            'message': str(e),
            'last_heartbeat': None,
            'connection_time': None
        })

MAX_HEARTBEAT_RETRIES = 3

def send_heartbeat():
    global last_heartbeat, webhook_connection
    retry_count = 0
    
    while retry_count < MAX_HEARTBEAT_RETRIES:
        try:
            retry_count += 1
            # Generate auth hash for this heartbeat
            auth_hash = hashlib.sha256(
                f"heartbeat{webhook_connection['webhook_secret']}".encode()
                ).hexdigest()
            
            response = requests.post(
                f"{WEBHOOK_SERVER_URL}/webhook/heartbeat",
                json={"auth_hash": auth_hash},
                timeout=2
            )
            
            if response.ok:
                with heartbeat_lock:
                    last_heartbeat = time.time()
                    uptime = time.time() - webhook_connection['connected_at']
                socketio.emit('webhook_status', {
                    'status': 'connected',
                    'uptime': int(uptime / 60)  # Convert to minutes
                })
                return True
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Heartbeat failed: {e}")
            logging.warning(f"Failed to send heartbeat (attempt {retry_count}/{MAX_HEARTBEAT_RETRIES})")
            
            # Emit status update to clients
            socketio.emit('webhook_status', {
                'status': 'retrying',
                'attempt': retry_count,
                'max_attempts': MAX_HEARTBEAT_RETRIES
            })
            
            if retry_count < MAX_HEARTBEAT_RETRIES:
                time.sleep(2)  # Wait before retrying
                continue
                
            # If we've exhausted all retries
            socketio.emit('webhook_status', {
                'status': 'failed',
                'message': 'Connection lost after max retries'
            })
            return False

def start_heartbeat_thread():
    """Start a thread to send periodic heartbeats"""
    def heartbeat_loop():
        while True:
            if webhook_connection:
                if not send_heartbeat():
                    logging.error("Heartbeat failed. Stopping heartbeat thread.")
                    break
            else:
                # No connection, stop the thread
                logging.info("No webhook connection. Stopping heartbeat thread.")
                break
                
            time.sleep(10)  # Send heartbeat every 10 seconds
            
    thread = Thread(target=heartbeat_loop, daemon=True)
    thread.start()
    logging.info("Started heartbeat thread")
    return thread

@app.route('/webhook/toggle', methods=['POST'])
@login_required
def toggle_webhook():
    """Connect/disconnect to webhook server"""
    global webhook_connection, heartbeat_thread
    try:
        action = request.json.get('action')
        logging.info(f"Webhook toggle action: {action}")

        if action == 'start':
            # Stop existing heartbeat thread if it exists
            if heartbeat_thread and heartbeat_thread.is_alive():
                webhook_connection = None  # This will stop the existing thread
                time.sleep(0.1)  # Give the thread time to stop

            client_secret = secrets.token_hex(32)
            logging.info(f"Connecting to webhook server at: {WEBHOOK_SERVER_URL}")

            response = requests.post(
                f"{WEBHOOK_SERVER_URL}/connect_webhook",
                json={'secret': client_secret},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                current_time = time.time()
                webhook_connection = {
                    'client_secret': client_secret,
                    'webhook_secret': data['webhook_secret'],
                    'connection_hash': data['connection_hash'],
                    'connected_at': current_time,  # Add connection timestamp
                    'start_time': current_time  # Add start time
                }
                logging.info("Successfully established webhook connection")

                # Start new heartbeat thread
                heartbeat_thread = start_heartbeat_thread()

                return jsonify({
                    'success': True,
                    'status': 'connected'
                })
        else:
            webhook_connection = None  # This will stop the heartbeat thread
            return jsonify({
                'success': True,
                'status': 'disconnected'
            })

    except requests.exceptions.ConnectionError as e:
        webhook_connection = None
        error_msg = f"Could not connect to {WEBHOOK_SERVER_URL}: {str(e)}"
        logging.error(error_msg)
        return jsonify({'success': False, 'message': error_msg}), 500
    except Exception as e:
        webhook_connection = None
        logging.error(f"Error in toggle_webhook: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/webhook/start_scraper', methods=['POST'])
@login_required
def start_scraper_command():
    global webhook_connection
    try:
        if not webhook_connection:
            return jsonify({
                'status': 'error',
                'message': 'Not connected to webhook server'
            }), 400

        # Generate auth hash using only webhook_secret (to match server side)
        auth_hash = hashlib.sha256(
            f"start_scraper{webhook_connection['webhook_secret']}".encode()
        ).hexdigest()

        logging.info(f"Sending start command with auth hash: {auth_hash[:8]}...")

        response = requests.post(
            f"{WEBHOOK_SERVER_URL}/webhook_command",
            json={
                'command': 'start_scraper',
                'auth_hash': auth_hash
            },
            timeout=5
        )

        if response.status_code == 401:
            logging.error("Authentication failed. Hash mismatch.")
            return jsonify({
                'status': 'error',
                'message': 'Authentication failed'
            }), 401

        return jsonify(response.json()), response.status_code

    except Exception as e:
        logging.error(f"Error starting scraper: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/webhook/stop_scraper', methods=['POST'])
@login_required
def stop_scraper_command():
    global webhook_connection
    try:
        if not webhook_connection:
            return jsonify({
                'status': 'error',
                'message': 'Not connected to webhook server'
            }), 400

        # Generate auth hash using only webhook_secret
        auth_hash = hashlib.sha256(
            f"stop_scraper{webhook_connection['webhook_secret']}".encode()
        ).hexdigest()

        logging.info(f"Sending stop command with auth hash: {auth_hash[:8]}...")

        response = requests.post(
            f"{WEBHOOK_SERVER_URL}/webhook_command",
            json={
                'command': 'stop_scraper',
                'auth_hash': auth_hash
            },
            timeout=5
        )

        if response.status_code == 401:
            logging.error("Authentication failed. Hash mismatch.")
            return jsonify({
                'status': 'error',
                'message': 'Authentication failed'
            }), 401

        return jsonify(response.json()), response.status_code

    except Exception as e:
        logging.error(f"Error stopping scraper: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/queue/pause', methods=['POST'])
@login_required
def pause_queue_task_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if task and task.anilist_id:
            sqlalchemy_fns.pause_queue_task(title)
            # Emit both events
            socketio.emit('queue_update', {'type': 'task_paused'})
            socketio.emit('download_status_update', {
                'anilist_id': task.anilist_id,
                'status': 'stopped'
            })
            logging.info(f"Emitted status update for {task.anilist_id}: stopped")  # Debug log
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error in pause_queue_task_route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/resume', methods=['POST'])
@login_required
def resume_queue_task_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if task and task.anilist_id:  # Add this check
            sqlalchemy_fns.resume_queue_task(title)
            socketio.emit('queue_update', {'type': 'task_resumed'})
            # Add this emit for download status
            socketio.emit('download_status_update', {
                'anilist_id': task.anilist_id,
                'status': 'pending'
            })
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/remove', methods=['POST'])
@login_required
def remove_queue_task_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if task and task.anilist_id:  # Add this check
            if sqlalchemy_fns.remove_queue_task(title):
                socketio.emit('queue_update', {'type': 'task_removed'})
                # Add this emit for download status
                socketio.emit('download_status_update', {
                    'anilist_id': task.anilist_id,
                    'status': 'not_downloaded'
                })
                return jsonify({'success': True}), 200
        return jsonify({'error': 'Task not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/force_priority', methods=['POST'])
@login_required
def force_priority_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        sqlalchemy_fns.force_task_priority(title)
        socketio.emit('queue_update', {'type': 'priority_changed'})
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/add', methods=['POST'])
@login_required
def add_to_queue_route():
    try:
        data = request.json
        title = data.get('title')
        bato_url = data.get('bato_url')
        anilist_id = data.get('anilist_id')

        if not all([title, bato_url]):
            return jsonify({'error': 'Missing required fields'}), 400

        if sqlalchemy_fns.add_to_queue(title, bato_url, anilist_id):
            # Emit WebSocket event for real-time update
            socketio.emit('download_status_update', {
                'anilist_id': anilist_id,
                'status': 'pending'
            })
            return jsonify({'success': True}), 200
        return jsonify({'error': 'Failed to add to queue'}), 500
    except Exception as e:
        logging.error(f"Error adding to queue: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/status')
@login_required
def get_queue_status_route():
    try:
        current_task, pending_tasks = sqlalchemy_fns.get_queue_status()
        
        return jsonify({
            'current_task': {
                'title': current_task.manhwa_title if current_task else None,
                'status': current_task.status if current_task else None,
                'current_chapter': current_task.current_chapter if current_task else 0,
                'total_chapters': current_task.total_chapters if current_task else 0,
                'error_message': current_task.error_message if current_task else None,
                'anilist_id': current_task.anilist_id if current_task else None
            } if current_task else None,
            'queued_tasks': [{
                'title': task.manhwa_title,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'current_chapter': task.current_chapter,
                'total_chapters': task.total_chapters,
                'anilist_id': task.anilist_id
            } for task in pending_tasks]
        })
    except Exception as e:
        logging.error(f"Error getting queue status: {e}")
        return jsonify({'error': str(e)}), 500

# Initialize SocketIO with the correct async mode
socketio = SocketIO(
    app,
    async_mode='gevent',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

@app.route('/webhook/queue_update', methods=['POST'])
def queue_update_notification():
    """Endpoint for webhook server to notify about queue changes"""
    try:
        # Emit socket event to all connected clients
        socketio.emit('queue_update', {
            'timestamp': datetime.utcnow().isoformat(),
            'type': request.json.get('type', 'update')
        })
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error handling queue update notification: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/heartbeat', methods=['POST'])
def handle_heartbeat():
    """Handle heartbeat from webhook server"""
    global webhook_connection, last_heartbeat
    try:
        if not webhook_connection:
            logging.warning("Received heartbeat but no webhook connection exists")
            return jsonify({'error': 'Not connected'}), 401

        data = request.json
        auth_hash = data.get('auth_hash')
        
        logging.info(f"Received heartbeat with auth hash: {auth_hash[:8] if auth_hash else 'None'}")
        
        expected_hash = hashlib.sha256(
            f"heartbeat{webhook_connection['webhook_secret']}".encode()
        ).hexdigest()
        
        logging.info(f"Expected auth hash: {expected_hash[:8]}")

        if auth_hash != expected_hash:
            logging.warning(f"Invalid heartbeat auth hash. Expected: {expected_hash[:8]}, Got: {auth_hash[:8]}")
            return jsonify({'error': 'Invalid authentication'}), 401

        # Initialize last_heartbeat if it's the first heartbeat
        with heartbeat_lock:
            if last_heartbeat == 0:
                logging.info("Received first heartbeat")
            previous_heartbeat = last_heartbeat
            last_heartbeat = time.time()
            time_since_last = last_heartbeat - previous_heartbeat if previous_heartbeat > 0 else 0
            
        logging.info(f"Heartbeat received and updated. Time since last heartbeat: {time_since_last:.1f}s")
        
        # Notify clients about the heartbeat via WebSocket
        socketio.emit('webhook_heartbeat', {
            'timestamp': time.time(),
            'connected': True
        })
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logging.error(f"Error handling heartbeat: {e}")
        return jsonify({'error': str(e)}), 500

# Add these routes for download status management
@app.route('/api/download/status')
@login_required
def get_download_status():
    try:
        statuses = sqlalchemy_fns.get_download_statuses()
        return jsonify(statuses)
    except Exception as e:
        logging.error(f"Error getting download status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/status/update', methods=['POST'])
@login_required
def update_download_status():
    try:
        data = request.json
        anilist_id = data.get('anilist_id')
        status = data.get('status')
        
        if not anilist_id or not status:
            return jsonify({'error': 'anilist_id and status are required'}), 400
            
        sqlalchemy_fns.update_download_status(anilist_id, status)
        
        # Notify clients about the status update
        socketio.emit('download_status_update', {
            'anilist_id': anilist_id,
            'status': status
        })
        
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error updating download status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/manga/titles', methods=['POST'])
@login_required
def get_manga_titles():
    data = request.get_json()
    anilist_ids = data.get('anilist_ids', [])
    
    # Query the manga list table for titles
    titles = {}
    try:
        manga_entries = MangaList.query.filter(MangaList.id_anilist.in_(anilist_ids)).all()
        for entry in manga_entries:
            titles[entry.id_anilist] = entry.title_english
    except Exception as e:
        print(f"Error fetching manga titles: {e}")
        return jsonify({}), 500
        
    return jsonify(titles)

@app.route('/api/notifications/refresh', methods=['POST'])
@login_required
def refresh_notifications():
    """Manual refresh endpoint"""
    notifications = notification_manager.get_notifications()
    return jsonify(notifications)

@app.route('/animelist')
@login_required
def animelist():
    """Display the anime list page"""
    try:
        # Query the database for anime list entries using SQLAlchemy with text()
        anime_list_entries = db_session.execute(
            text('SELECT * FROM anime_list ORDER BY last_updated_on_site DESC')
        ).fetchall()
        
        anime_entries = []
        episode_count = 0
        tv_count = 0
        ova_count = 0
        special_count = 0
        movie_count = 0
        average_score_count = 0
        record_count = 0
        record_count_without_rating = 0
        
        # Process the result into a list of dictionaries
        if anime_list_entries:
            for row in anime_list_entries:
                anime_entries.append({
                    'id_mal': row.id_mal,
                    'media_format': row.media_format,
                    'title_romaji': row.title_romaji,
                    'episodes_progress': row.episodes_progress,
                    'all_episodes': row.all_episodes,
                    'on_list_status': row.on_list_status,
                    'score': row.score,
                    'air_status': row.air_status,
                    'notes': row.notes,
                    'user_stardetAt': row.user_stardetAt,
                    'user_completedAt': row.user_completedAt,
                    'rewatched_times': row.rewatched_times
                })
                
                # Calculate statistics
                record_count += 1
                if row.score != 0:
                    record_count_without_rating += 1
                episode_count += row.episodes_progress
                if row.media_format == 'TV':
                    tv_count += 1
                elif row.media_format == 'OVA':
                    ova_count += 1
                elif row.media_format == 'Special':
                    special_count += 1
                elif row.media_format == 'Movie':
                    movie_count += 1
                if row.score != 0:
                    average_score_count += row.score
                    
                # Add rewatched episodes to count
                if row.rewatched_times != 0:
                    episode_count += row.episodes_progress * row.rewatched_times
        
        # Calculate average score
        avg_score = round(average_score_count / record_count_without_rating, 2) if record_count_without_rating > 0 else 0
        
        # Calculate days spent watching
        days_watched = round((episode_count * 23.8) / 60 / 24, 2)
        
        statistics = {
            'record_count': record_count,
            'tv_count': tv_count,
            'ova_count': ova_count,
            'special_count': special_count,
            'movie_count': movie_count,
            'episode_count': episode_count,
            'days_watched': days_watched,
            'avg_score': avg_score
        }
        
        # Load user color settings
        color_settings = load_color_settings()
        
        return render_template('animelist.html', 
                               anime_entries=anime_entries, 
                               statistics=statistics,
                               color_settings=color_settings)
    
    except Exception as e:
        logging.exception("Error loading anime list:")
        return render_template('animelist.html', anime_entries=[], error=str(e))

@app.route('/api/update_episodes', methods=['POST'])
@login_required
def update_episodes():
    """Update the number of episodes watched for an anime"""
    try:
        data = request.json
        anime_id = data.get('animeId')
        episodes = data.get('episodes')
        
        if not anime_id or episodes is None:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Validate that episodes is a number
        try:
            episodes = int(episodes)
            if episodes < 0:
                return jsonify({'success': False, 'message': 'Episodes must be a positive number'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Episodes must be a valid number'}), 400
            
        # Update the database using SQLAlchemy with text()
        try:
            db_session.execute(
                text("UPDATE anime_list SET episodes_progress = :episodes WHERE id_mal = :anime_id"),
                {"episodes": episodes, "anime_id": anime_id}
            )
            db_session.commit()
            
            # Log the successful update
            logging.info(f"Updated episodes for anime ID {anime_id} to {episodes}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully updated episodes to {episodes}'
            }), 200
            
        except Exception as db_error:
            db_session.rollback()
            logging.error(f"Database error during episode update: {db_error}")
            return jsonify({'success': False, 'message': f'Database error: {str(db_error)}'}), 500
            
    except Exception as e:
        logging.exception("Error updating episodes:")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/check_covers', methods=['POST'])
def check_covers():
    """Check if the specified covers have been downloaded"""
    try:
        data = request.get_json()
        anilist_ids = data.get('anilist_ids', [])
        
        if not anilist_ids:
            logging.warning("Check covers called with no IDs")
            return jsonify({'error': 'No IDs provided'}), 400
        
        logging.info(f"Checking covers for {len(anilist_ids)} IDs")
        results = {}
        covers_dir = os.path.join('app', 'static', 'covers')
        
        # Ensure the covers directory exists
        if not os.path.exists(covers_dir):
            logging.warning(f"Covers directory does not exist: {covers_dir}")
            os.makedirs(covers_dir, exist_ok=True)
        
        for anilist_id in anilist_ids:
            # Check if AVIF exists first (preferred format)
            avif_path = os.path.join(covers_dir, f"{anilist_id}.avif")
            webp_path = os.path.join(covers_dir, f"{anilist_id}.webp")
            
            if os.path.exists(avif_path):
                logging.debug(f"Found AVIF cover for ID {anilist_id}")
                results[anilist_id] = {
                    'downloaded': True,
                    'format': 'avif',
                    'path': f'/static/covers/{anilist_id}.avif'
                }
            elif os.path.exists(webp_path):
                logging.debug(f"Found WebP cover for ID {anilist_id}")
                results[anilist_id] = {
                    'downloaded': True,
                    'format': 'webp', 
                    'path': f'/static/covers/{anilist_id}.webp'
                }
            else:
                logging.debug(f"No cover found for ID {anilist_id}")
                results[anilist_id] = {
                    'downloaded': False
                }
        
        # If any covers were found, update the database
        downloaded_ids = [int(id) for id, result in results.items() 
                         if result['downloaded'] and id.isdigit()]
        
        if downloaded_ids:
            logging.info(f"Updating database for {len(downloaded_ids)} newly found covers")
            try:
                sqlalchemy_fns.update_cover_download_status_bulk(downloaded_ids, True)
            except Exception as e:
                logging.error(f"Error updating cover status in database: {e}")
        
        return jsonify({'results': results})
    except Exception as e:
        logging.error(f"Error checking covers: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For local development
    if os.getenv('FLASK_ENV') == 'development':
        socketio.run(app, host='0.0.0.0', port=5001, debug=True)
    else:
        # In production, Gunicorn will handle this
        app.run()



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
