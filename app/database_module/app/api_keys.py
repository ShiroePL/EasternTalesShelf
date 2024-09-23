import os

anilist_id = 444059
is_development = os.getenv('FLASK_ENV') # 'development' or 'production'
table_name = 'manga_list_development' if is_development == 'development' else 'manga_list'

print(f"Setting enviroment to: {is_development}, table name: {table_name}")

def refresh_credentials():
    # Main usage
    try:
        user_name = os.getenv['DB_USER_NAME']
        db_password = os.getenv['DB_PASSWORD']
        host_name = os.getenv['DB_HOST_NAME_VPS_CONTENER']
        db_name = os.getenv['ANILIST_DB_NAME']

        print("VARIABLES SET FROM DOPPLER")
    except Exception as e:
        print("COULDN'T SET VARIABLES FROM DOPPLER, ERROR: ")
        print(e)
    return host_name, db_name, user_name, db_password
