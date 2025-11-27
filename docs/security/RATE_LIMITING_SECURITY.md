# Rate Limiting & Security Implementation

## 🛡️ Overview

This document describes the comprehensive rate limiting and security measures implemented across the EasternTalesShelf application to prevent abuse, DDoS attacks, and resource exhaustion.

## 📦 Dependencies

- **Flask-Limiter 3.5.0**: Rate limiting extension for Flask
- **Storage**: In-memory storage (production should use Redis for distributed systems)

## 🔧 Configuration

### Global Defaults
- **200 requests per hour** (default for all endpoints)
- **50 requests per minute** (default for all endpoints)
- **Strategy**: Fixed window
- **Headers Enabled**: Yes (clients can see rate limit info in response headers)

### Rate Limit Headers
All responses include:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Timestamp when the limit resets

## 🚦 Endpoint-Specific Rate Limits

### 🔐 Authentication Endpoints (`auth.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/login` | **5 per minute** | Strict limit to prevent brute force attacks |
| `/auth/anilist` | **10 per minute** | Prevent OAuth flow abuse |
| `/auth/anilist/callback` | **10 per minute** | Prevent OAuth callback spam |

**Additional Security:**
- Username validation (alphanumeric, underscore, hyphen only)
- Input sanitization to prevent injection attacks
- Password length validation (max 100 chars)

### 📊 API Endpoints (`api.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/api/notifications` | **20 per minute** | Expensive database queries with joins |
| `/api/notifications/{id}/read` | **30 per minute** | Lighter write operation |
| `/api/update_episodes` | **20 per minute** | Database write operation |
| `/api/check_covers` | **Default** | File system checks |

### 🔍 GraphQL Endpoints (`graphql.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/graphql/` | **10 per minute** | Very expensive - complex queries, database joins |
| `/graphql/public` | **20 per minute** | Public endpoint, slightly more generous |

**Why so strict?**
- GraphQL allows arbitrary complex queries
- Single query can retrieve hundreds of records
- Potential for N+1 query problems
- Direct database proxy to Directus

### 📥 Download & Queue Management (`download.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/api/queue/add` | **20 per minute** | Prevents queue flooding |
| `/api/queue/pause` | **Default** | Admin control |
| `/api/queue/resume` | **Default** | Admin control |
| `/api/queue/remove` | **Default** | Admin control |

### 📚 Manga Management (`manga.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/add_bato` | **10 per minute** | Triggers expensive web scraping + API calls |
| `/sync` | **5 per minute** | Very expensive - full FastAPI sync |

**Why 5/min for sync?**
- Connects to external FastAPI server
- Processes entire manga database
- Can take several seconds per request

### 🔌 Extension Endpoints (`extension.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/extension/reading-time` | **30 per minute** | Chrome extension usage - moderate |
| `/extension/reading-time-batch` | **10 per minute** | Batch inserts - stricter |
| `/extension/reading-data` | **Default** | Admin only - get requests |

### 📰 Bato Notifications (`bato_notifications.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/api/bato/notifications` | **30 per minute** | Notification retrieval |
| `/api/bato/scrape/{id}` | **5 per minute** | Triggers expensive scraping job |
| `/api/bato/upload-statuses` | **Default** | Public bulk data endpoint |

### 👨‍💼 Bato Admin (`bato_admin.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/api/bato/admin/stats` | **30 per minute** | Monitoring - moderate limit |
| `/api/bato/admin/system-status` | **Default** | Lightweight queries |
| `/api/bato/admin/activity` | **Default** | Admin dashboard |

### 🔔 Notifications (`notifications.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/api/notifications/` | **20 per minute** | Expensive DB query |
| `/api/notifications/refresh` | **10 per minute** | Very expensive - fetches from external APIs |

### 🪝 Webhook Endpoints (`webhook.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/webhook/toggle` | **10 per minute** | Admin control |
| `/webhook/start_scraper` | **10 per minute** | Admin control |
| `/webhook/stop_scraper` | **10 per minute** | Admin control |
| `/webhook/heartbeat` | **Default** | Automatic system heartbeats |

### 🏠 Main Endpoints (`main.py`)

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `/` | **Default** | Public homepage |
| `/manhwa/{id}/{slug}` | **Default** | Public manga pages |
| `/save_color_settings` | **20 per minute** | User settings update |
| `/update_cover_status` | **30 per minute** | Cover status update |

## 🛡️ Additional Security Measures

### Input Validation

**Username Validation:**
```python
def validate_username(username):
    """Validate username format to prevent injection attacks"""
    if not username or len(username) > 50:
        return False
    # Allow alphanumeric, underscore, hyphen only
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
```

**Benefits:**
- Prevents SQL injection attempts
- Prevents XSS attacks
- Limits username length
- Ensures clean data

### Password Validation
- Maximum length: 100 characters
- Prevents buffer overflow attempts
- Validates presence before processing

### Origin Validation (GraphQL)
- Validates request origin against whitelist
- Checks `Origin` and `Referer` headers
- Development mode includes localhost

### API Key Protection (GraphQL)
- Requires `X-GraphQL-Key` header
- Validates against environment variable
- Prevents unauthorized GraphQL access

## 📈 Monitoring

### Rate Limit Headers
Clients receive information about their rate limits:
```http
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 18
X-RateLimit-Reset: 1699999999
```

### When Rate Limit Exceeded
Response:
```json
{
  "error": "429 Too Many Requests"
}
```

Status Code: **429 Too Many Requests**

## 🚀 Production Recommendations

### 1. Use Redis for Storage
```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",  # Use Redis instead of memory
    default_limits=["200 per hour", "50 per minute"]
)
```

**Why Redis?**
- Distributed rate limiting across multiple servers
- Persistent storage survives restarts
- Better performance at scale
- Shared state in containerized environments

### 2. Custom Key Functions
Consider IP + User ID for authenticated endpoints:
```python
def get_user_ip_key():
    if current_user.is_authenticated:
        return f"{current_user.id}:{request.remote_addr}"
    return request.remote_addr
```

### 3. Whitelist Trusted IPs
```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
    default_limits=["200 per hour", "50 per minute"],
    exempt_when=lambda: request.remote_addr in ['127.0.0.1', 'trusted-ip']
)
```

### 4. Monitor Rate Limit Violations
Add logging for rate limit hits:
```python
@app.after_request
def log_rate_limits(response):
    if response.status_code == 429:
        logger.warning(f"Rate limit hit: {request.path} from {request.remote_addr}")
    return response
```

## 🔄 Cloudflare Integration

### What Cloudflare Does
- ✅ DDoS protection at network layer
- ✅ Blocks known malicious IPs
- ✅ Bot detection and blocking
- ✅ CDN caching reduces server load

### What Flask-Limiter Does
- ✅ Application-level rate limiting
- ✅ Protects expensive operations
- ✅ Prevents API abuse from legitimate users
- ✅ Fine-grained control per endpoint
- ✅ Protects against authenticated user abuse

### Working Together
```
Internet Request
    ↓
Cloudflare (Network Layer)
    ├─ Blocks DDoS
    ├─ Filters bots
    └─ Passes legitimate traffic
         ↓
Flask Application (Application Layer)
    ├─ Rate limiting per endpoint
    ├─ Input validation
    └─ Business logic protection
```

## 🎯 Attack Scenarios Prevented

### 1. Brute Force Login
❌ **Without Rate Limiting:**
```python
for password in password_list:
    login(username, password)  # 10,000 attempts in seconds
```

✅ **With Rate Limiting:**
- Maximum 5 attempts per minute
- 10,000 attempts = 33+ hours
- Account lockout can be implemented

### 2. GraphQL Query Bombing
❌ **Without Rate Limiting:**
```graphql
query {
  manga_list {  # Get all manga
    chapters {  # For each manga, get all chapters
      pages {   # For each chapter, get all pages
        # Thousands of records in one query
      }
    }
  }
}
```

✅ **With Rate Limiting:**
- Maximum 10 queries per minute
- Expensive queries limited
- Server resources protected

### 3. Scraping Trigger Spam
❌ **Without Rate Limiting:**
```python
for manga_id in range(1, 10000):
    trigger_scrape(manga_id)  # Overload scraping system
```

✅ **With Rate Limiting:**
- Maximum 5 scraping triggers per minute
- Prevents scraping queue overflow
- Protects external services

### 4. Database Exhaustion
❌ **Without Rate Limiting:**
```python
while True:
    get_all_notifications()  # Complex query with joins
```

✅ **With Rate Limiting:**
- Maximum 20 queries per minute
- Database connections protected
- Other users can still access the system

## 📊 Testing Rate Limits

### Using cURL
```bash
# Test login rate limit (should block after 5 attempts)
for i in {1..10}; do
  curl -X POST http://localhost:5001/login \
    -d "username=test&password=wrong" \
    -w " - Status: %{http_code}\n"
  sleep 1
done
```

### Using Python
```python
import requests
import time

url = "http://localhost:5001/api/notifications"
headers = {"Cookie": "session=your-session-cookie"}

for i in range(25):  # Should block after 20
    response = requests.get(url, headers=headers)
    print(f"Request {i+1}: {response.status_code}")
    if response.status_code == 429:
        print(f"Rate limited! Headers: {response.headers}")
        break
    time.sleep(2)  # 2 seconds between requests
```

## 🔧 Troubleshooting

### Rate Limit Too Strict
Adjust in blueprint:
```python
@api_bp.route('/endpoint')
@get_limiter().limit("30 per minute")  # Increased from 20
def my_endpoint():
    pass
```

### Shared IP Issues
Users behind same NAT/proxy get shared limits. Solutions:
1. Use user ID in key function for authenticated routes
2. Increase limits for authenticated users
3. Use Redis with sliding window strategy

### Development Testing
Disable rate limiting in development:
```python
if os.getenv('FLASK_ENV') == 'development':
    limiter.enabled = False
```

## 📝 Summary

**Security Layers:**
1. ✅ Cloudflare (Network Layer)
2. ✅ Flask-Limiter (Application Layer)
3. ✅ Input Validation (Data Layer)
4. ✅ Authentication/Authorization (Access Layer)

**Protection Against:**
- ✅ Brute force attacks
- ✅ DDoS attacks
- ✅ API abuse
- ✅ Resource exhaustion
- ✅ Scraping abuse
- ✅ Database overload
- ✅ Queue flooding
- ✅ GraphQL query bombs

**Next Steps:**
1. Install Flask-Limiter: `pip install Flask-Limiter`
2. Deploy and monitor
3. Adjust limits based on actual usage patterns
4. Consider Redis for production
5. Set up alerting for rate limit violations
