from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.admin import admin_required
from app.functions import sqlalchemy_fns
import logging
import requests
from bs4 import BeautifulSoup
import re
from app.functions.class_mangalist import db_session, MangaUpdatesDetails
from app.functions.manga_updates_spider import MangaUpdatesSpider
from crochet import run_in_reactor
from scrapy.crawler import CrawlerRunner
from app.blueprints.webhook import webhook_status

manga_bp = Blueprint('manga', __name__)

@manga_bp.route('/add_bato', methods=['POST'])
@login_required
@admin_required
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
                            current_app.socketio.emit('mangaupdates_data_update', {
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
                    current_app.socketio.emit('mangaupdates_data_update', {
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

@manga_bp.route('/sync', methods=['POST'])
@login_required
@admin_required
def sync_with_fastapi():
    try:
        from app.config import fastapi_updater_server_IP
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