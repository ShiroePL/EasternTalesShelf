import json
import time
import requests
import mysql.connector
from db_config import conn
from datetime import datetime
import api_keys
# ANSI escape sequences for colors
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"


j = 0
how_many_anime_in_one_request = 50 #max 50
total_updated = 0
total_added = 0

def how_many_rows(query):
    """Add a pair of question and answer to the general table in the database"""
    global conn
    cursor = conn.cursor()
    cursor.execute(query)
    output = cursor.fetchall()
    print(f"{BLUE}Total number of rows in table: {cursor.rowcount}{RESET}")
    conn.commit()
    
    return output

def check_record(media_id):
    """Check if a record with the given media_id exists in the manga_list table in the database"""
    global conn
    check_record_query = "SELECT * FROM manga_list WHERE id_anilist = %s"
    cursor.execute(check_record_query, (media_id,))
    record = cursor.fetchone()
    return record

def update_querry_to_db(insert_query, insert_record):
    """Update a record in the manga_list table in the database"""
    global conn
    global cleaned_romaji
    cursor = conn.cursor()
    cursor.execute(insert_query, insert_record)
    print(f"{MAGENTA}updated record ^^ {CYAN}{cleaned_romaji}{RESET}")

def insert_querry_to_db(insert_query, insert_record, what_type_updated):
    """Insert a record into the manga_list table in the database"""
    global conn   
    cursor = conn.cursor()
    cursor.execute(insert_query, insert_record)
    if what_type_updated == "MANGA":
        print(f"{MAGENTA}...added ^^ manga to database.{RESET}")
    elif what_type_updated == "NOVEL":
        print(f"{MAGENTA}...added ^^ novel to database.{RESET}")

 
try: # open connection to database
    connection = conn
        # class cursor : Allows Python code to execute PostgreSQL command in a database session. Cursors are created by the connection.cursor() method
    cursor = connection.cursor()
        # need to take all records from database to compare entries
    # cheking if table even exists
    check_if_table_exists = "SHOW TABLES LIKE 'manga_list'"
    cursor.execute(check_if_table_exists)
    result = cursor.fetchone()
    if result:
        print(f"{GREEN}Table exists, next step...{RESET}")
    else:
        print(f"{RED}Table does not exist{RESET}")
        print(f"{RED}If there is no table, you need to first run 'take_full_manga_list.py'. This update program takes only most recent 50 entries. If you have updated more or didn't created table yet, please run the full list program.{RESET}")

    take_all_records = "select id_anilist, last_updated_on_site from manga_list"
    
    all_records = how_many_rows(take_all_records)
        # get all records
   
    total_anime = 0
    
    variables_in_api = {
    'page' : 1,
    'perPage' : how_many_anime_in_one_request,
    'userId' : api_keys.anilist_id # your anilist id, set in api_keys.py
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
    mediaList(userId: $userId, type: MANGA, sort: UPDATED_TIME_DESC) {
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

        #print(f"{RED}entry_createdAt_parsed : {cleanded_user_completedAt}{RESET}")
        updated_at_for_loop = updatedAt["updatedAt"]

        

        
        
        record = check_record(mediaId_parsed)
        #print(f"{RED}record : {record}{RESET}")
        
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
        if idMal_parsed is None:
            idMal_parsed = 0
        
        # Convert the Unix timestamp to a Python datetime object
        updatedAt_datetime = datetime.fromtimestamp(updatedAt_parsed)

        # Convert the datetime object to a string in the correct format
        updatedAt_parsed = updatedAt_datetime.strftime('%Y-%m-%d %H:%M:%S')

        # Convert the Unix timestamp to a Python datetime object
        entry_createdAt_datetime = datetime.fromtimestamp(entry_createdAt_parsed)

        # Convert the datetime object to a string in the correct format
        entry_createdAt_parsed = entry_createdAt_datetime.strftime('%Y-%m-%d %H:%M:%S')

        print(f"{GREEN}Checking for mediaId: {mediaId_parsed}{RESET}")

        if record:
            if record[18] is not None:
                # Check if record[16] is a string and convert it to datetime object
                if isinstance(record[18], str):
                    try:
                        db_datetime = datetime.strptime(record[18], '%Y-%m-%d %H:%M:%S')
                        db_timestamp = int(time.mktime(db_datetime.timetuple()))
                    except ValueError:
                        # Handle the exception if the date format is incorrect
                        print("Date format is incorrect")
                        db_timestamp = None
                else:
                    # If record[16] is already a datetime object
                    db_timestamp = int(time.mktime(record[18].timetuple()))
            else:
                db_timestamp = None

            if db_timestamp is not None and updatedAt_parsed is not None:
                updatedAt_timestamp = int(time.mktime(time.strptime(updatedAt_parsed, '%Y-%m-%d %H:%M:%S')))
            else:
                updatedAt_timestamp = None

            if db_timestamp != updatedAt_timestamp:         
                update_query = """
                UPDATE `manga_list` SET  
                    id_anilist = %s,
                    id_mal = %s,
                    title_english = %s,
                    title_romaji = %s,
                    on_list_status = %s,
                    status = %s,
                    media_format = %s,
                    all_chapters = %s,
                    all_volumes = %s,
                    chapters_progress = %s,
                    volumes_progress = %s,
                    score = %s,
                    reread_times = %s,
                    cover_image = %s,
                    is_favourite = %s,
                    anilist_url = %s,
                    mal_url = %s,
                    last_updated_on_site = %s,
                    entry_createdAt = %s,
                    user_startedAt = %s,
                    user_completedAt = %s,
                    notes = %s,
                    description = %s,
                    country_of_origin = %s,
                    media_start_date = %s,
                    media_end_date = %s,
                    genres = %s,
                    external_links = %s
                WHERE id_anilist = %s;
                """

                update_record = (
                    mediaId_parsed, idMal_parsed, cleaned_english, cleaned_romaji, on_list_status_parsed, status_parsed, format_parsed, 
                    chapters_parsed, volumes_parsed, progress_parsed, volumes_progress_parsed, score_parsed, repeat_parsed, large_parsed, 
                    isFavourite_parsed, siteUrl_parsed, mal_url_parsed, updatedAt_parsed, 
                    entry_createdAt_parsed, cleanded_user_startedAt, cleanded_user_completedAt, cleaned_notes, cleaned_description, 
                    country_parsed, media_startDate_parsed, media_endDate_parsed, genres_json, external_links_json, mediaId_parsed  # ID again for WHERE clause
                )
                    # using function from different file, I can't do this different 
                
                update_querry_to_db(update_query, update_record)
                
                #updated anime
                conn.commit()
                total_updated += 1
                

            else: # INSTEAD OF BREAKING, JUST SKIP TO NEXT ANIME BECAUSE NEXT ONE COULD BE NEW, NEED TO CHECK MORE ANIME
                print(f"{RED}No new updates for {RESET}{CYAN}{cleaned_romaji}{RESET}{RED}, going to next...{RESET}")
                
                    
        else:
            
            if format_parsed == "NOVEL":
                print(f"{RED}This novel is not in a table: {cleaned_romaji}{RESET}")
            elif format_parsed == "MANGA":
                print(f"{CYAN}This manga is not in a table: {cleaned_romaji}{RESET}")
            add_querry = """
                    INSERT INTO `manga_list` (
                        `id_anilist`, `id_mal`, `title_english`, `title_romaji`, `on_list_status`, `status`, `media_format`, 
                        `all_chapters`, `all_volumes`, `chapters_progress`, `volumes_progress`, `score`, `reread_times`, `cover_image`, 
                        `is_favourite`, `anilist_url`, `mal_url`, `last_updated_on_site`, `entry_createdAt`, `user_startedAt`, 
                        `user_completedAt`, `notes`, `description`, `country_of_origin`, `media_start_date`, `media_end_date`, `genres`, `external_links`
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                    """
                        # inserting variables to ^^ {x} 
            insert_record = (
                mediaId_parsed, idMal_parsed, cleaned_english, cleaned_romaji, on_list_status_parsed, status_parsed, format_parsed, 
                chapters_parsed, volumes_parsed, progress_parsed, volumes_progress_parsed, score_parsed, repeat_parsed, large_parsed, 
                isFavourite_parsed, siteUrl_parsed, mal_url_parsed, updatedAt_parsed, entry_createdAt_parsed, 
                cleanded_user_startedAt, cleanded_user_completedAt, cleaned_notes, cleaned_description, 
                country_parsed, media_startDate_parsed, media_endDate_parsed, genres_json, external_links_json
            )
                # using function from different file, I can't do this different 
            insert_querry_to_db(add_querry, insert_record, format_parsed)

            
            total_added+= 1 
             
    print(f"{YELLOW}Total added: {total_added}{RESET}")
    print(f"{MAGENTA}Total updated: {total_updated}{RESET}")
    conn.commit()
        
except mysql.connector.Error as e: #if cannot connect to database
    print("Error reading data from MySQL table", e)
finally: # close connection after completing program
    if connection.is_connected():
        connection.close()
        cursor.close()
        print("MySQL connection is closed")