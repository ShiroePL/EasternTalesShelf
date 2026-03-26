# Shareable Manhwa Links Guide 🔗

## Overview

Your website now supports **shareable direct links** to individual manhwa! Just like AniList, when you click on a manhwa, the URL updates to include that specific manhwa, and when you share that link with someone, it opens your site with that manhwa's details displayed.

## How It Works

### 1. **URL Changes When Clicking Manhwa** 
When you click on any manhwa in the grid:
- The right sidebar opens as usual with all the details
- **The URL automatically updates** to: `/manhwa/{anilist-id}/{title-slug}`
- Example: `/manhwa/123456/solo-leveling`

This uses the **History API** (`window.history.pushState()`), which changes the URL **without reloading the page**.

### 2. **Browser Navigation (Back/Forward)**
- Clicking the browser's back button closes the sidebar and returns to the home view
- The forward button reopens the previously viewed manhwa
- All handled smoothly without page reloads

### 3. **Direct Link Sharing**
When someone visits a direct link like:
```
https://easterntalesshelf.site/manhwa/123456/solo-leveling
```

The page:
1. Loads normally with all your manhwa
2. Automatically finds and opens the manhwa with ID `123456`
3. Shows the right sidebar with full details

### 4. **Discord Link Previews (Open Graph)**
When you paste a manhwa link into Discord (or Facebook, Twitter, etc.):

**Dynamic Meta Tags Include:**
- ✅ Manhwa title
- ✅ Description (first 200 characters)
- ✅ Cover image
- ✅ Score/rating
- ✅ Chapter progress
- ✅ Reading status

Discord will display a beautiful preview card with:
```
┌─────────────────────────────┐
│  [Cover Image]              │
│                             │
│  Solo Leveling              │
│  Score: 8.5/10              │
│  After the appearance of... │
│                             │
│  🔗 easterntalesshelf.site  │
└─────────────────────────────┘
```

## Technical Implementation

### Frontend (JavaScript)
**File:** `app/static/js/RightSidebarMain.js`

```javascript
// When manhwa is clicked, update URL
const titleSlug = localSeriesName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
const newUrl = `/manhwa/${localAnilistId}/${titleSlug}`;
window.history.pushState(
    { anilistId: localAnilistId, title: localSeriesName }, 
    '', 
    newUrl
);
```

**Features Added:**
- `pushState()` to change URL without reload
- `popstate` event listener for browser navigation
- Auto-open manhwa when page loads with `/manhwa/` URL

### Backend (Flask)
**File:** `app/blueprints/main.py`

```python
@main_bp.route('/manhwa/<int:anilist_id>/<slug>')
def manhwa_page(anilist_id, slug):
    """Handle direct links to specific manhwa with dynamic Open Graph tags"""
    manhwa_data = sqlalchemy_fns.get_manga_by_anilist_id(anilist_id)
    
    og_data = {
        'title': manhwa_data.get('title_english'),
        'description': manhwa_data.get('description'),
        'image': manhwa_data.get('cover_image'),
        'score': manhwa_data.get('score'),
        # ... more data
    }
    
    return render_template('pages/index.html', og_data=og_data)
```

### Database Query
**File:** `app/functions/sqlalchemy_fns.py`

```python
def get_manga_by_anilist_id(anilist_id):
    """Fetch a single manga entry by anilist_id for Open Graph meta tags."""
    manga = db_session.query(MangaList).filter(
        MangaList.id_anilist == anilist_id
    ).first()
    return manga_dict
```

### Meta Tags Template
**File:** `app/templates/components/_meta_tags.html`

```html
{% if og_data %}
    <meta property="og:title" content="{{ og_data.title }}" />
    <meta property="og:description" content="{{ og_data.description[:200] }}..." />
    <meta property="og:image" content="{{ og_data.image }}" />
    <meta property="og:type" content="book" />
    <meta property="book:rating:value" content="{{ og_data.score }}" />
{% endif %}
```

## Usage Examples

### For Users:
1. **Browse and share:**
   - Click any manhwa
   - Copy the URL from the address bar
   - Share it on Discord, social media, or with friends

2. **Direct access:**
   - Someone clicks your shared link
   - They see your full site with that specific manhwa open
   - They can explore other manhwa from there

### For Developers:
- The URL slug is SEO-friendly (contains the title)
- The anilist_id ensures the correct manhwa loads
- Open Graph tags make links look professional everywhere
- No page reloads = better UX

## Benefits

### 🎯 **User Experience**
- Share specific manhwa with friends
- Bookmark favorite manhwa directly
- Browser navigation works intuitively

### 📱 **Social Media Integration**
- Beautiful previews on Discord, Twitter, Facebook
- Shows cover art, title, rating automatically
- Drives more traffic to your site

### 🔍 **SEO Improvements**
- Each manhwa has its own URL
- Search engines can index individual manhwa
- Better discoverability

### 💻 **Technical Advantages**
- Single Page Application (SPA) feel
- Fast navigation (no reloads)
- Backward compatible with existing functionality

## Testing

### Test Local Development:
1. Run your Flask app
2. Click a manhwa
3. Check the URL changed to `/manhwa/123456/title-slug`
4. Refresh the page - manhwa should auto-open
5. Click back button - sidebar should close

### Test Open Graph Tags:
1. Deploy to your production server
2. Get a manhwa link like: `https://easterntalesshelf.site/manhwa/123456/solo-leveling`
3. Paste it into Discord
4. Check if the preview shows:
   - ✅ Cover image
   - ✅ Title
   - ✅ Description
   - ✅ Score

### Test with Facebook Debugger:
Visit: https://developers.facebook.com/tools/debug/
- Paste your manhwa URL
- Click "Scrape Again"
- Verify all Open Graph tags are correct

## Future Enhancements

### Possible Additions:
- [ ] Generate custom OG images with score overlay (like AniList)
- [ ] Add JSON-LD structured data for Google
- [ ] Support for chapter-specific links (`/manhwa/123/title/chapter/45`)
- [ ] Analytics tracking for shared links
- [ ] QR codes for easy mobile sharing

### Advanced OG Image Generation:
You could create dynamic images server-side:

```python
from PIL import Image, ImageDraw, ImageFont

@main_bp.route('/og-image/<int:anilist_id>')
def generate_og_image(anilist_id):
    # Fetch manhwa data
    # Load cover image
    # Add score overlay
    # Add title text
    # Return generated image
    pass
```

## Troubleshooting

### URL doesn't change when clicking manhwa
- Check browser console for JavaScript errors
- Verify `RightSidebarMain.js` is loaded
- Check if `showDetails()` function is being called

### Direct link doesn't open manhwa
- Verify the anilist_id exists in your database
- Check Flask route is registered
- Look at browser console for errors

### Discord doesn't show preview
- Ensure your site is publicly accessible (not localhost)
- Open Graph tags must be in `<head>` before JavaScript
- Discord caches previews - use Facebook debugger to force refresh

### Sidebar doesn't auto-open on page load
- Check the `DOMContentLoaded` event listener
- Verify manga grid is loaded before trying to open details
- Increase the interval timeout if needed

## Notes

- The URL slug (e.g., "solo-leveling") is **optional** - the anilist_id is what matters
- `/manhwa/123456/anything-here` will work fine
- This is good for SEO but the actual matching is ID-based
- Works seamlessly with your existing GraphQL-based data fetching

---

**Enjoy sharing your manhwa collection! 🎉**
