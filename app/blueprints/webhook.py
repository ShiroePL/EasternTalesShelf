from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from app.admin import admin_required
import requests
import time
import logging
import hashlib
import secrets
import os
from threading import Thread, Lock
from bs4 import BeautifulSoup
import re
from app.functions.class_mangalist import db_session
from app.functions import sqlalchemy_fns
from app.functions.manga_updates_spider import MangaUpdatesSpider
from crochet import run_in_reactor
from dataclasses import dataclass
from typing import Optional
from flask import current_app

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

# Global variables
webhook_connection = None
last_heartbeat = 0
heartbeat_lock = Lock()
heartbeat_thread = None

# Set webhook URL based on environment
is_development_mode = os.getenv('FLASK_ENV') == 'development'
if is_development_mode:
    WEBHOOK_SERVER_URL = "http://localhost:5000"
else:
    # Use container name and port for production
    WEBHOOK_SERVER_URL = "http://manhwa_reader:80"

@dataclass
class WebhookStatus:
    is_connected: bool = False
    last_heartbeat: float = 0
    connection_time: Optional[float] = None

webhook_status = WebhookStatus()

@webhook_bp.route('/status', methods=['GET'])
@login_required
@admin_required
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

@webhook_bp.route('/toggle', methods=['POST'])
@login_required
@admin_required
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

@webhook_bp.route('/start_scraper', methods=['POST'])
@login_required
@admin_required
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

@webhook_bp.route('/stop_scraper', methods=['POST'])
@login_required
@admin_required
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

@webhook_bp.route('/heartbeat', methods=['POST'])
@login_required
@admin_required
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
        current_app.socketio.emit('webhook_heartbeat', {
            'timestamp': time.time(),
            'connected': True
        })
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logging.error(f"Error handling heartbeat: {e}")
        return jsonify({'error': str(e)}), 500

@webhook_bp.route('/queue_update', methods=['POST'])
@login_required
@admin_required
def queue_update_notification():
    """Endpoint for webhook server to notify about queue changes"""
    try:
        # Emit socket event to all connected clients
        from datetime import datetime
        current_app.socketio.emit('queue_update', {
            'timestamp': datetime.utcnow().isoformat(),
            'type': request.json.get('type', 'update')
        })
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error handling queue update notification: {e}")
        return jsonify({'error': str(e)}), 500

# Utility functions
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

def send_heartbeat():
    global last_heartbeat, webhook_connection
    MAX_HEARTBEAT_RETRIES = 3
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
                current_app.socketio.emit('webhook_status', {
                    'status': 'connected',
                    'uptime': int(uptime / 60)  # Convert to minutes
                })
                return True
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Heartbeat failed: {e}")
            logging.warning(f"Failed to send heartbeat (attempt {retry_count}/{MAX_HEARTBEAT_RETRIES})")
            
            # Emit status update to clients
            current_app.socketio.emit('webhook_status', {
                'status': 'retrying',
                'attempt': retry_count,
                'max_attempts': MAX_HEARTBEAT_RETRIES
            })
            
            if retry_count < MAX_HEARTBEAT_RETRIES:
                time.sleep(2)  # Wait before retrying
                continue
                
            # If we've exhausted all retries
            current_app.socketio.emit('webhook_status', {
                'status': 'failed',
                'message': 'Connection lost after max retries'
            })
            return False

@webhook_bp.route('/manhwa', methods=['POST'])
def process_webhook_manhwa():
    try:
        data = request.json
        title = data.get('title')
        bato_link = data.get('bato_link')
        
        if not title or not bato_link:
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        # Extract links from bato page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(bato_link, headers=headers)
        if response.status_code != 200:
            return jsonify({'status': 'error', 'message': 'Failed to fetch bato page'}), 500
        
        extracted_links = extract_links_from_bato(response.text)
        
        # Look for MangaUpdates link
        mangaupdates_link = None
        for link in extracted_links:
            if 'mangaupdates.com' in link.lower():
                mangaupdates_link = link
                break
        
        if not mangaupdates_link:
            return jsonify({
                'status': 'warning',
                'message': 'No MangaUpdates link found',
                'extracted_links': extracted_links
            })
        
        # Run the MangaUpdates spider with the link
        # This would need to be implemented based on your specific needs
        
        return jsonify({
            'status': 'success',
            'message': 'Processed webhook successfully',
            'mangaupdates_link': mangaupdates_link,
            'extracted_links': extracted_links
        })
        
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

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