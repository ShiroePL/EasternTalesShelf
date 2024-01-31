from api_keys import refresh_credentials
import mysql.connector

# host_name = api_keys.host_name
# db_name = api_keys.db_name
# user_name = api_keys.user_name
# db_password = api_keys.db_password

host_name, db_name, user_name, db_password = refresh_credentials()

# Define the global connection object
conn = mysql.connector.connect(host = host_name,
                                         database = db_name,
                                         user = user_name,
                                         password = db_password)
