import json
import time
import requests
import sqlite3
import argparse
import sys

from tqdm import tqdm
from datetime import datetime

# ANSI escape sequences for colors
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"



def start_backup(input_value, db_type, logger):
    i = 1
    j = 0
    how_many_anime_in_one_request = 50 #max 50
    total_updated = 0
    total_added = 0

    logger(f"{YELLOW}Database type: {db_type}{RESET}")
    conn = sqlite3.connect('anilist_db.db')
    

    
    #need to fetch id from anilist API for user name
    # id_or_name has only digits
    if not input_value.isdigit():
        variables_in_api = {
            'name' : input_value
        }

        api_request  = '''
            query ($name: String) {
                User(name: $name) {
                    id
                    name
                    }
                }
            '''
        url = 'https://graphql.anilist.co'
            # sending api request
        response_frop_anilist = requests.post(url, json={'query': api_request, 'variables': variables_in_api})
            # take api response to python dictionary to parse json
        parsed_json = json.loads(response_frop_anilist.text)
        user_id = parsed_json["data"]["User"]["id"]
        logger(f"{BLUE}your user id is: {GREEN}{user_id}{RESET}")
        



    def how_many_rows(query):
        """Add a pair of question and answer to the general table in the database"""
        
        cursor = conn.cursor()
        cursor.execute(query)
        output = cursor.fetchall()
        logger(f"{BLUE}Total number of rows in table: {cursor.rowcount}{RESET}")
        #logger(f"{BLUE}Total number of rows in table: {cursor.rowcount}{RESET}")
        conn.commit()
            #wait 1 second so you can see number of rows in table
        time.sleep(1)
        return output

    def check_record(media_id):
        """Check if a record with the given media_id exists in the manga_list table in the database"""
        
        check_record_query = "SELECT * FROM manga_list WHERE id_anilist = ?"
        cursor.execute(check_record_query, (media_id,))
        record = cursor.fetchone()
        return record

    def update_querry_to_db(insert_query, insert_record):
        """Update a record in the manga_list table in the database"""
        
        global cleaned_romaji
        cursor = conn.cursor()
        cursor.execute(insert_query, insert_record)
        logger(f"{BLUE}updated record ^^ {cleaned_romaji}{RESET}")

    def insert_querry_to_db(insert_query, insert_record, what_type_updated):
        """Insert a record into the manga_list table in the database"""
         
        cursor = conn.cursor()
        cursor.execute(insert_query, insert_record)
        if what_type_updated == "MANGA":
            logger(f"{MAGENTA}...added ^^ manga to database.{RESET}")
        elif what_type_updated == "NOVEL":
            logger(f"{MAGENTA}...added ^^ novel to database.{RESET}")
        
    try: # open connection to database
        
        cursor = conn.cursor()


        check_if_table_exists = "SELECT name FROM sqlite_master WHERE type='table' AND name='manga_list'"
        
        cursor.execute(check_if_table_exists)
        result = cursor.fetchone()
        if result:
            logger(f"{GREEN}Table exists{RESET}")
        else:
            logger(f"{RED}Table does not exist{RESET}")
            logger(f"{RED}Creating table{RESET}")
            create_table_query = """CREATE TABLE manga_list (
                id_default INTEGER PRIMARY KEY AUTOINCREMENT,
                id_anilist INTEGER NOT NULL,
                id_mal INTEGER DEFAULT NULL,
                title_english TEXT DEFAULT NULL,
                title_romaji TEXT DEFAULT NULL,
                on_list_status TEXT DEFAULT NULL,
                status TEXT DEFAULT NULL,
                media_format TEXT DEFAULT NULL,
                all_chapters INTEGER DEFAULT 0,
                all_volumes INTEGER DEFAULT 0,
                chapters_progress INTEGER DEFAULT 0,
                volumes_progress INTEGER DEFAULT 0,
                score REAL DEFAULT 0,
                reread_times INTEGER DEFAULT 0,
                cover_image TEXT DEFAULT NULL,
                is_favourite INTEGER DEFAULT 0,
                anilist_url TEXT DEFAULT NULL,
                mal_url TEXT DEFAULT NULL,
                last_updated_on_site TEXT DEFAULT NULL,
                entry_createdAt TEXT DEFAULT NULL,
                user_startedAt TEXT DEFAULT 'not started',
                user_completedAt TEXT DEFAULT 'not completed',
                notes TEXT DEFAULT NULL,
                description TEXT DEFAULT NULL,
                country_of_origin TEXT DEFAULT NULL,
                media_start_date TEXT DEFAULT 'media not started',
                media_end_date TEXT DEFAULT 'media not ended',
                genres TEXT DEFAULT 'none genres provided',
                external_links TEXT DEFAULT 'none links associated'
            );

            """
            cursor.execute(create_table_query)
            logger(f"{GREEN}Table created successfully in MySQL{RESET}")
            # need to take all records from database to compare entries
        take_all_records = "select id_anilist, last_updated_on_site from manga_list"
        
        #cursor.execute(take_all_records)
        all_records = how_many_rows(take_all_records)
            # get all records
        
        # Customize the progress bar format
        
        
        has_next_page = True
        
        while has_next_page:
            
            variables_in_api = {
            'page' : i,
            'perPage' : how_many_anime_in_one_request,
            'userId' : user_id
            }

            api_request  = '''
                query ($page: Int, $perPage: Int, $userId: Int) {
            Page(page: $page, perPage: $perPage) {
            pageInfo {
            perPage
            currentPage
            lastPage
            hasNextPage
            }
            mediaList(userId: $userId, type: MANGA) {
            status
            mediaId
            score
            progress
            progressVolumes
            repeat
            updatedAt
            createdAt
            startedAt {
                year
                month
                day
            }
            completedAt {
                year
                month
                day
            }
            media {
                title {
                romaji
                english
                }
                idMal
                format
                status
                description
                chapters
                volumes
                coverImage {
                large
                }
                isFavourite
                siteUrl
                countryOfOrigin
                startDate {
                year
                month
                day
            }
            endDate {
                year
                month
                day
            }
            genres
            externalLinks {
                url
            }
            }
            notes
                }
            }
            }
                '''
            url = 'https://graphql.anilist.co'
                # sending api request
            response_frop_anilist = requests.post(url, json={'query': api_request, 'variables': variables_in_api})

                # take api response to python dictionary to parse json
            parsed_json = json.loads(response_frop_anilist.text)
            
            logger(f"{RED}page {i}{RESET}")

            has_next_page = parsed_json["data"]["Page"]["pageInfo"]["hasNextPage"]
        # this variable is for adding new record, it needs to be the same as amount of all records in database to fullfill condition to add record 
            # total_updated = 0
            # total_added = 0
            # this loop is defined by how many perPage is on one request (50 by default and max)
            for j in range(len(parsed_json["data"]["Page"]["mediaList"])):   # it needs to add one anime at 1 loop go

                on_list_status = mediaId = score = progress = volumes_progress = repeat = updatedAt = entry_createdAt = notes = parsed_json["data"]["Page"]["mediaList"][j]
                
                    # title
                english = romaji = parsed_json["data"]["Page"]["mediaList"][j]["media"]["title"]
                    # mediaList - media
                idMal = formatt = status  = chapters = volumes = isFavourite = siteUrl = description = country = genres = parsed_json["data"]["Page"]["mediaList"][j]["media"]
                    # coverimage
                large = parsed_json["data"]["Page"]["mediaList"][j]["media"]["coverImage"]
                    # user startedAt
                user_startedAt = parsed_json["data"]["Page"]["mediaList"][j]["startedAt"]
                    # user completedAt
                user_completedAt = parsed_json["data"]["Page"]["mediaList"][j]["completedAt"]
                    # media startedAt
                media_startDate = parsed_json["data"]["Page"]["mediaList"][j]["media"]["startDate"]
                    # media completedAt
                media_endDate = parsed_json["data"]["Page"]["mediaList"][j]["media"]["endDate"]
                    # media external links
                media_externalLinks = parsed_json["data"]["Page"]["mediaList"][j]["media"]["externalLinks"]

                on_list_status_parsed = on_list_status["status"]
                mediaId_parsed = mediaId["mediaId"]
                score_parsed = score["score"]
                progress_parsed = progress["progress"]
                volumes_progress_parsed = volumes_progress["progressVolumes"]
                repeat_parsed = repeat["repeat"]
                english_parsed = english["english"]
                romaji_parsed = romaji["romaji"]
                idMal_parsed = idMal["idMal"]
                format_parsed = formatt["format"]
                status_parsed = status["status"]
                
                updatedAt_parsed = updatedAt["updatedAt"]
                
                chapters_parsed = chapters["chapters"]
                volumes_parsed = volumes["volumes"]
                large_parsed = large["large"]
                isFavourite_parsed = isFavourite["isFavourite"]
                siteUrl_parsed = siteUrl["siteUrl"]
                notes_parsed = notes["notes"]
                description_parsed = description["description"]
                entry_createdAt_parsed = entry_createdAt["createdAt"]
                country_parsed = country["countryOfOrigin"]

                    # started at 
                user_startedAt_year = user_startedAt["year"]
                user_startedAt_month = user_startedAt["month"]
                user_startedAt_day = user_startedAt["day"]
                
                    # completed at
                user_completedAt_year = user_completedAt["year"]
                user_completedAt_month = user_completedAt["month"]
                user_completedAt_day = user_completedAt["day"]

                    # media start date
                media_startDate_year = media_startDate["year"]
                media_startDate_month = media_startDate["month"]
                media_startDate_day = media_startDate["day"]
                
                    # media end date
                media_endDate_year = media_endDate["year"]
                media_endDate_month = media_endDate["month"]
                media_endDate_day = media_endDate["day"]


                # Initialize an empty list to store the parsed URLs
                media_externalLinks_parsed = []

                # Iterate through each item in the media_externalLinks list
                for link in media_externalLinks:
                    # Extract the URL and append it to the media_externalLinks_parsed list
                    url = link["url"]
                    media_externalLinks_parsed.append(url)

                # Assuming external_links is a Python list
                external_links_json = json.dumps(media_externalLinks_parsed)
                # Initialize an empty list to store the parsed URLs
                # Extract genres
                genres_parsed = genres['genres']

                # Convert genres list to JSON string
                genres_json = json.dumps(genres_parsed)

                    # cleaning strings and formating
                cleaned_english = str(english_parsed).replace("'" , '"')
                cleaned_romaji = str(romaji_parsed).replace("'" , '"')
                cleaned_notes = str(notes_parsed).replace("'" , '"')
                isFavourite_parsed = str(isFavourite_parsed).replace("True" , "1")
                isFavourite_parsed = str(isFavourite_parsed).replace("False" , "0")
                cleaned_description = str(description_parsed).replace("<br><br>" , '<br>')
                cleaned_description = str(cleaned_description).replace("'" , '"')       
                mal_url_parsed = "https://myanimelist.net/manga/" + str(idMal_parsed)

    
                    # reformating user started and completed to date format from sql
                user_startedAt_parsed = str(user_startedAt_year) + "-" + str(user_startedAt_month) + "-" + str(user_startedAt_day)
                user_completedAt_parsed = str(user_completedAt_year) + "-" + str(user_completedAt_month) + "-" + str(user_completedAt_day)

                    # reformating MEDIA start date and completed to date format from sql
                media_startDate_parsed = str(media_startDate_year) + "-" + str(media_startDate_month) + "-" + str(media_startDate_day)
                media_endDate_parsed = str(media_endDate_year) + "-" + str(media_endDate_month) + "-" + str(media_endDate_day)

                    # if null make null to add to databese user started and completed
                cleanded_user_startedAt = user_startedAt_parsed.replace('None-None-None' , 'not started')
                cleanded_user_completedAt = user_completedAt_parsed.replace('None-None-None' , 'not completed')
                chapters_parsed = '0' if chapters_parsed is None else chapters_parsed
                volumes_parsed = '0' if volumes_parsed is None else volumes_parsed

                #logger(f"{RED}entry_createdAt_parsed : {cleanded_user_completedAt}{RESET}")
                updated_at_for_loop = updatedAt["updatedAt"]

                
    
                
                tqdm.write(f"{GREEN}Checking for mediaId: {mediaId_parsed}{RESET}")
                record = check_record(mediaId_parsed)
                #logger(f"{RED}record : {record}{RESET}")
                
                if entry_createdAt_parsed == 'NULL':
                    created_at_for_db = 'NULL'
                elif entry_createdAt_parsed == 0:
                    created_at_for_db = 'NULL'
                else:
                    created_at_for_db = f"FROM_UNIXTIME({entry_createdAt_parsed})"

                if updatedAt_parsed == 'NULL':
                    updatedAt_parsed_for_db = 'NULL'
                elif updatedAt_parsed == 0:
                    updatedAt_parsed_for_db = 'NULL'
                else:
                    updatedAt_parsed_for_db = f"FROM_UNIXTIME({updatedAt_parsed})"

                #logger("idMal_parsed : ", idMal_parsed)
                if idMal_parsed is None:
                    idMal_parsed = 0
                #logger("changed idMal_parsed : ", idMal_parsed)
                # Convert the Unix timestamp to a Python datetime object
                updatedAt_datetime = datetime.fromtimestamp(updatedAt_parsed)

                # Convert the datetime object to a string in the correct format
                updatedAt_parsed = updatedAt_datetime.strftime('%Y-%m-%d %H:%M:?')

                # Convert the Unix timestamp to a Python datetime object
                entry_createdAt_datetime = datetime.fromtimestamp(entry_createdAt_parsed)

                # Convert the datetime object to a string in the correct format
                entry_createdAt_parsed = entry_createdAt_datetime.strftime('%Y-%m-%d %H:%M:?')
                #logger("cleanded_user_startedAt : ", cleanded_user_startedAt)
                #logger("cleanded_user_completedAt : ", cleanded_user_completedAt)
                
                # rekor[18] is last_updated_on_site
                if record:
                    if record[18] is not None:
                        # Check if record[18] is a string and convert it to datetime object
                        if isinstance(record[18], str):
                            try:
                                db_datetime = datetime.strptime(record[18], '%Y-%m-%d %H:%M:?')
                                db_timestamp = int(time.mktime(db_datetime.timetuple()))
                            except ValueError:
                                # Handle the exception if the date format is incorrect
                                logger("Date format is incorrect")
                                db_timestamp = None
                        else:
                            # If record[18] is already a datetime object
                            db_timestamp = int(time.mktime(record[18].timetuple()))
                    else:
                        db_timestamp = None

                    if db_timestamp is not None and updatedAt_parsed is not None:
                        updatedAt_timestamp = int(time.mktime(time.strptime(updatedAt_parsed, '%Y-%m-%d %H:%M:?')))
                    else:
                        updatedAt_timestamp = None

                    # logger(f"updatedAt_parsed: {updatedAt_parsed}")
                    # logger("db_timestamp: " + str(db_timestamp))
                    # logger("updatedAt_timestamp: " + str(updatedAt_timestamp))
                    # logger(f"rekors 18 : {record[18]} for anime {romaji_parsed}")
                    #       
                    if db_timestamp != updatedAt_timestamp:
                        
                    #if record[18] != updatedAt_parsed:
                        update_query = """
                        UPDATE `manga_list` SET  
                            id_anilist = ?,
                            id_mal = ?,
                            title_english = ?,
                            title_romaji = ?,
                            on_list_status = ?,
                            status = ?,
                            media_format = ?,
                            all_chapters = ?,
                            all_volumes = ?,
                            chapters_progress = ?,
                            volumes_progress = ?,
                            score = ?,
                            reread_times = ?,
                            cover_image = ?,
                            is_favourite = ?,
                            anilist_url = ?,
                            mal_url = ?,
                            last_updated_on_site = ?,
                            entry_createdAt = ?,
                            user_startedAt = ?,
                            user_completedAt = ?,
                            notes = ?,
                            description = ?,
                            country_of_origin = ?,
                            media_start_date = ?,
                            media_end_date = ?,
                            genres = ?,
                            external_links = ?
                        WHERE id_anilist = ?;
                        """

                        update_record = (
                            mediaId_parsed, idMal_parsed, cleaned_english, cleaned_romaji, on_list_status_parsed, status_parsed, format_parsed, 
                            chapters_parsed, volumes_parsed, progress_parsed, volumes_progress_parsed, score_parsed, repeat_parsed, large_parsed, 
                            isFavourite_parsed, siteUrl_parsed, mal_url_parsed, updatedAt_parsed, 
                            entry_createdAt_parsed, cleanded_user_startedAt, cleanded_user_completedAt, cleaned_notes, cleaned_description, 
                            country_parsed, media_startDate_parsed, media_endDate_parsed, genres_json, external_links_json, mediaId_parsed  # ID again for WHERE clause
                        )

                        # Execute the query
                        update_querry_to_db(update_query, update_record)


                        total_updated += 1
                        

                else:
                    if format_parsed == "NOVEL":
                        logger(f"{RED}This novel is not in a table: {cleaned_romaji}{RESET}")
                    elif format_parsed == "MANGA":
                        logger(f"{CYAN}This manga is not in a table: {cleaned_romaji}{RESET}")

                    
                        # building querry to insert to table
                    insert_query = """
                    INSERT INTO `manga_list` (
                        `id_anilist`, `id_mal`, `title_english`, `title_romaji`, `on_list_status`, `status`, `media_format`, 
                        `all_chapters`, `all_volumes`, `chapters_progress`, `volumes_progress`, `score`, `reread_times`, `cover_image`, 
                        `is_favourite`, `anilist_url`, `mal_url`, `last_updated_on_site`, `entry_createdAt`, `user_startedAt`, 
                        `user_completedAt`, `notes`, `description`, `country_of_origin`, `media_start_date`, `media_end_date`, `genres`, `external_links`
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                    """

                    insert_record = (
                        mediaId_parsed, idMal_parsed, cleaned_english, cleaned_romaji, on_list_status_parsed, status_parsed, format_parsed, 
                        chapters_parsed, volumes_parsed, progress_parsed, volumes_progress_parsed, score_parsed, repeat_parsed, large_parsed, 
                        isFavourite_parsed, siteUrl_parsed, mal_url_parsed, updatedAt_parsed, entry_createdAt_parsed, 
                        cleanded_user_startedAt, cleanded_user_completedAt, cleaned_notes, cleaned_description, 
                        country_parsed, media_startDate_parsed, media_endDate_parsed, genres_json, external_links_json
                    )


                    
                    
                    
                        # using function from different file, I can't do this different
                    #logger("insert record: ", insert_record) #uncomment to see what is going to be inserted
                    insert_querry_to_db(insert_query, insert_record, format_parsed)
                    total_added+= 1    
                    
            logger(f"{YELLOW}Total added: {total_added}{RESET}")
            logger(f"{MAGENTA}Total updated: {total_updated}{RESET}")
            conn.commit()
            
            i += 1

    
    except Exception as e:
        logger(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Backup utility for manga list")
    parser.add_argument("--input_value", type=str, required=True, help="Input value for the backup")
    parser.add_argument("--db_type", type=str, choices=["file", "mariadb"], required=True, help="Database type")
    
    args = parser.parse_args()
    
    # Define a simple logger function to print to stdout
    def logger(message):
        print(message)

    # Call the start_backup function with arguments
    start_backup(args.input_value, args.db_type, logger)