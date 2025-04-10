"""
OAuth handler for AniList authentication
"""

import requests
import json
import secrets
from flask import session, redirect, url_for, request
from werkzeug.exceptions import BadRequest
from flask_login import login_user

from app.oauth_config import (
    ANILIST_CLIENT_ID, 
    ANILIST_CLIENT_SECRET,
    ANILIST_REDIRECT_URI,
    ANILIST_AUTHORIZE_URL,
    ANILIST_TOKEN_URL,
    ANILIST_API_URL
)
print("ANILIST_REDIRECT_URI: ", ANILIST_REDIRECT_URI)
class AniListOAuth:
    @staticmethod
    def get_auth_url():
        """Generate the AniList authorization URL"""
        # Generate a random state to protect against CSRF
        state = secrets.token_hex(16)
        session['oauth_state'] = state
        
        # Generate the authorization URL without scope (AniList doesn't support scopes)
        params = {
            'client_id': ANILIST_CLIENT_ID,
            'redirect_uri': ANILIST_REDIRECT_URI,
            'response_type': 'code',
            'state': state
        }
        
        # Convert params to query string
        query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
        auth_url = f"{ANILIST_AUTHORIZE_URL}?{query_string}"
        
        return auth_url
    
    @staticmethod
    def handle_callback(code, state, store_token=False):
        """Handle the OAuth callback from AniList
        
        Args:
            code: The authorization code from AniList
            state: The state parameter for CSRF protection
            store_token: Whether to store the access token for additional features (default: False)
        """
        # Verify state to prevent CSRF attacks
        if state != session.get('oauth_state'):
            raise BadRequest("Invalid state parameter")
        
        # Exchange authorization code for access token
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': ANILIST_CLIENT_ID,
            'client_secret': ANILIST_CLIENT_SECRET,
            'redirect_uri': ANILIST_REDIRECT_URI,
            'code': code
        }
        
        # Make the token request
        response = requests.post(ANILIST_TOKEN_URL, data=token_data)
        if response.status_code != 200:
            raise BadRequest(f"Failed to obtain access token: {response.text}")
        
        token_response = response.json()
        access_token = token_response.get('access_token')
        
        # Store the token in the session if needed for current session use
        session['anilist_token'] = access_token
        
        # Get user information from AniList API
        user_info = AniListOAuth.get_user_info(access_token)
        
        # Return both user info and access token (with None if not storing)
        return user_info, access_token if store_token else None
    
    @staticmethod
    def get_user_info(access_token):
        """Get user information from AniList API using GraphQL"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        # GraphQL query to get user information
        query = """
        query {
            Viewer {
                id
                name
                avatar {
                    large
                }
                options {
                    titleLanguage
                }
            }
        }
        """
        
        # Make the GraphQL request
        response = requests.post(
            ANILIST_API_URL,
            headers=headers,
            json={'query': query}
        )
        
        if response.status_code != 200:
            raise BadRequest(f"Failed to fetch user information: {response.text}")
        
        data = response.json()
        return data.get('data', {}).get('Viewer', {}) 