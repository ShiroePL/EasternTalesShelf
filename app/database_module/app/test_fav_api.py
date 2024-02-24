import json
import requests
import mysql.connector
from db_config import conn
import api_keys

# Terminal color codes
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"

user_id = api_keys.anilist_id
page = 0
per_page_favorite = 25
has_next_page = True
connection = conn
cursor = connection.cursor()

# Fetch already favorite manga IDs to optimize updates
cursor.execute("SELECT id_anilist FROM manga_list WHERE is_favourite = 0")
already_favorites = {row[0] for row in cursor.fetchall()}

api_request = '''
    query ($page: Int, $id: Int) {
        User(id: $id) {
            id
            name
            favourites {
                manga(page: $page) {
                    pageInfo {
                        total
                        perPage
                        currentPage
                        lastPage
                        hasNextPage
                    }
                    nodes {
                        id
                        title {
                            english
                        }
                    }
                }
            }
        }
    }
    '''
url = 'https://graphql.anilist.co'
while has_next_page:
    variables_in_api = {'page': page, 'id': user_id}
    response_from_anilist = requests.post(url, json={'query': api_request, 'variables': variables_in_api})
    parsed_json = json.loads(response_from_anilist.text)

    ids_to_update = [fav_manga["id"] for fav_manga in parsed_json["data"]["User"]["favourites"]["manga"]["nodes"] if fav_manga["id"] not in already_favorites]

    print(f"{RED}Page {page}{RESET}")
    # If there are new favorites to update
    if ids_to_update:
        update_query = "UPDATE manga_list SET is_favourite = 0 WHERE id_anilist = %s"
        try:
            # Execute updates in a batch
            for fav_manga_id in ids_to_update:
                cursor.execute(update_query, (fav_manga_id,))
            # Commit all changes at once
            connection.commit()
            print(f"{GREEN}Updated {len(ids_to_update)} mangas to favorite{RESET}")
        except mysql.connector.Error as err:
            print(f"{RED}Failed to batch update mangas: {err}{RESET}")

    has_next_page = parsed_json["data"]["User"]["favourites"]["manga"]["pageInfo"]["hasNextPage"]
    page += 1
