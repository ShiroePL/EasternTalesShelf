import os
from app.vault_approle_functions import vault_login, read_secret

import os

class Config(object):
    @classmethod
    def fetch_doppler_secrets(cls):
        try:
            cls.user_name = os.getenv('DB_USER_NAME')
            cls.db_password = os.getenv('DB_PASSWORD')
            cls.db_name = os.getenv('ANILIST_DB_NAME')
            cls.flask_secret_key = os.getenv('FLASK_SECRET_KEY')
            cls.fastapi_updater_server_IP = os.getenv('FASTAPI_UPDATER_SERVER_IP') #ip of contaier in docker networks

            if os.getenv('FLASK_ENV') == 'production':
                cls.host_name = os.getenv('DB_HOST_NAME_VPS_CONTENER')
            else:
                cls.host_name = os.getenv('DB_HOST_NAME')

            print("VARIABLES SET FROM DOPPLER")
        except Exception as e:
            print("Couldn't set variables from Doppler, error:")
            print(e)

Config.fetch_doppler_secrets()


        
class DevelopmentConfig(Config):
    DEBUG = True
    # Development-specific configurations

class ProductionConfig(Config):
    DEBUG = False
    # Production-specific configurations

# Choose the configuration based on an environment variable
config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}

is_development_mode = config_dict[os.getenv('FLASK_ENV', 'development')]
is_development_boolen = is_development_mode.DEBUG

print("is_development_mode: ", is_development_boolen)

if is_development_boolen: # for dev environment
    fastapi_updater_server_IP = "127.0.0.1"

# Database configurations
database_type = "mariadb"  #  "mariadb" or "sql_lite"

if database_type == "mariadb":
    DATABASE_URI = f"mysql+pymysql://{Config.user_name}:{Config.db_password}@{Config.host_name}/{Config.db_name}"    
elif database_type == "sql_lite":
    DATABASE_URI = 'sqlite:///anilist_db.db'

