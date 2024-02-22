import mysql.connector
from datetime import datetime
from config import Config
# For MySQL/MariaDB
from mysql.connector import Error

def get_manga_list(config, testing=False):
    try:
        # Establish a database connection
        host_name = Config.host_name
        db_name = Config.db_name
        user_name = Config.user_name
        db_password = Config.db_password

        # print("host_name: ", host_name)
        # print("db_name: ", db_name)
        # print("user_name: ", user_name)
        # print("db_password: ", db_password)
        # Define the global connection object
        connection = mysql.connector.connect(host = host_name,
                                                database = db_name,
                                                user = user_name,
                                                password = db_password)
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Execute the query to retrieve data

            if testing:
                cursor.execute("SELECT * FROM manga_list2")
            else:
                cursor.execute("SELECT * FROM manga_list")
            # Fetch all the rows in a list of dictionaries
            manga_list = cursor.fetchall()

            # Helper function to handle None values and convert timestamps to datetime
            def parse_timestamp(timestamp):
                return datetime(1900, 1, 1) if timestamp is None else timestamp

            # Now let's sort the fetched data before returning it
            manga_list.sort(key=lambda x: parse_timestamp(x['last_updated_on_site']), reverse=True)
            # Print only the genres of each manga
            # for manga in manga_list:
            #     print(manga['genres'])  # This will print the genres field of each manga
            return manga_list
    except Error as e:
        print("Error while connecting to MariaDB", e)
    finally:
        # Close the connection
        if connection.is_connected():
            cursor.close()
            connection.close()
    return []