# MangaUpdates.com API Analysis

**Investigation Date**: October 20, 2025  
**Status**: ❌ No GraphQL API Found | ✅ REST API Available

## 🔍 Investigation Summary

MangaUpdates.com **does NOT use GraphQL**. They use a traditional REST API.

### What We Found:

1. **❌ No GraphQL**: Extensive search found NO GraphQL endpoint
   - Checked common paths: `/graphql`, `/gql`, `/api/graphql`, etc.
   - No GraphQL indicators in HTML (`__typename`, Apollo, etc.)
   - No GraphQL queries in JavaScript files

2. **✅ REST API**: They have a documented REST API at `api.mangaupdates.com/v1`
   - **Endpoint**: `https://api.mangaupdates.com/v1`
   - **Technology**: Next.js frontend + REST backend
   - **Authentication**: Not required for public data

## 📋 Available REST API

### Base URL
```
https://api.mangaupdates.com/v1
```

### Working Endpoints

#### 1. Get Series Details
```
GET /v1/series/{series_id}
```

**Important**: Must use numeric ID (e.g., `48465726286`), not slug (e.g., `m9j8pqm`)

**Example Request**:
```python
import requests

series_id = 48465726286
url = f"https://api.mangaupdates.com/v1/series/{series_id}"

response = requests.get(url, headers={'Accept': 'application/json'})
data = response.json()
```

**Response Fields**:
```json
{
  "series_id": 48465726286,
  "title": "What Should I Do With My Brother?",
  "url": "https://www.mangaupdates.com/series/m9j8pqm/...",
  "associated": [...],
  "description": "...",
  "image": {
    "url": {
      "original": "https://cdn.mangaupdates.com/image/i292132.jpg",
      "thumb": "https://cdn.mangaupdates.com/image/thumb/i292132.jpg"
    },
    "height": 226,
    "width": 160
  },
  "type": "Manhua",
  "year": "2017",
  "bayesian_rating": 6.26,
  "rating_votes": 15,
  "genres": [
    {"genre": "Adventure"},
    {"genre": "Comedy"},
    ...
  ],
  "categories": [
    {
      "series_id": 48465726286,
      "category": "Cultivation",
      "votes": 1,
      "votes_plus": 1,
      "votes_minus": 0
    },
    ...
  ],
  "latest_chapter": 311,
  "status": "311 Chapters (Complete)",
  "licensed": true,
  "completed": true,
  "anime": {...},
  "related_series": [...],
  "authors": [...],
  "publishers": [...],
  "publications": [...],
  "recommendations": [...],
  "category_recommendations": [...],
  "rank": {...},
  "last_updated": {...}
}
```

#### 2. Search Series
```
POST /v1/series/search
Content-Type: application/json

{
  "search": "villainess"
}
```

**Response**:
```json
{
  "results": [
    {
      "record": {
        "series_id": 123456,
        "title": "...",
        "url": "...",
        "description": "...",
        ...
      }
    },
    ...
  ],
  "total_hits": 25
}
```

## 🔧 Converting Slug to ID

**Problem**: The API requires numeric ID, but URLs use slugs (e.g., `m9j8pqm`)

**Solution**: Parse the HTML page to extract the ID

```python
import requests
import re

def slug_to_id(slug):
    """Convert MangaUpdates slug to numeric series ID."""
    url = f"https://www.mangaupdates.com/series/{slug}"
    response = requests.get(url)
    html = response.text
    
    # Find RSS feed URL which contains the numeric ID
    match = re.search(r'https://api\.mangaupdates\.com/v1/series/(\d+)/rss', html)
    
    if match:
        return match.group(1)
    
    return None

# Example usage
series_id = slug_to_id("m9j8pqm")  # Returns: "48465726286"
```

## 📊 Comparison: GraphQL vs REST

| Feature | Batotwo (GraphQL) | MangaUpdates (REST) |
|---------|-------------------|---------------------|
| **API Type** | GraphQL | REST |
| **Endpoint** | `/apo/` | `/v1/series/{id}` |
| **Query Flexibility** | High (request only what you need) | Low (fixed response structure) |
| **Request Count** | 1 query for multiple resources | Multiple requests needed |
| **Discovery** | Hard (introspection disabled) | Easy (documented) |
| **Speed** | Fast (~500ms) | Moderate (~800ms) |
| **Data Freshness** | Real-time | Real-time |

## 🎯 What MangaUpdates API Provides

### ✅ Available Data:
- Title, alt titles, description
- Type (Manga/Manhwa/Manhua/etc.)
- Publication year, status, latest chapter
- Rating (Bayesian) and votes
- Genres and categories (with votes)
- Authors, artists, publishers
- Related series, recommendations
- Image (original + thumbnail)
- Anime adaptations
- Licensed status

### ❌ Missing Data (compared to what you might want):
- **No chapter list** with individual chapter details
- **No views statistics** (total, monthly, etc.)
- **No upload dates** for chapters
- **No scanlation group** information
- **No chapter images/pages**
- **No user comments** on chapters

## 💡 Recommendation

**For MangaUpdates**: Stick with the REST API. No hidden GraphQL endpoint exists.

**Workflow**:
1. Convert slug to ID (parse HTML once)
2. Use REST API with numeric ID
3. Cache the slug→ID mapping

**Alternative**: If you need chapter-level data, you'll need to scrape the website directly or find another source (like Batotwo).

---

## 📝 Example Complete Workflow

```python
import requests
import re
import json

class MangaUpdatesAPI:
    """Simple wrapper for MangaUpdates REST API."""
    
    def __init__(self):
        self.base_url = "https://api.mangaupdates.com/v1"
        self.headers = {'Accept': 'application/json'}
    
    def slug_to_id(self, slug):
        """Convert slug to numeric ID."""
        url = f"https://www.mangaupdates.com/series/{slug}"
        response = requests.get(url)
        match = re.search(r'/series/(\d+)/rss', response.text)
        return match.group(1) if match else None
    
    def get_series(self, series_id):
        """Get full series details."""
        url = f"{self.base_url}/series/{series_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def search(self, query):
        """Search for series."""
        url = f"{self.base_url}/series/search"
        response = requests.post(
            url,
            json={'search': query},
            headers={**self.headers, 'Content-Type': 'application/json'}
        )
        return response.json()

# Usage
api = MangaUpdatesAPI()

# From slug
series_id = api.slug_to_id("m9j8pqm")
details = api.get_series(series_id)

print(f"Title: {details['title']}")
print(f"Rating: {details['bayesian_rating']}/10")
print(f"Status: {details['status']}")

# Or search directly
results = api.search("villainess")
print(f"Found {len(results['results'])} results")
```

---

**Conclusion**: MangaUpdates uses REST API only. For better data (chapters, views, comments), use Batotwo's GraphQL API which provides much more detailed information.
