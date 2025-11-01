from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.admin import admin_required
from app.functions import sqlalchemy_fns
import logging
import requests
from bs4 import BeautifulSoup
import re
import traceback
from app.functions.class_mangalist import db_session, MangaUpdatesDetails
from app.scraper.mangaupdates_api.mangaupdates_api_client import MangaUpdatesAPIClient
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
            logging.info("MangaUpdates link detected, processing with API client")
            try:
                # Store the MangaUpdates link in external_links
                sqlalchemy_fns.update_manga_links(anilist_id, None, [input_link])
                
                # Also store the URL in mangaupdates_details table
                sqlalchemy_fns.save_mangaupdates_url(anilist_id, input_link)
                
                # Fetch data using the new API client (much faster than spider!)
                api_client = MangaUpdatesAPIClient()
                result = api_client.get_series_full_data(input_link)
                
                if result:
                    # Save to database with both spider-compatible and full API data
                    sqlalchemy_fns.save_manga_details(
                        result['spider_data'], 
                        anilist_id,
                        api_data=result['api_data']
                    )
                    
                    logging.info(f"✅ Successfully fetched and saved MangaUpdates data via API")
                    
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
                                    'last_updated': manga_updates.last_updated_timestamp,
                                    'rating': manga_updates.bayesian_rating,
                                    'latest_chapter': manga_updates.latest_chapter
                                }
                            })
                    except Exception as e:
                        logging.error(f"Error emitting WebSocket update: {e}")
                        # Continue execution even if WebSocket update fails

                    return jsonify({
                        "status": "success",
                        "message": "MangaUpdates link added and data retrieved successfully via API",
                        "extractedLinks": [input_link]
                    }), 200
                else:
                    logging.error("Failed to fetch data from MangaUpdates API")
                    return jsonify({
                        "status": "error",
                        "message": "Failed to fetch data from MangaUpdates API"
                    }), 500
                    
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

        # ==================== TRIGGER INITIAL BATO SCRAPING ====================
        # This is the missing piece! When a Bato link is added, we need to:
        # 1. Scrape initial manga details and chapters
        # 2. Create initial schedule entry
        # 3. This makes the manga visible to the Bato container for ongoing scraping
        
        bato_scrape_success = False
        bato_scrape_message = ""
        
        try:
            # Extract bato_id from the input_link
            bato_id_match = re.search(r'/title/(\d+)', input_link)
            if bato_id_match:
                bato_id = bato_id_match.group(1)
                logging.info(f"🔄 Triggering initial Bato scraping for bato_id: {bato_id}")
                
                # Import Bato scrapers
                from app.scraper.bato_graphql_hidden_api.bato_chapters_list_graphql import BatoChaptersListGraphQL
                from app.scraper.bato_graphql_hidden_api.bato_manga_details_graphql import BatoMangaDetailsGraphQL
                from app.database_module.bato_repository import BatoRepository
                from datetime import datetime, timedelta
                
                # Initialize scrapers and repository
                chapters_scraper = BatoChaptersListGraphQL(verbose=False)
                details_scraper = BatoMangaDetailsGraphQL(verbose=False)
                bato_repo = BatoRepository()
                
                # Scrape manga details
                logging.info(f"📚 Fetching Bato manga details for {series_name}...")
                details_data = details_scraper.scrape_manga_details(bato_id)
                
                # Scrape chapters
                logging.info(f"📖 Fetching Bato chapters for {series_name}...")
                chapters_result = chapters_scraper.scrape_chapters(bato_id, get_manga_title=False)
                chapters_data = chapters_result.get('chapters', [])
                
                # Save manga details to bato_manga_details table
                # Map GraphQL API fields to database columns (see bato_models.py)
                manga_details_dict = {
                    'anilist_id': anilist_id,
                    'bato_link': input_link,
                    'bato_id': bato_id,
                    'name': details_data.get('name', series_name),
                    'alt_names': details_data.get('alt_names', []),  # JSON column, not comma-separated
                    'authors': details_data.get('authors', []),  # JSON column
                    'artists': details_data.get('artists', []),  # JSON column
                    'genres': details_data.get('genres', []),  # JSON column
                    'upload_status': details_data.get('upload_status'),
                    'summary': details_data.get('summary'),
                    # Rating data (stat_score_*)
                    'stat_score_val': details_data.get('stat_score_val', 0.0),
                    'stat_count_votes': details_data.get('stat_count_votes', 0),
                    'stat_count_scores': details_data.get('stat_count_scores', []),
                    # Statistics (stat_count_*)
                    'stat_count_follows': details_data.get('stat_count_follows', 0),
                    'stat_count_reviews': details_data.get('stat_count_reviews', 0),
                    'stat_count_post_reply': details_data.get('stat_count_post_reply', 0),
                    'stat_count_views_total': details_data.get('stat_count_views_total', 0),
                    'stat_count_emotions': details_data.get('stat_count_emotions', []),
                    # Publication info
                    'orig_lang': details_data.get('orig_lang'),
                    'original_status': details_data.get('original_status'),
                    'original_pub_from': details_data.get('original_pub_from'),
                    'original_pub_till': details_data.get('original_pub_till'),
                    'read_direction': details_data.get('read_direction')
                }
                bato_repo.upsert_manga_details(manga_details_dict)
                logging.info(f"✅ Saved Bato manga details for {series_name}")
                
                # Save chapters to bato_chapters table
                if chapters_data:
                    # Check if chapters already exist (skip if this is a retry)
                    existing_chapters = bato_repo.get_chapters(anilist_id)
                    if existing_chapters:
                        logging.info(f"ℹ️ Manga already has {len(existing_chapters)} chapters in database, skipping chapter insert")
                        inserted_count = len(existing_chapters)
                    else:
                        chapters_to_insert = []
                        for chapter in chapters_data:
                            chapter_dict = {
                                'anilist_id': anilist_id,
                                'bato_link': input_link,
                                'bato_chapter_id': chapter.get('bato_chapter_id'),
                                'canonical_chapter_id': chapter.get('canonical_chapter_id'),  # Required field
                                'chapter_number': chapter.get('chapter_number'),
                                'dname': chapter.get('dname'),
                                'title': chapter.get('title'),
                                'url_path': chapter.get('url_path'),
                                'full_url': chapter.get('full_url'),
                                'date_create': chapter.get('date_create'),
                                'date_public': chapter.get('date_public'),
                                # Statistics (stat_count_*)
                                'stat_count_views_guest': chapter.get('stat_count_views_guest', 0),
                                'stat_count_views_login': chapter.get('stat_count_views_login', 0),
                                'stat_count_views_total': chapter.get('stat_count_views_total', 0),
                                'stat_count_post_reply': chapter.get('stat_count_post_reply', 0)
                            }
                            chapters_to_insert.append(chapter_dict)
                        
                        inserted_count = bato_repo.bulk_insert_chapters(chapters_to_insert)
                        logging.info(f"✅ Saved {inserted_count} Bato chapters for {series_name}")
                else:
                    logging.warning(f"⚠️ No chapters found for {series_name}")
                    inserted_count = 0
                
                # Create initial schedule (24 hours default) - skip if already exists
                existing_schedule = bato_repo.get_schedule(anilist_id)
                if existing_schedule:
                    logging.info(f"ℹ️ Schedule already exists for manga, skipping schedule creation")
                    next_scrape_at = existing_schedule.next_scrape_at
                else:
                    next_scrape_at = datetime.now() + timedelta(hours=24)
                    schedule_data = {
                        'anilist_id': anilist_id,
                        'bato_link': input_link,
                        'next_scrape_at': next_scrape_at,
                        'scraping_interval_hours': 24,  # Correct column name
                        'total_chapters_tracked': len(chapters_data) if chapters_data else 0
                    }
                    bato_repo.upsert_schedule(schedule_data)
                    logging.info(f"✅ Created initial Bato schedule for {series_name} (next scrape: {next_scrape_at})")
                
                # Log the scraping job
                log_data = {
                    'anilist_id': anilist_id,
                    'bato_link': input_link,
                    'scrape_type': 'initial',
                    'status': 'success',
                    'chapters_found': len(chapters_data) if chapters_data else 0,
                    'new_chapters': len(chapters_data) if chapters_data else 0,  # All chapters are new on initial scrape
                    'duration_seconds': 0,  # Not tracking duration for initial scrape
                    'error_message': None
                }
                bato_repo.log_scraping_job(log_data)
                
                bato_scrape_success = True
                bato_scrape_message = f"Initial Bato scraping completed: {inserted_count} chapters saved (scraped {len(chapters_data) if chapters_data else 0} total)"
                logging.info(f"🎉 {bato_scrape_message}")
                
            else:
                logging.warning(f"⚠️ Could not extract bato_id from link: {input_link}")
                bato_scrape_message = "Could not extract Bato ID from link"
                
        except Exception as bato_error:
            logging.error(f"❌ Error during initial Bato scraping: {bato_error}")
            logging.error(traceback.format_exc())
            bato_scrape_message = f"Bato scraping failed: {str(bato_error)}"
        
        # ==================== END BATO SCRAPING ====================

        # Look for the MangaUpdates link
        mangaupdates_link = None
        for link in extracted_links:
            if 'mangaupdates.com' in link.lower():
                mangaupdates_link = link
                logging.info(f"Found MangaUpdates link: {link}")
                break

        # If MangaUpdates link is found, add it to external_links and fetch data via API
        if mangaupdates_link:
            # Add the MangaUpdates link to external_links
            logging.info(f"Adding MangaUpdates link to external_links: {mangaupdates_link}")
            sqlalchemy_fns.update_manga_links(anilist_id, None, [mangaupdates_link])
            
            # Also store the URL in mangaupdates_details table
            sqlalchemy_fns.save_mangaupdates_url(anilist_id, mangaupdates_link)
            
            logging.info(f"Fetching data from MangaUpdates API for: {mangaupdates_link}")
            
            # Use the new API client instead of the spider
            api_client = MangaUpdatesAPIClient()
            result = api_client.get_series_full_data(mangaupdates_link)
            
            if result:
                # Save to database with both spider-compatible and full API data
                sqlalchemy_fns.save_manga_details(
                    result['spider_data'], 
                    anilist_id,
                    api_data=result['api_data']
                )
                logging.info(f"✅ Successfully fetched and saved MangaUpdates data via API")
            else:
                logging.warning("Failed to fetch MangaUpdates data from API, but continuing...")

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
                            'last_updated': manga_updates.last_updated_timestamp,
                            'rating': manga_updates.bayesian_rating,
                            'latest_chapter': manga_updates.latest_chapter
                        }
                    })
            except Exception as e:
                logging.error(f"Error emitting WebSocket update: {e}")
                # Continue execution even if WebSocket update fails

        return jsonify({
            "status": "success",
            "message": "Bato link added successfully" + 
                    (" and MangaUpdates data retrieved" if mangaupdates_link else ", but no MangaUpdates link found") +
                    (f". {bato_scrape_message}" if bato_scrape_message else ""),
            "extractedLinks": extracted_links,
            "bato_scraping": {
                "success": bato_scrape_success,
                "message": bato_scrape_message
            }
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