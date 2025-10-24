import app.download_covers as download_covers
from app.functions import sqlalchemy_fns as sqlalchemy_fns
from flask import Flask, flash, render_template, jsonify, request, session, url_for, redirect, send_from_directory
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
from functools import wraps
from engineio.async_drivers import gevent
import secrets
import hashlib
from app.background_tasks import BackgroundTaskManager
from app.services.anilist_notification import AnilistNotificationManager
import asyncio
from app.functions.class_mangalist import MangaStatusNotification, AnilistNotification
from sqlalchemy import text
from app.oauth_handler import AniListOAuth
from app.oauth_config import ANILIST_CLIENT_ID, ANILIST_CLIENT_SECRET, ANILIST_REDIRECT_URI
from app.utils.token_encryption import encrypt_token
from flask_cors import CORS

# Import blueprints
from app.blueprints.auth import auth_bp
from app.blueprints.main import main_bp
from app.blueprints.api import api_bp
from app.blueprints.download import download_bp
from app.blueprints.webhook import webhook_bp, webhook_status
from app.blueprints.notifications import notifications_bp
from app.blueprints.manga import manga_bp
from app.blueprints.graphql import graphql_bp
from app.blueprints.extension import extension_bp
from app.blueprints.bato_notifications import bato_notifications_bp
from app.blueprints.bato_admin import bato_admin_bp

# Import Bato database initialization and notification polling
from app.models.bato_models import init_bato_db
from app.services.bato_notification_polling import init_bato_notification_poller, stop_bato_notification_poller

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
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
    
    # Add MIME type configuration for static files
    app.config['MIME_TYPES'] = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.avif': 'image/avif'
    }
    
    # Initialize CORS with permissive settings for development
    # In production, you should specify allowed origins for security
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5001", "https://easterntalesshelf.site"],  # Restrict to localhost:5001 and your website
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Register all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(manga_bp)
    app.register_blueprint(graphql_bp)
    app.register_blueprint(extension_bp)
    app.register_blueprint(bato_notifications_bp)
    app.register_blueprint(bato_admin_bp)

    with app.app_context():
        # Initialize database tables for Bato
        try:
            from app.functions.class_mangalist import engine
            init_bato_db(engine)
            logging.info("Bato database tables initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Bato database tables: {e}")
        
        # Initialize notification manager and background tasks
        app.notification_manager = AnilistNotificationManager()
        app.background_manager = BackgroundTaskManager()
        
        # Note: BatoScrapingService now runs in a separate container
        # See docker-compose.yml for bato-scraping-service configuration
        
        # Create a thread to run the background tasks
        def run_background_tasks():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start the background polling
            app.background_manager.start_polling(
                app.notification_manager,
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

# Ensure this is only set for development
app.config['DEBUG'] = (os.getenv('FLASK_ENV') == 'development')
# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

Users = class_mangalist.Users

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized_callback():
    return jsonify({'error': 'Unauthorized access'}), 401

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/x-icon')

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
    
    # Get GraphQL safety key from environment
    graphql_safety_key = os.getenv('GRAPHQL_SAFETY_KEY', '')
    
    # printing in what mode the program is runned
    return dict(
        isDevelopment=(os.getenv('FLASK_ENV') == 'development'),
        graphql_safety_key=graphql_safety_key
    )

@app.after_request
def set_security_headers(response):
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com https://cdn.jsdelivr.net/npm https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob: https://*.anilist.co; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "connect-src 'self' ws://localhost:* wss://localhost:* ws://*.easterntalesshelf.site wss://*.easterntalesshelf.site chrome-extension://* http://localhost:* https://localhost:* https://cdn.jsdelivr.net;"
    )

    # Add CORS headers for API requests
    if request.path.startswith('/api/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        # Handle preflight OPTIONS requests
        if request.method == 'OPTIONS':
            response.status_code = 200
            return response

    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = csp_policy
    return response

@app.teardown_appcontext
def cleanup(resp_or_exc):
    try:
        db_session.remove()
    except Exception as e:
        print(f"Error during database cleanup: {e}")

def shutdown_services():
    """Gracefully shutdown all background services"""
    logging.info("Shutting down background services...")
    
    # Stop Bato notification poller
    try:
        stop_bato_notification_poller()
        logging.info("Bato notification poller stopped")
    except Exception as e:
        logging.error(f"Error stopping Bato notification poller: {e}")
    
    # Note: BatoScrapingService runs in a separate container and is managed independently
    # No need to stop it from the main web application
    
    logging.info("All background services shut down")

# Register shutdown handler
import atexit
atexit.register(shutdown_services)

def start_background_services():
    """Start background services in separate threads"""
    update_service_thread = Thread(target=start_update_service, daemon=True)
    update_service_thread.start()

# Initialize SocketIO with the correct async mode
socketio = SocketIO(
    app,
    async_mode='gevent',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

# Attach socketio to app for access via current_app.socketio
app.socketio = socketio

# Initialize Bato notification poller (polls every 60 seconds)
# This bridges the standalone Bato scraping container with the web app's real-time notifications
try:
    init_bato_notification_poller(socketio, poll_interval=60)
    logging.info("Bato notification poller initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize Bato notification poller: {e}")

if __name__ == '__main__':
    # For local development
    if os.getenv('FLASK_ENV') == 'development':
        socketio.run(app, host='0.0.0.0', port=5001, debug=True)
    else:
        # In production, Gunicorn will handle this
        app.run()