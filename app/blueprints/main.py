from flask import Blueprint, render_template, jsonify, request, send_from_directory, current_app
from flask_login import login_required, current_user
import os
import json
import logging
from datetime import datetime, timedelta
from app.functions import sqlalchemy_fns
import app.download_covers as download_covers
from threading import Thread
from app.utils.token_encryption import encrypt_token

main_bp = Blueprint('main', __name__)

# Utility functions for templates
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

def save_user_color_settings(user_id, color_settings):
    # Create directory if it doesn't exist
    settings_dir = os.path.join('app', 'user_settings')
    os.makedirs(settings_dir, exist_ok=True)
    
    # Save the color settings to a file or database
    settings_path = os.path.join(settings_dir, f'user_color_settings_{user_id}.json')
    with open(settings_path, 'w') as f:
        json.dump(color_settings, f)

@main_bp.route('/')
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
    return render_template('pages/index.html', manga_entries=manga_entries, mangaupdates_details=mangaupdates_details, color_settings=color_settings)


@main_bp.route('/animelist')
@login_required
def animelist():
    """Display the anime list page"""
    try:
        # Query the database for anime list entries using SQLAlchemy with text()
        from sqlalchemy import text
        from app.functions.class_mangalist import db_session
        
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

@main_bp.route('/save_color_settings', methods=['POST'])
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

@main_bp.route('/get_color_settings', methods=['GET'])
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

@main_bp.route('/dev_covers/<filename>')
def dev_covers(filename):
    if os.getenv('FLASK_ENV') == 'development':
        # Path to your local backup folder
        dev_covers_path = r"G:\backup_vpsa_calego_dockera_foldera\EasternTalesShelf\app\static\covers"
        try:
            return send_from_directory(dev_covers_path, filename)
        except Exception as e:
            logging.error(f"Error serving file {filename}: {str(e)}")
            return jsonify({'error': str(e)}), 500