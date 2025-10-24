"""
MangaUpdates.com API Discovery Script
Checking for GraphQL endpoint and hidden APIs
"""
import requests
import re
from urllib.parse import urlparse

# Test URLs
test_url = "https://www.mangaupdates.com/series/m9j8pqm/what-should-i-do-with-my-brother"
base_url = "https://www.mangaupdates.com"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

print("="*80)
print("MANGAUPDATES.COM API DISCOVERY")
print("="*80)

# Step 1: Check common GraphQL endpoints
print("\n[STEP 1] Testing common GraphQL endpoints...")
print("-"*80)

graphql_endpoints = [
    '/graphql',
    '/api/graphql',
    '/gql',
    '/query',
    '/api/query',
    '/v1/graphql',
    '/api/v1/graphql',
]

for endpoint in graphql_endpoints:
    url = base_url + endpoint
    try:
        # Try GET first
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"  [FOUND] {url} - Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type')}")
            print(f"  Preview: {response.text[:200]}")
        elif response.status_code == 405:  # Method Not Allowed - might be POST only
            print(f"  [MAYBE] {url} - Status: 405 (POST might work)")
            # Try POST with empty query
            post_response = requests.post(
                url,
                json={'query': '{__typename}'},
                headers={**headers, 'Content-Type': 'application/json'},
                timeout=5
            )
            print(f"    POST Status: {post_response.status_code}")
            if post_response.status_code in [200, 400]:
                print(f"    POST Response: {post_response.text[:300]}")
    except requests.exceptions.RequestException as e:
        pass  # Silent fail for non-existent endpoints

# Step 2: Fetch the page HTML and look for API calls
print("\n[STEP 2] Analyzing page HTML for API endpoints...")
print("-"*80)

try:
    response = requests.get(test_url, headers=headers, timeout=10)
    html = response.text
    
    # Look for API endpoints in JavaScript
    api_patterns = [
        r'["\']https?://[^"\']*(?:api|graphql|gql|query)[^"\']*["\']',
        r'["\'](?:/api/|/graphql|/gql)[^"\']*["\']',
        r'endpoint\s*[:=]\s*["\']([^"\']+)["\']',
        r'apiUrl\s*[:=]\s*["\']([^"\']+)["\']',
        r'fetch\(["\']([^"\']+)["\']',
    ]
    
    found_apis = set()
    for pattern in api_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        found_apis.update(matches)
    
    if found_apis:
        print("  [FOUND] Potential API endpoints in HTML:")
        for api in sorted(found_apis):
            print(f"    - {api}")
    else:
        print("  [NONE] No obvious API endpoints found in HTML")
    
    # Look for GraphQL-specific patterns
    graphql_indicators = [
        'graphql',
        'apollo',
        '__typename',
        'query {',
        'mutation {',
        'subscription {',
    ]
    
    found_graphql = []
    for indicator in graphql_indicators:
        if indicator.lower() in html.lower():
            found_graphql.append(indicator)
    
    if found_graphql:
        print(f"\n  [FOUND] GraphQL indicators: {', '.join(found_graphql)}")
    else:
        print("\n  [NONE] No GraphQL indicators found")
    
except Exception as e:
    print(f"  [ERROR] {e}")

# Step 3: Check for API in response headers
print("\n[STEP 3] Checking response headers for API hints...")
print("-"*80)

try:
    response = requests.get(test_url, headers=headers, timeout=10)
    interesting_headers = ['X-API', 'X-GraphQL', 'X-Powered-By', 'Server', 'X-Backend']
    
    found = False
    for header in interesting_headers:
        if header in response.headers:
            print(f"  {header}: {response.headers[header]}")
            found = True
    
    if not found:
        print("  [NONE] No interesting headers found")
        
except Exception as e:
    print(f"  [ERROR] {e}")

# Step 4: Check their documented API
print("\n[STEP 4] Checking MangaUpdates documented API...")
print("-"*80)

api_base = "https://api.mangaupdates.com"
api_v1 = f"{api_base}/v1"

print(f"  Testing: {api_v1}/")

try:
    response = requests.get(f"{api_v1}/", headers=headers, timeout=10)
    print(f"  Status: {response.status_code}")
    print(f"  Content-Type: {response.headers.get('Content-Type')}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Response keys: {list(data.keys())}")
    
    # Try the series endpoint
    series_id = "m9j8pqm"
    series_url = f"{api_v1}/series/{series_id}"
    
    print(f"\n  Testing series endpoint: {series_url}")
    response = requests.get(series_url, headers=headers, timeout=10)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Available fields: {list(data.keys())[:20]}")
        
except Exception as e:
    print(f"  [ERROR] {e}")

# Step 5: Look for hidden endpoints in JavaScript files
print("\n[STEP 5] Checking for API calls in JavaScript files...")
print("-"*80)

try:
    response = requests.get(test_url, headers=headers, timeout=10)
    html = response.text
    
    # Find script tags
    script_urls = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    
    print(f"  Found {len(script_urls)} script files")
    
    # Check first 3 scripts for API endpoints
    for i, script_url in enumerate(script_urls[:3]):
        if not script_url.startswith('http'):
            script_url = base_url + script_url
        
        print(f"\n  Checking script {i+1}: {script_url[:80]}...")
        
        try:
            script_response = requests.get(script_url, headers=headers, timeout=5)
            script_content = script_response.text
            
            # Look for GraphQL/API patterns
            if 'graphql' in script_content.lower():
                print(f"    [FOUND] Contains 'graphql'!")
                # Find the context
                matches = re.finditer(r'.{0,100}graphql.{0,100}', script_content, re.IGNORECASE)
                for match in list(matches)[:3]:
                    print(f"      Context: ...{match.group(0)}...")
            
            if 'apollo' in script_content.lower():
                print(f"    [FOUND] Contains 'apollo' (GraphQL client)!")
            
            # Look for endpoint URLs
            endpoints = re.findall(r'["\'](?:https?://[^"\']*)?/(?:api|graphql|gql)[^"\']*["\']', script_content)
            if endpoints:
                print(f"    [FOUND] API endpoints: {endpoints[:5]}")
                
        except Exception as e:
            print(f"    [ERROR] {e}")

except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "="*80)
print("DISCOVERY COMPLETE")
print("="*80)
