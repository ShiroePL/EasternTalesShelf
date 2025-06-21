from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.functions.class_mangalist import db_session, ReadingHistory, MangaList, Users
from app.admin import admin_required
import logging
import datetime
from flask_cors import cross_origin
import requests

extension_bp = Blueprint('extension', __name__, url_prefix='/extension')

@extension_bp.route('/reading-time', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def receive_reading_time():
    """Endpoint for Chrome extension to submit reading time data"""
    # Handle OPTIONS request explicitly for CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
        
    try:
        # Verify request is coming from a Chrome extension
        origin = request.headers.get('Origin', '')
        if not origin.startswith('chrome-extension://'):
            logging.warning(f"Blocked unauthorized access attempt from origin: {origin}")
            return jsonify({
                'success': False,
                'message': 'Unauthorized: This API endpoint is only available for the Chrome extension'
            }), 403
            
        # Get data from request
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        title = data.get('title')
        url = data.get('url')
        reading_time = data.get('seconds')
        anilist_token = data.get('token')
        timestamp = data.get('timestamp')
        claimed_anilist_user_id = data.get('anilist_user_id')
        
        # Get the additional fields from the enhanced extension data
        manhwa_id = data.get('manhwaId')
        manhwa_title = data.get('manhwaTitle')
        chapter_id = data.get('chapterId')
        chapter_title = data.get('chapterTitle')
        is_total_update = data.get('totalTimeUpdate', False)
        print(f"Received data: {data}")
        if not all([title, url, reading_time]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # UPDATED: Require both token and user ID, and verification must succeed
        if not anilist_token or not claimed_anilist_user_id:
            logging.warning(f"Blocked request without proper authentication credentials")
            return jsonify({
                'success': False,
                'message': 'Unauthorized: AniList authentication credentials required'
            }), 403
        
        # Verify the token with AniList API
        verified_user = verify_anilist_token(anilist_token, claimed_anilist_user_id)
        if not verified_user:
            logging.warning(f"AniList token verification failed for claimed user ID: {claimed_anilist_user_id}")
            return jsonify({
                'success': False, 
                'message': 'Unauthorized: Invalid or mismatched AniList credentials'
            }), 403
            
        # User verification succeeded - find or create user in our database
        # Find user by AniList ID
        user = db_session.query(Users).filter(Users.anilist_id == claimed_anilist_user_id).first()
        
        user_id = None
        user_name = None
        if user:
            user_id = user.id
            user_name = user.username
            logging.info(f"Found user: {user_name} (ID: {user_id}) for AniList ID: {claimed_anilist_user_id}")
        else:
            logging.warning(f"User with AniList ID {claimed_anilist_user_id} exists on AniList but not in our database")
            return jsonify({
                'success': False,
                'message': 'Unauthorized: User exists on AniList but not registered in our system'
            }), 403
        
        # Log the received data
        logging.info(f"Received reading time data: {title}, {reading_time} seconds")
        if is_total_update:
            logging.info(f"This is a total time update for {manhwa_title} Chapter {chapter_id}")
        
        # Extract AniList ID from the manhwaId if possible
        anilist_id = None
        if manhwa_id and isinstance(manhwa_id, str):
            # Try to extract AniList ID from formats like "bato-12345"
            parts = manhwa_id.split('-')
            if len(parts) >= 2 and parts[1].isdigit():
                try:
                    # This could be an AniList ID in some cases
                    potential_anilist_id = int(parts[1])
                    # Validate against database
                    manga_entry = db_session.query(MangaList).filter(
                        MangaList.id_anilist == potential_anilist_id
                    ).first()
                    if manga_entry:
                        anilist_id = potential_anilist_id
                        logging.info(f"Matched reading to AniList ID: {anilist_id}")
                except (ValueError, Exception) as e:
                    logging.debug(f"Could not extract AniList ID from {manhwa_id}: {e}")
        
        # Store reading data in database
        try:
            # If this is a total time update, find and update any existing records first
            if is_total_update:
                existing_entry = None
                # Try to find by specific chapter information first
                if manhwa_id and chapter_id:
                    existing_entry = db_session.query(ReadingHistory).filter(
                        ReadingHistory.user_id == user_id,
                        ReadingHistory.anilist_id == anilist_id,
                        ReadingHistory.chapter == chapter_id
                    ).first()
                
                if existing_entry:
                    # Update the existing entry
                    existing_entry.seconds = reading_time
                    existing_entry.timestamp = datetime.datetime.fromtimestamp(timestamp/1000) if timestamp else datetime.datetime.now()
                    existing_entry.url = url
                    existing_entry.title = title
                    existing_entry.synced = True
                    db_session.commit()
                    logging.info(f"Updated existing reading entry with total time: {reading_time} seconds")
                    
                    # Return success after updating
                    return jsonify({
                        'success': True,
                        'message': 'Reading time data updated',
                        'data': {
                            'title': title,
                            'url': url,
                            'reading_time': reading_time,
                            'updated_at': datetime.datetime.now().isoformat(),
                            'user_id': user_id,
                            'user_name': user_name,
                            'manhwa_id': manhwa_id,
                            'chapter_id': chapter_id,
                            'action': 'updated'
                        }
                    })
            
            # Create new reading history entry
            new_entry = ReadingHistory(
                user_id=user_id,
                title=title,
                url=url,
                seconds=reading_time,
                timestamp=datetime.datetime.fromtimestamp(timestamp/1000) if timestamp else datetime.datetime.now(),
                username=user_name,
                anilist_id=anilist_id,
                chapter=chapter_id,
                synced=True
            )
            
            db_session.add(new_entry)
            db_session.commit()
            logging.info(f"Saved reading time data to database")
            
        except Exception as db_error:
            logging.error(f"Database error: {str(db_error)}")
            db_session.rollback()
            return jsonify({
                'success': False,
                'message': f'Database error: {str(db_error)}'
            }), 500
        
        # Return success
        return jsonify({
            'success': True,
            'message': 'Reading time data received',
            'data': {
                'title': title,
                'url': url,
                'reading_time': reading_time,
                'received_at': datetime.datetime.now().isoformat(),
                'user_id': user_id,
                'user_name': user_name,
                'manhwa_id': manhwa_id,
                'chapter_id': chapter_id,
                'action': 'created'
            }
        })
        
    except Exception as e:
        logging.exception("Error processing reading time data:")
        response = jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
        # Add CORS headers to error response as well
        if isinstance(response, tuple):
            response[0].headers.add('Access-Control-Allow-Origin', '*')
        else:
            response.headers.add('Access-Control-Allow-Origin', '*')
        return response

@extension_bp.route('/reading-time-batch', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def receive_reading_time_batch():
    """Endpoint for Chrome extension to submit multiple reading time entries in one request"""
    # Handle OPTIONS request explicitly for CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
        
    try:
        # Verify request is coming from a Chrome extension
        origin = request.headers.get('Origin', '')
        if not origin.startswith('chrome-extension://'):
            logging.warning(f"Blocked unauthorized access attempt from origin: {origin}")
            return jsonify({
                'success': False,
                'message': 'Unauthorized: This API endpoint is only available for the Chrome extension'
            }), 403
            
        # Get data from request
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('entries') or not isinstance(data.get('entries'), list):
            return jsonify({'success': False, 'message': 'No valid entries provided'}), 400
            
        entries = data.get('entries', [])
        anilist_token = data.get('token')
        claimed_anilist_user_id = data.get('anilist_user_id')
        
        logging.info(f"Received batch reading time data with {len(entries)} entries")
        
        # UPDATED: Require both token and user ID, and verification must succeed
        if not anilist_token or not claimed_anilist_user_id:
            logging.warning(f"Blocked batch request without proper authentication credentials")
            return jsonify({
                'success': False,
                'message': 'Unauthorized: AniList authentication credentials required'
            }), 403
        
        # Verify the token with AniList API once for all entries
        verified_user = verify_anilist_token(anilist_token, claimed_anilist_user_id)
        if not verified_user:
            logging.warning(f"AniList token verification failed for claimed user ID: {claimed_anilist_user_id}")
            return jsonify({
                'success': False, 
                'message': 'Unauthorized: Invalid or mismatched AniList credentials'
            }), 403
        
        # User verification succeeded - find user in our database
        # Find user by AniList ID
        user = db_session.query(Users).filter(Users.anilist_id == claimed_anilist_user_id).first()
        
        user_id = None
        user_name = None
        if user:
            user_id = user.id
            user_name = user.username
            logging.info(f"Found user: {user_name} (ID: {user_id}) for AniList ID: {claimed_anilist_user_id}")
        else:
            logging.warning(f"User with AniList ID {claimed_anilist_user_id} exists on AniList but not in our database")
            return jsonify({
                'success': False,
                'message': 'Unauthorized: User exists on AniList but not registered in our system'
            }), 403
        
        # Process each entry in the batch
        results = []
        for entry in entries:
            try:
                title = entry.get('title')
                url = entry.get('url')
                reading_time = entry.get('seconds')
                timestamp = entry.get('timestamp')
                manhwa_id = entry.get('manhwaId')
                manhwa_title = entry.get('manhwaTitle')
                chapter_id = entry.get('chapterId')
                chapter_title = entry.get('chapterTitle')
                is_total_update = entry.get('totalTimeUpdate', False)
                
                if not all([title, url, reading_time]):
                    results.append({
                        'success': False,
                        'message': 'Missing required fields',
                        'entry': entry
                    })
                    continue
                
                # Log the entry data
                logging.info(f"Processing batch entry: {title}, {reading_time} seconds")
                if is_total_update:
                    logging.info(f"This is a total time update for {manhwa_title} Chapter {chapter_id}")
                
                # Extract AniList ID from the manhwaId if possible
                anilist_id = None
                if manhwa_id and isinstance(manhwa_id, str):
                    # Try to extract AniList ID from formats like "bato-12345"
                    parts = manhwa_id.split('-')
                    if len(parts) >= 2 and parts[1].isdigit():
                        try:
                            # This could be an AniList ID in some cases
                            potential_anilist_id = int(parts[1])
                            # Validate against database
                            manga_entry = db_session.query(MangaList).filter(
                                MangaList.id_anilist == potential_anilist_id
                            ).first()
                            if manga_entry:
                                anilist_id = potential_anilist_id
                                logging.info(f"Matched reading to AniList ID: {anilist_id}")
                        except (ValueError, Exception) as e:
                            logging.debug(f"Could not extract AniList ID from {manhwa_id}: {e}")
                
                # Store reading data in database
                # Check for existing entry to update
                if is_total_update and manhwa_id and chapter_id:
                    existing_entry = db_session.query(ReadingHistory).filter(
                        ReadingHistory.user_id == user_id,
                        ReadingHistory.anilist_id == anilist_id,
                        ReadingHistory.chapter == chapter_id
                    ).first()
                    
                    if existing_entry:
                        # Update the existing entry
                        existing_entry.seconds = reading_time
                        existing_entry.timestamp = datetime.datetime.fromtimestamp(timestamp/1000) if timestamp else datetime.datetime.now()
                        existing_entry.url = url
                        existing_entry.title = title
                        existing_entry.synced = True
                        
                        results.append({
                            'success': True,
                            'message': 'Reading time data updated',
                            'action': 'updated',
                            'entry': entry
                        })
                        continue
                
                # Create new reading history entry
                new_entry = ReadingHistory(
                    user_id=user_id,
                    title=title,
                    url=url,
                    seconds=reading_time,
                    timestamp=datetime.datetime.fromtimestamp(timestamp/1000) if timestamp else datetime.datetime.now(),
                    username=user_name,
                    anilist_id=anilist_id,
                    chapter=chapter_id,
                    synced=True
                )
                
                db_session.add(new_entry)
                results.append({
                    'success': True,
                    'message': 'Reading time data received',
                    'action': 'created',
                    'entry': entry
                })
                
            except Exception as entry_error:
                logging.error(f"Error processing batch entry: {str(entry_error)}")
                results.append({
                    'success': False,
                    'message': f'Error: {str(entry_error)}',
                    'entry': entry
                })
        
        # Commit all changes at once
        try:
            db_session.commit()
            logging.info(f"Saved batch reading time data to database: {len(results)} entries")
        except Exception as db_error:
            db_session.rollback()
            logging.error(f"Database error during batch commit: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': f'Database error: {str(db_error)}',
                'results': results
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(entries)} reading time entries',
            'results': results
        })
        
    except Exception as e:
        logging.exception("Error processing batch reading time data:")
        response = jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
        if isinstance(response, tuple):
            response[0].headers.add('Access-Control-Allow-Origin', '*')
        else:
            response.headers.add('Access-Control-Allow-Origin', '*')
        return response

@extension_bp.route('/reading-data', methods=['GET'])
@login_required
@admin_required
def get_reading_data():
    """Get all reading history data (admin only)"""
    try:
        # Get reading data from database
        query = db_session.query(ReadingHistory)
        
        # Optional filter by username/user_id
        user_id = request.args.get('user_id')
        username = request.args.get('username')
        
        if user_id:
            query = query.filter(ReadingHistory.user_id == user_id)
        elif username:
            query = query.filter(ReadingHistory.username == username)
            
        # Get the data
        reading_data = query.order_by(ReadingHistory.timestamp.desc()).all()
        
        # Format data for response
        formatted_data = []
        for entry in reading_data:
            formatted_data.append({
                'id': entry.id,
                'user_id': entry.user_id,
                'username': entry.username,
                'title': entry.title,
                'url': entry.url,
                'seconds': entry.seconds,
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'anilist_id': entry.anilist_id,
                'chapter': entry.chapter
            })
            
        return jsonify({
            'success': True,
            'count': len(formatted_data),
            'data': formatted_data
        })
    except Exception as e:
        logging.exception("Error retrieving reading data:")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Function to verify AniList token with AniList API
def verify_anilist_token(token, claimed_user_id):
    """
    Verify that the provided token is valid and belongs to the claimed user ID
    
    Args:
        token: The AniList access token
        claimed_user_id: The user ID claimed by the extension
        
    Returns:
        dict: User information if verification succeeds, None otherwise
    """
    try:
        # AniList GraphQL query to get the authenticated user's info
        query = """
        query {
            Viewer {
                id
                name
                avatar {
                    large
                }
            }
        }
        """
        
        # Make request to AniList API
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code != 200:
            logging.error(f"AniList API error: {response.status_code}, {response.text}")
            return None
            
        data = response.json()
        viewer = data.get('data', {}).get('Viewer')
        
        if not viewer:
            logging.error("No viewer data returned from AniList")
            return None
            
        actual_user_id = viewer.get('id')
        
        # Check if the claimed user ID matches the actual user ID
        if str(actual_user_id) != str(claimed_user_id):
            logging.warning(f"User ID mismatch: Claimed {claimed_user_id}, Actual {actual_user_id}")
            return None
            
        # User verification succeeded
        logging.info(f"Successfully verified AniList token for user: {viewer.get('name')} (ID: {actual_user_id})")
        return viewer
        
    except Exception as e:
        logging.exception(f"Error verifying AniList token: {str(e)}")
        return None 