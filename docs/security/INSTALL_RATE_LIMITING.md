# 🚀 Quick Start: Installing Rate Limiting

## Installation Steps

### 1. Install Flask-Limiter
```bash
pip install Flask-Limiter
```

Or using your virtual environment:
```bash
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install Flask-Limiter
```

### 2. Verify Installation
```bash
pip list | Select-String "Flask-Limiter"
```

Should show:
```
Flask-Limiter    3.5.0
limits           3.6.0
```

### 3. Start the Application
```bash
python app.py
# or
.\run_app.bat
# or
.\run_app.ps1
```

### 4. Test Rate Limiting

#### Test Login Rate Limit (5 per minute)
```powershell
# Should block after 5 attempts
1..10 | ForEach-Object {
    Invoke-WebRequest -Uri "http://localhost:5001/login" `
        -Method POST `
        -Body @{username="test"; password="wrong"} `
        -UseBasicParsing
    Start-Sleep -Seconds 2
}
```

#### Check Response Headers
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:5001/api/notifications" `
    -Headers @{Cookie="session=your-session-cookie"} `
    -UseBasicParsing

# View rate limit headers
$response.Headers["X-RateLimit-Limit"]
$response.Headers["X-RateLimit-Remaining"]
$response.Headers["X-RateLimit-Reset"]
```

## What Changed?

### Files Modified
- ✅ `app/app.py` - Initialized Flask-Limiter
- ✅ `app/blueprints/auth.py` - Added login protection (5/min)
- ✅ `app/blueprints/api.py` - Added API rate limits (20/min)
- ✅ `app/blueprints/graphql.py` - Added GraphQL protection (10/min)
- ✅ `app/blueprints/download.py` - Protected queue operations
- ✅ `app/blueprints/manga.py` - Protected scraping triggers (10/min)
- ✅ `app/blueprints/extension.py` - Protected extension endpoints
- ✅ `app/blueprints/bato_notifications.py` - Protected Bato endpoints
- ✅ `app/blueprints/bato_admin.py` - Protected admin endpoints
- ✅ `app/blueprints/webhook.py` - Protected webhook controls
- ✅ `app/blueprints/notifications.py` - Protected notification endpoints
- ✅ `app/blueprints/main.py` - Protected user settings
- ✅ `requirements.txt` - Added Flask-Limiter dependencies
- ✅ `requirements.in` - Added Flask-Limiter

### New Files
- 📄 `RATE_LIMITING_SECURITY.md` - Complete documentation
- 📄 `INSTALL_RATE_LIMITING.md` - This installation guide

## Quick Reference

### Rate Limit Tiers

| Tier | Limit | Use Case |
|------|-------|----------|
| **Very Strict** | 5/min | Login, sync, manual scraping |
| **Strict** | 10/min | GraphQL, add_bato, batch operations |
| **Moderate** | 20/min | API endpoints, notifications |
| **Generous** | 30/min | Lightweight operations |
| **Default** | 50/min | Standard endpoints |

### Common Endpoints

```python
# Authentication
POST /login                    # 5 per minute ⚠️ STRICT

# GraphQL
POST /graphql/                 # 10 per minute ⚠️ STRICT
POST /graphql/public          # 20 per minute

# Manga Operations
POST /add_bato                # 10 per minute ⚠️ STRICT
POST /sync                    # 5 per minute ⚠️ VERY STRICT

# API
GET  /api/notifications       # 20 per minute
POST /api/notifications/{id}/read  # 30 per minute

# Extension
POST /extension/reading-time  # 30 per minute
POST /extension/reading-time-batch  # 10 per minute

# Admin
GET  /api/bato/admin/stats   # 30 per minute
POST /api/bato/scrape/{id}   # 5 per minute ⚠️ VERY STRICT
```

## Troubleshooting

### Error: "No module named 'flask_limiter'"
```bash
pip install Flask-Limiter
```

### Error: "429 Too Many Requests" During Development
Option 1: Wait for rate limit to reset (check `X-RateLimit-Reset` header)

Option 2: Temporarily disable in development (in `app/app.py`):
```python
if os.getenv('FLASK_ENV') == 'development':
    limiter.enabled = False
```

### Rate Limits Not Working
1. Check Flask-Limiter is installed: `pip show Flask-Limiter`
2. Verify app.py imports: Look for `from flask_limiter import Limiter`
3. Check logs for initialization errors

### Shared IP Issues (NAT/VPN)
Multiple users behind same IP share rate limits. For production:
1. Use Redis storage
2. Implement user-based rate limiting for authenticated routes
3. Increase limits for authenticated users

## Production Setup

### Use Redis (Recommended)
```bash
# Install Redis
pip install redis

# Update app.py
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",  # Use Redis
    default_limits=["200 per hour", "50 per minute"]
)
```

### Docker Redis
```yaml
# Add to docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## Monitoring

### View Rate Limit Info
Every response includes:
```
X-RateLimit-Limit: 20        # Max requests allowed
X-RateLimit-Remaining: 15    # Requests left
X-RateLimit-Reset: 1699999999  # When limit resets (Unix timestamp)
```

### Log Rate Limit Violations
Add to `app.py`:
```python
@app.after_request
def log_rate_limits(response):
    if response.status_code == 429:
        app.logger.warning(f"Rate limit exceeded: {request.path} from {request.remote_addr}")
    return response
```

## Next Steps

1. ✅ Install Flask-Limiter
2. ✅ Test rate limiting locally
3. ✅ Review rate limits in `RATE_LIMITING_SECURITY.md`
4. ✅ Adjust limits based on your usage patterns
5. ✅ Deploy to production
6. ✅ Monitor for 429 errors
7. ✅ Consider Redis for distributed rate limiting

## Questions?

See full documentation in `RATE_LIMITING_SECURITY.md` for:
- Detailed endpoint breakdown
- Security benefits
- Attack scenarios prevented
- Testing examples
- Production recommendations
