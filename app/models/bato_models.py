"""
Bato.to Database Models
SQLAlchemy models for storing Bato manga data scraped from batotwo.com
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, Text, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import text
from datetime import datetime

# Import the shared Base from the main app to ensure all models share the same metadata
from app.functions.class_mangalist import Base


class BatoMangaDetails(Base):
    """
    Stores comprehensive manga metadata from Bato.to
    Field names match GraphQL API (see BATOTWO_NAMING_CONVENTION.md)
    Connected via bato_link which matches manga_list.bato_link
    """
    __tablename__ = 'bato_manga_details'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, ForeignKey('manga_list.id_anilist'), nullable=False)
    bato_link = Column(String(500), unique=True, nullable=False)  # Full URL: https://batotwo.com/title/110100-...
    bato_id = Column(String(20), unique=True, nullable=False)  # Comic ID from API (e.g., "110100")
    
    # Basic Info (API fields)
    name = Column(String(500), nullable=False)  # API: name
    alt_names = Column(JSON, nullable=True)  # API: altNames - Array of alternative titles
    authors = Column(JSON, nullable=True)  # API: authors - Array of author names
    artists = Column(JSON, nullable=True)  # API: artists - Array of artist names
    genres = Column(JSON, nullable=True)  # API: genres - Array of genres (lowercase with underscores)
    
    # Publication Info (API fields)
    orig_lang = Column(String(10), nullable=True)  # API: origLang - Language code (ko/ja/zh/en)
    original_status = Column(String(50), nullable=True)  # API: originalStatus - ongoing/completed/hiatus/cancelled
    original_pub_from = Column(String(10), nullable=True)  # API: originalPubFrom - Start year
    original_pub_till = Column(String(10), nullable=True)  # API: originalPubTill - End year (null if ongoing)
    read_direction = Column(String(10), nullable=True)  # API: readDirection - ltr/rtl
    
    # Bato-specific (API fields)
    upload_status = Column(String(50), nullable=True)  # API: uploadStatus - ongoing/completed/dropped (scraping frequency)
    
    # Rating Data (API fields - stat_score_*)
    stat_score_val = Column(Float, nullable=True)  # API: stat_score_val - Average rating 0-10 (e.g., 8.72)
    stat_count_votes = Column(Integer, default=0)  # API: stat_count_votes - Total votes (e.g., 1365)
    stat_count_scores = Column(JSON, nullable=True)  # API: stat_count_scores - [{field: "10", count: 567}, ...]
    
    # Statistics (API fields - stat_count_*)
    stat_count_follows = Column(Integer, default=0)  # API: stat_count_follows - Followers (e.g., 20075)
    stat_count_reviews = Column(Integer, default=0)  # API: stat_count_reviews - Reviews (e.g., 90)
    stat_count_post_reply = Column(Integer, default=0)  # API: stat_count_post_reply - Comments/replies (e.g., 7458)
    stat_count_views_total = Column(Integer, default=0)  # API: stat_count_views[field="d000"] - All-time views
    
    # Emotions (reactions) (API field)
    stat_count_emotions = Column(JSON, nullable=True)  # API: stat_count_emotions - [{field: "upvote", count: 71}, ...]
    
    # Content (API field)
    summary = Column(Text, nullable=True)  # API: summary.text
    
    # Metadata
    first_scraped_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    last_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    
    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)


class BatoChapters(Base):
    """
    Stores individual chapter data from Bato.to
    Field names match GraphQL API (see BATOTWO_NAMING_CONVENTION.md)
    Each chapter is tracked for new chapter detection
    """
    __tablename__ = 'bato_chapters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, ForeignKey('manga_list.id_anilist'), nullable=False)
    bato_link = Column(String(500), ForeignKey('bato_manga_details.bato_link'), nullable=False)
    bato_chapter_id = Column(String(20), unique=True, nullable=False)  # API: id - Chapter ID (e.g., "2068065")
    
    # Chapter Info (API fields)
    chapter_number = Column(Integer, nullable=False)  # Computed: 1, 2, 3... (position in list)
    dname = Column(String(500), nullable=False)  # API: dname - Display name (e.g., "Chapter 112")
    title = Column(String(500), nullable=True)  # API: title - Optional chapter title/subtitle (can be null)
    url_path = Column(String(500), nullable=False)  # API: urlPath - Relative URL path
    full_url = Column(String(500), nullable=False)  # Computed: Full chapter URL (https://batotwo.com + url_path)
    
    # Dates (API fields)
    date_create = Column(TIMESTAMP, nullable=True)  # API: dateCreate - Creation timestamp
    date_public = Column(TIMESTAMP, nullable=True)  # API: datePublic - Publication timestamp
    
    # Statistics (API fields - stat_count_*)
    stat_count_views_guest = Column(Integer, default=0)  # API: stat_count_views_guest - Guest views
    stat_count_views_login = Column(Integer, default=0)  # API: stat_count_views_login - Logged-in user views
    stat_count_views_total = Column(Integer, default=0)  # Computed: guest + login views
    stat_count_post_reply = Column(Integer, default=0)  # API: stat_count_post_reply - Comments count
    
    # User Tracking
    is_read = Column(Boolean, default=False)  # For future user interaction
    
    # Metadata
    first_seen_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))  # When we first discovered this chapter
    
    # Ensure no duplicate chapters per manga
    __table_args__ = (
        UniqueConstraint('bato_link', 'chapter_number', name='unique_chapter_per_manga'),
        UniqueConstraint('bato_chapter_id', name='unique_bato_chapter_id'),
    )
    
    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)


class BatoNotifications(Base):
    """
    Stores notifications for Bato manga updates
    Triggers when new chapters are found or status changes
    Uses consistent naming with API fields
    """
    __tablename__ = 'bato_notifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, ForeignKey('manga_list.id_anilist'), nullable=False)
    bato_link = Column(String(500), ForeignKey('bato_manga_details.bato_link'), nullable=False)
    
    # Notification Info
    notification_type = Column(String(50), nullable=False)  # "new_chapter", "status_change", "batch_update"
    manga_name = Column(String(500), nullable=False)  # Manga name for display (from API: name)
    message = Column(Text, nullable=False)  # "New chapter 112 available!"
    
    # Chapter-specific (if notification_type = "new_chapter")
    chapter_id = Column(Integer, ForeignKey('bato_chapters.id'), nullable=True)
    chapter_dname = Column(String(500), nullable=True)  # Display name (e.g., "Chapter 112")
    chapter_full_url = Column(String(500), nullable=True)  # Full URL to chapter
    
    # Status change (if notification_type = "status_change")
    old_status = Column(String(50), nullable=True)  # Previous upload_status
    new_status = Column(String(50), nullable=True)  # New upload_status
    
    # Batch updates (if notification_type = "batch_update")
    chapters_count = Column(Integer, default=1)  # How many new chapters in this batch
    
    # User Interaction
    is_read = Column(Boolean, default=False)
    is_emitted = Column(Boolean, default=False)  # Track if notification has been emitted via SocketIO
    importance = Column(Integer, default=1)  # 1=normal, 2=important (batch), 3=critical (status change)
    
    # Metadata
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)


class BatoScraperLog(Base):
    """
    Logs scraping activity for monitoring and debugging
    Tracks when we scrape each manga and if it was successful
    """
    __tablename__ = 'bato_scraper_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, ForeignKey('manga_list.id_anilist'), nullable=False)
    bato_link = Column(String(500), ForeignKey('bato_manga_details.bato_link'), nullable=False)
    
    # Scraping Info
    scrape_type = Column(String(50), nullable=False)  # "details", "chapters", "full"
    status = Column(String(50), nullable=False)  # "success", "failed", "partial"
    
    # Results
    chapters_found = Column(Integer, default=0)  # How many chapters were found
    new_chapters = Column(Integer, default=0)  # How many were NEW (not in DB)
    
    # Error Handling
    error_message = Column(Text, nullable=True)  # If failed, store error
    
    # Performance
    duration_seconds = Column(Float, nullable=True)  # How long did scraping take
    
    # Metadata
    scraped_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)


class BatoScrapingSchedule(Base):
    """
    Tracks scraping schedules and release patterns for each manga
    Enables intelligent scheduling based on release history
    """
    __tablename__ = 'bato_scraping_schedule'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, ForeignKey('manga_list.id_anilist'), unique=True, nullable=False)
    bato_link = Column(String(500), ForeignKey('bato_manga_details.bato_link'), nullable=False)
    
    # Scheduling
    scraping_interval_hours = Column(Integer, default=24)  # How often to check for updates
    last_scraped_at = Column(TIMESTAMP, nullable=True)  # When we last scraped this manga
    next_scrape_at = Column(TIMESTAMP, nullable=False)  # When to check next (indexed for queries)
    
    # Pattern Analysis
    average_release_interval_days = Column(Float, nullable=True)  # Calculated from chapter history
    preferred_release_day = Column(Integer, nullable=True)  # 0=Monday, 6=Sunday (null if no pattern)
    release_pattern_confidence = Column(Float, default=0.0)  # 0.0-1.0 confidence in pattern
    
    # Statistics
    total_chapters_tracked = Column(Integer, default=0)  # Total chapters we've seen
    last_chapter_date = Column(TIMESTAMP, nullable=True)  # When last chapter was published
    consecutive_no_update_count = Column(Integer, default=0)  # Increase interval if no updates
    
    # Status
    is_active = Column(Boolean, default=True)  # Can be paused by user or system
    priority = Column(Integer, default=1)  # 1=normal, 2=high (user favorite), 3=urgent
    
    # Metadata
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    
    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)


def init_bato_db(engine):
    """
    Initialize all Bato tables in the database
    Call this from your main init_db() function
    """
    Base.metadata.create_all(bind=engine)
    
    # Create tables if they don't exist
    BatoMangaDetails.create_table_if_not_exists(engine)
    BatoChapters.create_table_if_not_exists(engine)
    BatoNotifications.create_table_if_not_exists(engine)
    BatoScraperLog.create_table_if_not_exists(engine)
    BatoScrapingSchedule.create_table_if_not_exists(engine)
    
    print("✅ Bato database tables initialized")
