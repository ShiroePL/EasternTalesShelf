
import app.download_covers as download_covers
from app.functions import sqlalchemy_fns as sqlalchemy_fns
from flask import Flask, render_template, current_app, jsonify, request, url_for
import json
from app.config import is_development_mode, database_type 
from app.config import database_type # "mariadb" or "sql_lite"

import os
import requests

app = Flask(__name__)


# @app.template_filter('versioned')
# def versioned_static(filename):
#     # Manually specify the path to the 'app/static' directory
#     static_dir = 'app/static'  # Adjust this path based on your project structure
#     file_path = os.path.join(app.root_path, static_dir, filename)
#     print("file_path: ", file_path)
#     try:
#         last_modified_time = int(os.path.getmtime(file_path))
#         return url_for('static', filename=filename) + f'?v={last_modified_time}'
#     except OSError:
#         return url_for('static', filename=filename)





@app.context_processor
def inject_debug():
    # Directly print out the FLASK_ENV variable
    print("FLASK_ENV: ", os.getenv('FLASK_ENV'))
    # printing in what mode the program is runned
    print("isDevelopment?: ", is_development_mode.DEBUG)
    return dict(isDevelopment=is_development_mode.DEBUG)


app.config['DEBUG'] = bool(is_development_mode.DEBUG)



# Route for your home page
@app.route('/')
def home():
    # Fetch the 10 newest manga entries.
    # Example usage
# manga_entries = ...
# ids_to_download = ...
# download_covers_concurrently(ids_to_download, manga_entries)

    manga_entries = sqlalchemy_fns.get_manga_list_alchemy()

    if ids_to_download := [
        entry['id_anilist']
        for entry in manga_entries
        if not entry['is_cover_downloaded']
    ]:
        try:
            if successful_ids := download_covers.download_covers_concurrently(
                ids_to_download, manga_entries
            ):
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





@app.route('/homepage')
def homepage():
    # Fetch the 10 newest manga entries.
    # manga_entries = anilist_api_request.get_10_newest_entries('MANGA')
    
    # Pass the entries to the template.
    #return render_template('portfoli_testing_something.html')



# Route for handling the log sync functionality
@app.route('/log_sync', methods=['POST'])
def log_sync():
    print('Sync successful')  # Print message to console
    return '', 204  # Return an empty response


@app.route('/sync', methods=['POST'])
def sync_with_fastapi():
    # Check if app is in development mode before proceeding
    if not app.config['DEBUG']:
        # If not in debug mode, return a custom message
        return jsonify({
            "status": "error",
            "message": "Nice try, but you can't do that"
        }), 403  # 403 Forbidden status code

    try:
        # Replace the URL with your actual FastAPI server address
        url = "http://10.147.17.133:8057/sync"
        response = requests.post(url)

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


@app.route('/add_bato', methods=['POST'])
def add_bato_link():
    # Check if app is in development mode before proceeding
    if not app.config['DEBUG']:
        # If not in debug mode, return a custom message
        return jsonify({
            "status": "error",
            "message": "Nice try, but you can't do that"
        }), 403  # 403 Forbidden status code

    try:
        data = request.get_json()
        anilist_id = data.get('anilistId')
        bato_link = data.get('batoLink')  # Make sure to send this from your JS



        # Then, update the manga entry with the provided Bato link
        sqlalchemy_fns.add_bato_link(anilist_id, bato_link)

        return jsonify({"message": "Bato link updated successfully."}), 200
    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"An error occurred while adding bato link: {str(e)}",
                }
            ),
            500,
        )


    

if __name__ == '__main__':
    app.run(host='10.147.17.21', port=5000)




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