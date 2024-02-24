import requests
from PIL import Image
from io import BytesIO
import os
import mysql.connector
from datetime import datetime
from app.config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
# For MySQL/MariaDB
from mysql.connector import Error


def download_and_convert_image(image_url, image_id, save_dir='app/static/covers'):
    try:
        # Download the image
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))

        # Ensure the save directory exists
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Prepare file paths
        webp_path = os.path.join(save_dir, f"{image_id}.webp")
        avif_path = os.path.join(save_dir, f"{image_id}.avif")

        # Convert and save in WebP format using Pillow
        image.save(webp_path, format="WEBP", quality=80)

        # Use ffmpeg directly for AVIF conversion
        # First, save a temporary PNG for ffmpeg to convert
        temp_png_path = os.path.join(save_dir, f"{image_id}_temp.png")
        image.save(temp_png_path, format="PNG")
        
        # Call ffmpeg to convert PNG to AVIF
        ffmpeg_command = [
            'ffmpeg',
            '-y',  # Automatically overwrite existing files 
            '-loglevel', 'error',  # Adjust logging level
            '-i', temp_png_path, 
            '-c:v', 'libaom-av1', 
            '-pix_fmt', 'yuv420p', 
            '-crf', '30',  # You can adjust CRF (quality) as needed
            '-strict', 'experimental',
            avif_path
        ]
        subprocess.run(ffmpeg_command, check=True)
        
        # Remove the temporary PNG file
        os.remove(temp_png_path)

        return True
    except Exception as e:
        print(f"Error processing image {image_id}: {e}")
        return False


def download_covers_concurrently(ids_to_download, manga_entries):
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_id = {
            executor.submit(download_and_convert_image, entry['cover_image'], str(entry['id_anilist'])): entry['id_anilist']
            for entry in manga_entries if entry['id_anilist'] in ids_to_download
        }

        successful_ids = []
        for future in as_completed(future_to_id):
            image_id = future_to_id[future]
            try:
                if future.result():
                    print(f"Successfully downloaded and converted cover for ID {image_id}")
                    successful_ids.append(image_id)
                else:
                    print(f"Failed to download or convert cover for ID {image_id}")
            except Exception as e:
                print(f"Error downloading cover for ID {image_id}: {e}")

        return successful_ids

# def get_covers(testing=False):
#     session = get_session()

#     try:
#         # Choose the table based on the testing flag
#         if testing:
#             manga_list_query = session.query(MangaList.id_anilist, MangaList.cover_image).filter(MangaList.table_name == 'manga_list2')
#         else:
#             manga_list_query = session.query(MangaList.id_anilist, MangaList.cover_image)

#         manga_list = manga_list_query.all()
        
#         # Loop through each manga entry
#         for manga in manga_list:
#             image_id = manga.id_anilist
#             image_url = manga.cover_image
            
#             # Ensure image_url is not None or empty
#             if image_url:
#                 # Call the function to download, convert, and save images
#                 webp_path, avif_path = download_convert_and_save_image(image_url, str(image_id))
#                 print(f"Processed {image_id}: WebP at {webp_path}, AVIF at {avif_path}")

#                 # Update the cover download status in the database
#                 update_cover_download_status(image_id, True)

#     except Exception as e:
#         print("Error while processing covers", e)
#     finally:
#         session.close()


