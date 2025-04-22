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
    # Load user-specific color settings
    color_settings = load_color_settings()
    
    # Determine if we're in development mode
    is_development = os.getenv('FLASK_ENV') == 'development'
    
    # Pass only color settings to the template.
    # The manga data will be loaded dynamically via GraphQL
    return render_template('pages/index.html', 
                           color_settings=color_settings, 
                           isDevelopment=is_development)


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

@main_bp.route('/update_cover_status', methods=['POST'])
@login_required
def update_cover_status():
    """Update the cover download status for a manga entry"""
    try:
        data = request.get_json()
        anilist_id = data.get('anilist_id')
        is_downloaded = data.get('is_downloaded', False)
        
        if not anilist_id:
            return jsonify({'success': False, 'message': 'AniList ID is required'}), 400
        
        # Update the status in the database
        from app.functions.class_mangalist import db_session, MangaList
        
        manga = db_session.query(MangaList).filter_by(id_anilist=anilist_id).first()
        if manga:
            manga.is_cover_downloaded = is_downloaded
            db_session.commit()
            return jsonify({'success': True, 'message': 'Cover status updated'})
        else:
            return jsonify({'success': False, 'message': 'Manga not found'}), 404
    
    except Exception as e:
        db_session.rollback()
        logging.exception("Error updating cover status:")
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/api/download-statuses')
@login_required
def get_download_statuses():
    """Get all download statuses for manga entries"""
    try:
        # Get download statuses using the existing function
        download_statuses = sqlalchemy_fns.get_download_statuses()
        
        # Format the response
        formatted_statuses = [
            {
                'anilist_id': status['anilist_id'], 
                'status': status['status'].lower()
            } 
            for status in download_statuses
        ]
        
        return jsonify({
            'success': True,
            'statuses': formatted_statuses
        })
    except Exception as e:
        logging.exception("Error fetching download statuses:")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500