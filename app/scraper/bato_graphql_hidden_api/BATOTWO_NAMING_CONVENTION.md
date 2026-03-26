# Batotwo GraphQL API - Naming Convention Standard

**Purpose**: This document defines the official naming convention for all Batotwo data across our application.  
**Principle**: Use GraphQL API field names as the source of truth to avoid confusion.

---

## 📋 Comic/Manga Details API Fields

### GraphQL Query: `get_content_comicNode`

| GraphQL API Field | Type | Database Column | Description |
|------------------|------|-----------------|-------------|
| `id` | String | `bato_id` | Comic ID (e.g., "110100") |
| `name` | String | `name` | Official title |
| `altNames` | Array[String] | `alt_names` | Alternative titles (JSON) |
| `authors` | Array[String] | `authors` | Author names (JSON) |
| `artists` | Array[String] | `artists` | Artist names (JSON) |
| `genres` | Array[String] | `genres` | Genre tags (JSON) |
| `origLang` | String | `orig_lang` | Original language code (ko/ja/zh/en) |
| `originalStatus` | String | `original_status` | Publication status (ongoing/completed/hiatus/cancelled) |
| `originalPubFrom` | String | `original_pub_from` | Start year |
| `originalPubTill` | String/null | `original_pub_till` | End year (null if ongoing) |
| `uploadStatus` | String | `upload_status` | Bato upload status (ongoing/completed/dropped) |
| `readDirection` | String | `read_direction` | Reading direction (ltr/rtl) |
| `summary.text` | String | `summary` | Plot summary |

### Rating Fields
| GraphQL API Field | Type | Database Column | Description |
|------------------|------|-----------------|-------------|
| `stat_score_val` | Float | `stat_score_val` | Average rating (0-10) |
| `stat_count_votes` | Integer | `stat_count_votes` | Total votes |
| `stat_count_scores` | Array[Object] | `stat_count_scores` | Distribution (JSON: [{field: "1", count: 5}, ...]) |

### Statistics Fields
| GraphQL API Field | Type | Database Column | Description |
|------------------|------|-----------------|-------------|
| `stat_count_follows` | Integer | `stat_count_follows` | Followers count |
| `stat_count_reviews` | Integer | `stat_count_reviews` | Reviews count |
| `stat_count_post_reply` | Integer | `stat_count_post_reply` | Comments/replies count |
| `stat_count_views[{field:"d000"}]` | Integer | `stat_count_views_total` | Total all-time views |
| `stat_count_emotions` | Array[Object] | `stat_count_emotions` | Reactions (JSON: [{field: "upvote", count: 71}, ...]) |

---

## 📖 Chapter List API Fields

### GraphQL Query: `get_content_chapterList`

| GraphQL API Field | Type | Database Column | Description |
|------------------|------|-----------------|-------------|
| `id` | String | `bato_chapter_id` | Chapter ID (e.g., "2068065") |
| `dname` | String | `dname` | Display name (e.g., "Chapter 1") |
| `title` | String/null | `title` | Optional chapter title/subtitle |
| `urlPath` | String | `url_path` | Relative URL path |
| `stat_count_views_guest` | Integer | `stat_count_views_guest` | Guest views |
| `stat_count_views_login` | Integer | `stat_count_views_login` | Logged-in user views |
| `stat_count_post_reply` | Integer | `stat_count_post_reply` | Comments count |
| `dateCreate` | ISO String | `date_create` | Creation timestamp |
| `datePublic` | ISO String | `date_public` | Publication timestamp |

---

## 🎯 Naming Rules

### 1. **Keep Original API Names Where Possible**
- ✅ `stat_count_views_guest` → `stat_count_views_guest`
- ✅ `stat_count_post_reply` → `stat_count_post_reply`
- ❌ Don't rename to `comments_count` (non-standard)

### 2. **Snake_case for Database Columns**
- GraphQL uses camelCase: `datePublic`
- Database uses snake_case: `date_public`

### 3. **Prefixes for Clarity**
- `bato_id` - Bato comic/manga ID
- `bato_chapter_id` - Bato chapter ID  
- `stat_count_*` - All statistics use this prefix (from API)
- `date_*` - All dates use this prefix

### 4. **Special Conversions**
| GraphQL | Python/Output | Database | Notes |
|---------|---------------|----------|-------|
| `id` (comic) | `bato_id` | `bato_id` | Avoid generic "id" |
| `id` (chapter) | `bato_chapter_id` | `bato_chapter_id` | Avoid generic "id" |
| `dname` | `dname` | `dname` | Keep as-is (display name) |
| `origLang` | `orig_lang` | `orig_lang` | Snake_case |
| `datePublic` | `date_public` | `date_public` | Snake_case + ISO → MySQL format |

### 5. **Computed/Derived Fields**
These are NOT in the API but we calculate them:

| Field | Type | Description | Formula |
|-------|------|-------------|---------|
| `stat_count_views_total` | Integer | Total views (guest + login) | `views_guest + views_login` |
| `chapter_number` | Integer | Sequential chapter number | Position in list (1, 2, 3...) |
| `full_url` | String | Complete URL | `https://batotwo.com` + `url_path` |

---

## 📦 Output Format Standards

### Manga Details Output
```json
{
  "bato_id": "110100",
  "name": "The Villainess's Stationery Shop",
  "alt_names": ["악녀의 문구점에 오지 마세요!", ...],
  "authors": ["S.moo", "yeoroeun"],
  "artists": ["Minjeolmi"],
  "genres": ["adaptation", "fantasy", ...],
  "orig_lang": "ko",
  "original_status": "ongoing",
  "original_pub_from": "2022",
  "original_pub_till": null,
  "upload_status": "ongoing",
  "read_direction": "ltr",
  "summary": "What's a girl to do...",
  "stat_score_val": 8.72,
  "stat_count_votes": 1365,
  "stat_count_scores": [{"field": "10", "count": 567}, ...],
  "stat_count_follows": 20075,
  "stat_count_reviews": 90,
  "stat_count_post_reply": 7458,
  "stat_count_views_total": 1475049,
  "stat_count_emotions": [{"field": "upvote", "count": 71}, ...]
}
```

### Chapter List Output
```json
{
  "bato_id": "110100",
  "name": "The Villainess's Stationery Shop",
  "total_chapters": 112,
  "chapters": [
    {
      "bato_chapter_id": "2068065",
      "chapter_number": 1,
      "dname": "Chapter 1",
      "title": null,
      "url_path": "/title/110100-.../2068065-ch_1",
      "full_url": "https://batotwo.com/title/110100-.../2068065-ch_1",
      "stat_count_views_guest": 135239,
      "stat_count_views_login": 24584,
      "stat_count_views_total": 159823,
      "stat_count_post_reply": 115,
      "date_create": "2022-10-01 18:01:11",
      "date_public": "2022-10-01 18:01:11"
    }
  ]
}
```

---

## ⚠️ Important Notes

1. **Never use generic names** like `id`, `title`, `views` without context
2. **Always use API names** as source of truth for data fields
3. **Use snake_case** for Python/database, keep `stat_count_*` pattern
4. **Document computed fields** separately (not from API)
5. **Preserve API structure** in JSON columns (don't flatten unnecessarily)

---

## 🔄 Migration from Old Names

| Old Name | New Name | Reason |
|----------|----------|--------|
| `manga_id` | `bato_id` | More specific |
| `title` | `name` | Match API |
| `alt_titles` | `alt_names` | Match API |
| `chapter_order` | `chapter_number` | More clear |
| `uploaded_at` | `date_public` | Match API |
| `views` | `stat_count_views_total` | Match pattern |
| `views_raw` | (remove) | Redundant |
| `comments_count` | `stat_count_post_reply` | Match API |
| `rating_average` | `stat_score_val` | Match API |
| `rating_votes` | `stat_count_votes` | Match API |

---

**Last Updated**: 2025-10-20  
**Status**: Official Standard ✅
