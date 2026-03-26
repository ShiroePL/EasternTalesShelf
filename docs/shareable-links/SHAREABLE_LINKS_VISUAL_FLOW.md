# 🎯 Shareable Links - Visual Flow Diagram

## 📊 System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     SHAREABLE MANHWA LINKS                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         SCENARIO 1:                             │
│                    User Clicks Manhwa                           │
└─────────────────────────────────────────────────────────────────┘

  User                Browser                  Server
   │                     │                       │
   │   Click Manhwa      │                       │
   │────────────────────>│                       │
   │                     │                       │
   │                     │  showDetails()        │
   │                     │  ┌──────────────┐     │
   │                     │  │ Fetch data   │     │
   │                     │  │ via GraphQL  │────>│
   │                     │  │              │<────│
   │                     │  └──────────────┘     │
   │                     │                       │
   │                     │  pushState()          │
   │                     │  ┌──────────────┐     │
   │  URL Changes!       │  │ Update URL:  │     │
   │<────────────────────│  │ /manhwa/123/ │     │
   │  /manhwa/123/title  │  │ solo-leveling│     │
   │                     │  └──────────────┘     │
   │                     │                       │
   │  Sidebar Opens!     │  Show Right Sidebar   │
   │<────────────────────│  with Details         │
   │                     │                       │


┌─────────────────────────────────────────────────────────────────┐
│                         SCENARIO 2:                             │
│            Someone Visits Shared Link                           │
└─────────────────────────────────────────────────────────────────┘

  Friend              Browser                  Server
   │                     │                       │
   │  Paste Link         │                       │
   │  /manhwa/123/title  │                       │
   │────────────────────>│                       │
   │                     │                       │
   │                     │  GET /manhwa/123/...  │
   │                     │──────────────────────>│
   │                     │                       │
   │                     │       manhwa_page()   │
   │                     │       ┌─────────────┐ │
   │                     │       │ Fetch from  │ │
   │                     │       │ Database    │ │
   │                     │       │ anilist_id  │ │
   │                     │       │ = 123       │ │
   │                     │       └─────────────┘ │
   │                     │                       │
   │                     │       Generate OG Tags│
   │                     │       ┌─────────────┐ │
   │                     │       │ og:title    │ │
   │                     │       │ og:image    │ │
   │                     │       │ og:desc     │ │
   │                     │       │ og:score    │ │
   │                     │       └─────────────┘ │
   │                     │                       │
   │  HTML with OG tags  │<──────────────────────│
   │<────────────────────│                       │
   │                     │                       │
   │                     │  DOMContentLoaded     │
   │                     │  ┌──────────────┐     │
   │                     │  │ Detect URL   │     │
   │                     │  │ /manhwa/123  │     │
   │                     │  │              │     │
   │                     │  │ Find element │     │
   │                     │  │ [data-       │     │
   │                     │  │ anilist-id=  │     │
   │                     │  │ "123"]       │     │
   │                     │  │              │     │
   │                     │  │ showDetails()│     │
   │                     │  └──────────────┘     │
   │                     │                       │
   │  Sidebar Opens!     │  Automatically!       │
   │<────────────────────│                       │


┌─────────────────────────────────────────────────────────────────┐
│                         SCENARIO 3:                             │
│              Discord Generates Preview                          │
└─────────────────────────────────────────────────────────────────┘

  Discord Bot          Browser                  Your Server
   │                     │                       │
   │  User pastes link   │                       │
   │  in Discord         │                       │
   │                     │                       │
   │  GET /manhwa/123/...│                       │
   │────────────────────>│──────────────────────>│
   │                     │                       │
   │                     │       manhwa_page()   │
   │                     │       Fetch Data      │
   │                     │       Generate OG     │
   │                     │                       │
   │  HTML with OG tags  │<──────────────────────│
   │<────────────────────│                       │
   │                     │                       │
   │  Parse <meta>       │                       │
   │  ┌──────────────┐   │                       │
   │  │ og:title     │   │                       │
   │  │ og:image     │   │                       │
   │  │ og:desc      │   │                       │
   │  └──────────────┘   │                       │
   │                     │                       │
   │  Display Preview!   │                       │
   │  ┌────────────────┐ │                       │
   │  │ [Cover Image]  │ │                       │
   │  │ Solo Leveling  │ │                       │
   │  │ Rating: 8.5/10 │ │                       │
   │  │ Description... │ │                       │
   │  └────────────────┘ │                       │


┌─────────────────────────────────────────────────────────────────┐
│                         SCENARIO 4:                             │
│                 Browser Back/Forward                            │
└─────────────────────────────────────────────────────────────────┘

  User                Browser                  
   │                     │                       
   │  Click Back Button  │                       
   │────────────────────>│                       
   │                     │                       
   │                     │  popstate event       
   │                     │  ┌──────────────┐     
   │                     │  │ Check state  │     
   │                     │  │ = null?      │     
   │                     │  │              │     
   │                     │  │ Close sidebar│     
   │                     │  └──────────────┘     
   │                     │                       
   │  URL: /             │  URL changes to /     
   │<────────────────────│                       
   │  Sidebar Closes     │                       
   │<────────────────────│                       
   │                     │                       
   │                     │                       
   │  Click Forward      │                       
   │────────────────────>│                       
   │                     │                       
   │                     │  popstate event       
   │                     │  ┌──────────────┐     
   │                     │  │ state.       │     
   │                     │  │ anilistId    │     
   │                     │  │ = 123        │     
   │                     │  │              │     
   │                     │  │ Find element │     
   │                     │  │ showDetails()│     
   │                     │  └──────────────┘     
   │                     │                       
   │  URL: /manhwa/...   │                       
   │<────────────────────│                       
   │  Sidebar Opens!     │                       
   │<────────────────────│                       
```

## 🔧 Code Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      FILE STRUCTURE                             │
└─────────────────────────────────────────────────────────────────┘

app/
├── static/js/
│   └── RightSidebarMain.js ──────┐
│       ├── showDetails()          │ ← Updates URL with pushState()
│       ├── popstate listener      │ ← Handles back/forward
│       └── DOMContentLoaded       │ ← Auto-opens on page load
│
├── blueprints/
│   └── main.py ──────────────────┐
│       ├── home() route /         │ ← Default Open Graph tags
│       └── manhwa_page() route    │ ← Dynamic Open Graph tags
│           /manhwa/<id>/<slug>    │
│
├── functions/
│   └── sqlalchemy_fns.py ─────────┐
│       └── get_manga_by_anilist_id() ← Fetch data for OG tags
│
└── templates/
    ├── components/
    │   └── _meta_tags.html ───────┐
    │       ├── {% if og_data %}    │ ← Dynamic OG tags
    │       └── {% else %}          │ ← Default OG tags
    │
    └── pages/
        └── index.html
```

## 🎨 Open Graph Tag Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPEN GRAPH META TAGS                         │
└─────────────────────────────────────────────────────────────────┘

When Discord/Facebook/Twitter fetch your link:

<html>
  <head>
    <!-- These tags are READ by social media bots -->
    
    <meta property="og:title" content="Solo Leveling" />
    └──> Shows as the main title in preview
    
    <meta property="og:description" content="10 years ago..." />
    └──> Shows as the description text
    
    <meta property="og:image" content="https://cover.jpg" />
    └──> Shows as the preview image
    
    <meta property="og:url" content="https://your.site/manhwa/123/..." />
    └──> The actual link
    
    <meta property="og:type" content="book" />
    └──> Tells it's a book/manhwa
    
    <meta property="book:rating:value" content="8.5" />
    <meta property="book:rating:scale" content="10" />
    └──> Book-specific data (score)
    
    <!-- Twitter also reads these -->
    <meta name="twitter:card" content="summary_large_image" />
    └──> Large image preview style
  </head>
  <body>
    <!-- Page content -->
  </body>
</html>

Discord Bot reads <head>, ignores <body>
└──> Generates beautiful preview card!
```

## 📱 Discord Preview Generation

```
┌─────────────────────────────────────────────────────────────────┐
│              HOW DISCORD CREATES PREVIEW                        │
└─────────────────────────────────────────────────────────────────┘

Step 1: User pastes link
   https://easterntalesshelf.site/manhwa/123456/solo-leveling

Step 2: Discord bot sends GET request
   GET /manhwa/123456/solo-leveling
   User-Agent: DiscordBot

Step 3: Your server responds with HTML containing OG tags
   <meta property="og:title" content="Solo Leveling" />
   <meta property="og:image" content="https://cover.jpg" />
   <meta property="og:description" content="..." />

Step 4: Discord parses the meta tags
   title     = "Solo Leveling"
   image_url = "https://cover.jpg"
   desc      = "10 years ago, after..."

Step 5: Discord downloads the image
   GET https://cover.jpg

Step 6: Discord generates embed card
   ┌──────────────────────────┐
   │  [Downloaded Image]      │
   │  Solo Leveling           │
   │  10 years ago, after...  │
   │  🔗 easterntalesshelf... │
   └──────────────────────────┘

Step 7: Discord caches the preview
   (Won't fetch again for ~24 hours)
```

## 🔄 URL Update Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  HISTORY API (pushState)                        │
└─────────────────────────────────────────────────────────────────┘

Traditional Web (OLD WAY):
   Click link → Server request → Page reload → New URL
   ❌ Slow, loses state, jarring experience

Single Page Application (NEW WAY):
   Click → JavaScript → Update URL → No reload
   ✅ Fast, smooth, keeps state

How pushState Works:
   
   Before: https://site.com/
   
   JavaScript executes:
   window.history.pushState(
     { anilistId: 123 },    // State data
     '',                     // Title (unused)
     '/manhwa/123/title'    // New URL
   );
   
   After: https://site.com/manhwa/123/title
   
   ✨ URL changed WITHOUT page reload!
   ✨ Browser back button works!
   ✨ Can share the new URL!
```

## 🎯 Complete Request/Response Flow

```
┌─────────────────────────────────────────────────────────────────┐
│           COMPLETE DATA FLOW (Direct Link Visit)                │
└─────────────────────────────────────────────────────────────────┘

Browser                           Flask Server                     Database
   │                                    │                              │
   │  GET /manhwa/123456/solo-leveling  │                              │
   │───────────────────────────────────>│                              │
   │                                    │                              │
   │                                    │  Route matched:              │
   │                                    │  @main_bp.route(             │
   │                                    │    '/manhwa/<int:id>/<slug>' │
   │                                    │  )                           │
   │                                    │                              │
   │                                    │  manhwa_page(123456, "...")  │
   │                                    │  ┌─────────────────────────┐ │
   │                                    │  │ Get manhwa data         │ │
   │                                    │  └─────────────────────────┘ │
   │                                    │                              │
   │                                    │  get_manga_by_anilist_id(123456)
   │                                    │─────────────────────────────>│
   │                                    │                              │
   │                                    │  SELECT * FROM manga_list    │
   │                                    │  WHERE id_anilist = 123456   │
   │                                    │                              │
   │                                    │<─────────────────────────────│
   │                                    │  {                           │
   │                                    │    title: "Solo Leveling",   │
   │                                    │    description: "...",       │
   │                                    │    cover_image: "...",       │
   │                                    │    score: 8.5,               │
   │                                    │    ...                       │
   │                                    │  }                           │
   │                                    │                              │
   │                                    │  Prepare og_data             │
   │                                    │  ┌─────────────────────────┐ │
   │                                    │  │ og_data = {             │ │
   │                                    │  │   'title': ...,         │ │
   │                                    │  │   'image': ...,         │ │
   │                                    │  │   'description': ...,   │ │
   │                                    │  │   'score': ...          │ │
   │                                    │  │ }                       │ │
   │                                    │  └─────────────────────────┘ │
   │                                    │                              │
   │                                    │  render_template(            │
   │                                    │    'pages/index.html',       │
   │                                    │    og_data=og_data           │
   │                                    │  )                           │
   │                                    │                              │
   │  HTML Response                     │                              │
   │<───────────────────────────────────│                              │
   │  <html>                            │                              │
   │    <head>                          │                              │
   │      <meta property="og:title"     │                              │
   │        content="Solo Leveling" />  │                              │
   │      ...                           │                              │
   │    </head>                         │                              │
   │    <body>...</body>                │                              │
   │  </html>                           │                              │
   │                                    │                              │
   │  Page loads                        │                              │
   │  ┌──────────────────────┐          │                              │
   │  │ DOMContentLoaded     │          │                              │
   │  │ Detect /manhwa/123.. │          │                              │
   │  │ Find grid element    │          │                              │
   │  │ showDetails()        │          │                              │
   │  └──────────────────────┘          │                              │
   │                                    │                              │
   │  Sidebar opens automatically!      │                              │
```

---

**Visual guide to help understand the complete flow! 🎉**
