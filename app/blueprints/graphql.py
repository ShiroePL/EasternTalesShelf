import os
import requests
import json
import time
from flask import Blueprint, request, jsonify, current_app, Response
from flask_login import login_required

# Create Blueprint
graphql_bp = Blueprint('graphql', __name__, url_prefix='/graphql')

@graphql_bp.route('/', methods=['POST'])
@login_required  # Keep authentication if needed for your app's endpoint
def graphql_proxy_endpoint():
    """Proxies GraphQL requests to the Directus instance."""
    
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
        current_app.logger.info(f"Response status: {response.status_code}")
        current_app.logger.info(f"Response headers: {dict(response.headers)}")
        
        try:
            # Try to parse response as JSON
            response_json = response.json()
            
            # Add timing information to the response
            if isinstance(response_json, dict):
                response_json['_meta'] = {
                    'requestTimeMs': round(elapsed_time, 2)
                }
            
            # Log the response body
            current_app.logger.info(f"Response body: {json.dumps(response_json, indent=2)}")
            
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
