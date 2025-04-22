# simple_graphql_test.py
import requests
import json
from pprint import pprint

def test_graphql_endpoint(url):
    """
    Test a GraphQL endpoint directly without login (assuming session already exists)
    """
    # Your GraphQL query
    query = """
    query {
      mangaList {
        idAnilist
        titleEnglish
        chaptersProgress
        allChapters
        coverImage
        isCoverDownloaded
        score
      }
      mangaUpdates {
        anilistId
        status
        lastUpdatedTimestamp
      }
    }
    """
    
    # Create a session that will maintain cookies
    session = requests.Session()
    
    # Get the CSRF token if needed (visiting a page first to get the token)
    # Uncomment these lines if you need CSRF token
    """
    response = session.get(url.replace('/graphql/', '/'))
    # You would need to extract the CSRF token from the response
    # This depends on how your app provides the token
    # csrf_token = extract_token_from_response(response)
    """
    
    # For this example, we'll assume you might have a CSRF token in a cookie
    # If you don't need CSRF, you can remove this
    csrf_token = session.cookies.get('csrf_token', '')
    
    # Set up headers
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token  # Include CSRF token if needed
    }
    
    # Make the GraphQL request
    try:
        response = session.post(
            url,
            headers=headers,
            json={'query': query}
        )
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            print("✅ GraphQL query successful!")
            
            # Display summary of results
            if 'data' in data:
                if 'mangaList' in data['data']:
                    manga_count = len(data['data']['mangaList'])
                    print(f"📚 Found {manga_count} manga entries")
                
                if 'mangaUpdates' in data['data']:
                    update_count = len(data['data']['mangaUpdates'])
                    print(f"🔄 Found {update_count} manga updates")
                
                # Print the first few entries
                print("\n📌 Sample data (first 3 entries):")
                sample_data = {}
                for key, value in data['data'].items():
                    if isinstance(value, list) and len(value) > 3:
                        sample_data[key] = value[:3]
                    else:
                        sample_data[key] = value
                
                pprint(sample_data)
                
                # Ask if user wants to see all data
                if input("\nShow full data? (y/n): ").lower() == 'y':
                    print("\n📋 Full response data:")
                    pprint(data)
            else:
                print("❓ No data returned in the response")
                pprint(data)
            
            return data
            
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error making request: {str(e)}")
        
    return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter GraphQL endpoint URL (e.g., http://localhost:5000/graphql/): ")
    
    test_graphql_endpoint(url)
