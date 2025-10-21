import os
import requests
import json
import time
import re
from flask import Blueprint, request, jsonify, current_app, Response, session
from flask_login import login_required, current_user
from flask_cors import cross_origin

from app.admin import admin_required

# Create Blueprint
graphql_bp = Blueprint('graphql', __name__, url_prefix='/graphql')

def validate_request_origin():
    """Validate the request is coming from an allowed origin and referer"""
    # Get allowed domains from environment
    allowed_domains_raw = os.getenv('WEBSITE_ALLOWED_DOMAINS', '')
    
 
    
    # Split by comma and clean up each domain
    allowed_domains = []
    for domain in allowed_domains_raw.split(','):
        domain = domain.strip()
        # Remove protocol (http:// or https://)
        domain = re.sub(r'^https?://', '', domain)
        # Remove trailing slash
        domain = domain.rstrip('/')
        # Remove 'www.' prefix if present
        domain = re.sub(r'^www\.', '', domain)
        
        if domain:
            allowed_domains.append(domain)
    
    # Add localhost/127.0.0.1 for development if in development mode
    if os.getenv('FLASK_ENV') == 'development':
        allowed_domains.extend(['localhost', '127.0.0.1', 'localhost:5001', '127.0.0.1:5001'])
    
    # If no domains are specified, skip this check
    if not allowed_domains:
        current_app.logger.warning("WEBSITE_ALLOWED_DOMAINS not set, skipping origin validation")
        return True
    
    current_app.logger.info(f"Allowed domains: {allowed_domains}")
    
    # Check Origin header (used in CORS preflight and AJAX requests)
    origin = request.headers.get('Origin', '')
    
    # Check Referer header (used in regular requests)
    referer = request.headers.get('Referer', '')
    
    # Function to check if a URL matches our allowed domains
    def url_matches_allowed_domains(url):
        if not url:
            return False
            
        # Clean up the URL for matching - remove protocol and trailing slash
        cleaned_url = re.sub(r'^https?://', '', url).rstrip('/')
        
        for domain in allowed_domains:
            # Create a pattern that matches the domain exactly or as a subdomain
            pattern = r'^{0}$|^[^/]+\.{0}$|^{0}:[0-9]+$'.format(re.escape(domain))
            if re.search(pattern, cleaned_url):
                return True
        return False
    
    # If either header matches our allowed domains, allow the request
    origin_valid = url_matches_allowed_domains(origin) if origin else False
    referer_valid = url_matches_allowed_domains(referer) if referer else False
    
    # Log the result
    if origin:
        current_app.logger.info(f"Origin validation: {origin} -> {'✓' if origin_valid else '❌'}")
    if referer:
        current_app.logger.info(f"Referer validation: {referer} -> {'✓' if referer_valid else '❌'}")
    
    return origin_valid or referer_valid

def validate_graphql_key():
    """Validate the GraphQL API key from request headers"""
    # Get the expected key from environment variables
    expected_key = os.getenv('GRAPHQL_SAFETY_KEY')
    
    if not expected_key:
        current_app.logger.warning("GRAPHQL_SAFETY_KEY not set in environment variables")
        return False
    
    # Get the provided key from headers
    provided_key = request.headers.get('X-GraphQL-Key')
    
    if not provided_key:
        current_app.logger.warning("Missing GraphQL safety key in request headers")
        return False
        
    # Validate the key
    key_match = provided_key == expected_key
    
    if not key_match:
        current_app.logger.warning(f"GraphQL key validation failed - provided: {provided_key[:5]}...")
    
    return key_match

@graphql_bp.route('/', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@admin_required
@login_required
def graphql_proxy_endpoint():
    """Proxies GraphQL requests to the Directus instance."""
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return Response(), 200
    
    # Validate the request origin
    if not validate_request_origin():
        return jsonify({'errors': ['Request origin not allowed']}), 403
    
    # Validate the GraphQL safety key
    if not validate_graphql_key():
        return jsonify({'errors': ['Invalid or missing API key']}), 403
    
    if os.getenv('FLASK_ENV') == 'development':
        directus_url = os.getenv('DIRECTUS_URL')
    else:
        directus_url = os.getenv('DIRECTUS_URL_VPS')

    directus_token = os.getenv('DIRECTUS_STATIC_TOKEN') # Or however you handle auth

    if not directus_url:
        return jsonify({'errors': ['Directus URL not configured in Flask app.']}), 500

    # Prepare headers, including authorization if needed
    headers = {'Content-Type': 'application/json'}
    if directus_token:
        headers['Authorization'] = f'Bearer {directus_token}'

    # Forward the request data (query, variables)
    data = request.get_json()
    
    # Log the request details for debugging (be careful not to log tokens in production)
    current_app.logger.info(f"Proxying GraphQL request to: {directus_url.rstrip('/')}/graphql")
    current_app.logger.info(f"Request data: {json.dumps(data, indent=2)}")
    
    final_directus_endpoint = f"{directus_url.rstrip('/')}/graphql" # Add back the /graphql path
    current_app.logger.info(f"Attempting POST request to: {final_directus_endpoint}")
    
    try:
        # Start timing the request
        start_time = time.time()
        
        response = requests.post(
            final_directus_endpoint, # Use the variable here
            json=data,
            headers=headers,
            timeout=10 # Add a reasonable timeout
        )
        
        # Calculate elapsed time
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        current_app.logger.info(f"Directus request completed in {elapsed_time:.2f}ms")
        
        # Log response for debugging
        #current_app.logger.info(f"Response status: {response.status_code}")
        #current_app.logger.info(f"Response headers: {dict(response.headers)}")
        
        try:
            # Try to parse response as JSON
            response_json = response.json()
            
            # Add timing information to the response
            if isinstance(response_json, dict):
                response_json['_meta'] = {
                    'requestTimeMs': round(elapsed_time, 2)
                }
            
            # Log a summary of the response body instead of the whole thing
            if isinstance(response_json, dict):
                items_count = 0
                if 'data' in response_json:
                    # Count items in each collection
                    for key, value in response_json['data'].items():
                        if isinstance(value, list):
                            items_count += len(value)
                
                current_app.logger.info(f"Response successful with {items_count} total items")
            else:
                current_app.logger.info("Response received (body not logged)")
            
            # Return the modified response
            return jsonify(response_json), response.status_code
            
        except:
            # If response is not JSON, return it as-is
            current_app.logger.info(f"Response body (first 200 chars): {response.text[:200]}")
            return Response(
                response.content, 
                status=response.status_code, 
                mimetype=response.headers.get('Content-Type', 'application/json')
            )

    except requests.exceptions.RequestException as e:
        # Log the error for debugging
        current_app.logger.error(f"Error proxying GraphQL request to Directus: {e}")
        return jsonify({'errors': [f'Failed to connect to Directus GraphQL endpoint: {str(e)}']}), 502 # Bad Gateway

    except Exception as e:
        # Catch unexpected errors
        current_app.logger.error(f"Unexpected error in GraphQL proxy: {e}")
        return jsonify({'errors': ['An unexpected error occurred.']}), 500

@graphql_bp.route('/public', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def public_graphql_endpoint():
    """Public GraphQL endpoint that serves demo data without authentication."""
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return Response(), 200
    
    # Validate the request origin
    if not validate_request_origin():
        return jsonify({'errors': ['Request origin not allowed']}), 403
    
    # Validate the GraphQL safety key
    if not validate_graphql_key():
        return jsonify({'errors': ['Invalid or missing API key']}), 403
    
    if os.getenv('FLASK_ENV') == 'development':
        directus_url = os.getenv('DIRECTUS_URL')
    else:
        directus_url = os.getenv('DIRECTUS_URL_VPS')

    directus_token = os.getenv('DIRECTUS_STATIC_TOKEN')

    if not directus_url:
        return jsonify({'errors': ['Directus URL not configured in Flask app.']}), 500

    # Prepare headers for Directus request
    headers = {'Content-Type': 'application/json'}
    if directus_token:
        headers['Authorization'] = f'Bearer {directus_token}'

    # Get the original request data
    data = request.get_json()
    
    # Only allow specific queries for public access
    # This ensures that only demo data is accessible
    if data and 'query' in data:
        # Check if the query contains operations that should be allowed for public access
        query = data['query'].lower()
        allowed_tables = ['manga_list', 'manga_list_aggregated']
        
        # Simple check to ensure the query only accesses allowed tables
        # For a more robust solution, you'd want to use a proper GraphQL parser
        is_allowed = any(table in query for table in allowed_tables)
        
        if not is_allowed:
            return jsonify({'errors': ['This query is not allowed for public access']}), 403
    else:
        return jsonify({'errors': ['Invalid GraphQL request']}), 400
    
    final_directus_endpoint = f"{directus_url.rstrip('/')}/graphql"
    current_app.logger.info(f"Proxying public GraphQL request to: {final_directus_endpoint}")
    
    try:
        # Start timing the request
        start_time = time.time()
        
        response = requests.post(
            final_directus_endpoint,
            json=data,
            headers=headers,
            timeout=10
        )
        
        # Calculate elapsed time
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        try:
            # Try to parse response as JSON
            response_json = response.json()
            
            # Add timing and demo mode information
            if isinstance(response_json, dict):
                response_json['_meta'] = {
                    'requestTimeMs': round(elapsed_time, 2),
                    'demoMode': True
                }
            
            # Return the modified response
            return jsonify(response_json), response.status_code
            
        except:
            # If response is not JSON, return it as-is
            return Response(
                response.content, 
                status=response.status_code, 
                mimetype=response.headers.get('Content-Type', 'application/json')
            )

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error proxying public GraphQL request: {e}")
        return jsonify({'errors': [f'Failed to connect to Directus GraphQL endpoint: {str(e)}']}), 502

    except Exception as e:
        current_app.logger.error(f"Unexpected error in public GraphQL proxy: {e}")
        return jsonify({'errors': ['An unexpected error occurred.']}), 500

# Keep GraphiQL interface for development/testing - point it to the proxy endpoint
# @graphql_bp.route('/graphiql', methods=['GET'])
# @login_required
# def graphiql():
#     # Ensure the fetcher URL points to your proxy endpoint ('/graphql/')
#     # The CSRF token handling might need adjustment depending on your setup
#     return """
#     <!DOCTYPE html>
#     <html>
#       <head>
#         <title>GraphiQL (Directus Proxy)</title>
#         <link href="https://cdn.jsdelivr.net/npm/graphiql/graphiql.min.css" rel="stylesheet" />
#       </head>
#       <body style="margin: 0;">
#         <div id="graphiql" style="height: 100vh;"></div>
#         <script
#           crossorigin
#           src="https://cdn.jsdelivr.net/npm/react/umd/react.production.min.js"
#         ></script>
#         <script
#           crossorigin
#           src="https://cdn.jsdelivr.net/npm/react-dom/umd/react-dom.production.min.js"
#         ></script>
#         <script
#           crossorigin
#           src="https://cdn.jsdelivr.net/npm/graphiql/graphiql.min.js"
#         ></script>
#         <script>
#           const fetcher = GraphiQL.createFetcher({
#             url: '/graphql/', // This now points to your Flask proxy
#             headers: {
#               // Adjust CSRF token handling if necessary based on your Flask-WTF setup
#               'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrf_token='))?.split('=')[1] || ''
#             }
#           });
#
#           ReactDOM.render(
#             React.createElement(GraphiQL, { fetcher }),
#             document.getElementById('graphiql'),
#           );
#         </script>
#       </body>
#     </html>
#     """
