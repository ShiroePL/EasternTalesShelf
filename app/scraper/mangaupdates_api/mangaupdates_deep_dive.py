"""
Deep dive into MangaUpdates API structure
Let's explore their actual REST API to find hidden/undocumented endpoints
"""
import requests
import json

base_url = "https://api.mangaupdates.com/v1"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    'Accept': 'application/json',
}

print("="*80)
print("MANGAUPDATES REST API DEEP DIVE")
print("="*80)

# The series ID from URL: /series/m9j8pqm/...
series_slug = "5ojazp5"

# Convert slug to numeric ID by looking at page source
print("\n[STEP 1] Testing different series ID formats...")
print("-"*80)

# Try different ID formats
id_variations = [
    series_slug,  # m9j8pqm
    "48465726286",  # Found in HTML (from RSS URL)
]

for series_id in id_variations:
    url = f"{base_url}/series/{series_id}"
    print(f"\nTrying: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS! Got data for series ID: {series_id}")
            print(f"Available fields ({len(data.keys())}): {list(data.keys())[:30]}")
            
            # Save full response
            with open(f'mangaupdates_series_{series_id}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved to: mangaupdates_series_{series_id}.json")
            
            # Check what data we got
            print("\nKey data points:")
            for key in ['title', 'description', 'type', 'year', 'status', 'rating', 'categories']:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and len(value) > 100:
                        print(f"  {key}: {value[:100]}...")
                    elif isinstance(value, list) and len(value) > 5:
                        print(f"  {key}: [{len(value)} items]")
                    else:
                        print(f"  {key}: {value}")
            
            break
        else:
            print(f"Failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")

# Step 2: Discover other endpoints
print("\n\n[STEP 2] Testing other API endpoints...")
print("-"*80)

endpoints_to_test = [
    '/series/search',
    '/series',
    '/releases',
    '/authors',
    '/publishers',
    '/groups',
    '/lists',
    '/reviews',
    '/forum',
]

for endpoint in endpoints_to_test:
    url = base_url + endpoint
    print(f"\n{endpoint}:")
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"  GET Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Response type: {type(data)}")
                if isinstance(data, dict):
                    print(f"  Keys: {list(data.keys())[:10]}")
                elif isinstance(data, list):
                    print(f"  List length: {len(data)}")
            except:
                print(f"  Response: {response.text[:100]}")
        
        # Try POST with search
        if 'search' in endpoint:
            post_response = requests.post(
                url,
                json={'search': 'villainess'},
                headers={**headers, 'Content-Type': 'application/json'},
                timeout=5
            )
            print(f"  POST Status: {post_response.status_code}")
            if post_response.status_code == 200:
                data = post_response.json()
                print(f"  Search results: {len(data.get('results', []))} items")
                
    except Exception as e:
        print(f"  Error: {e}")

# Step 3: Check for batch/GraphQL-like queries
print("\n\n[STEP 3] Testing for batch queries...")
print("-"*80)

batch_endpoints = [
    '/batch',
    '/query',
    '/multi',
]

for endpoint in batch_endpoints:
    url = base_url + endpoint
    print(f"\n{endpoint}:")
    
    try:
        response = requests.post(
            url,
            json={'queries': [{'series': series_slug}]},
            headers={**headers, 'Content-Type': 'application/json'},
            timeout=5
        )
        print(f"  Status: {response.status_code}")
        if response.status_code != 404:
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*80)
print("DEEP DIVE COMPLETE")
print("="*80)
