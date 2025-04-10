"""
OAuth Configuration for AniList Authentication
"""

import os



# Callback URLs
# Set the redirect URI based on environment
if os.getenv('FLASK_ENV') == 'production':
    ANILIST_REDIRECT_URI = os.getenv('ANILIST_REDIRECT_URI')
    ANILIST_CLIENT_ID = os.getenv('ANILIST_CLIENT_ID', '')
    ANILIST_CLIENT_SECRET = os.getenv('ANILIST_CLIENT_SECRET', '')

elif os.getenv('FLASK_ENV') == 'development':
    ANILIST_REDIRECT_URI = os.getenv('ANILIST_REDIRECT_URI_LOCAL')
    ANILIST_CLIENT_ID = os.getenv('ANILIST_CLIENT_ID_LOCAL', '')
    ANILIST_CLIENT_SECRET = os.getenv('ANILIST_CLIENT_SECRET_LOCAL', '')

else:
    ANILIST_REDIRECT_URI = os.getenv('ANILIST_REDIRECT_URI')
    ANILIST_REDIRECT_URI = os.getenv('ANILIST_REDIRECT_URI')
    ANILIST_CLIENT_ID = os.getenv('ANILIST_CLIENT_ID', '')

# OAuth Endpoints
ANILIST_AUTHORIZE_URL = 'https://anilist.co/api/v2/oauth/authorize'
ANILIST_TOKEN_URL = 'https://anilist.co/api/v2/oauth/token'
ANILIST_API_URL = 'https://graphql.anilist.co' 