import os
from sqlalchemy import create_engine, MetaData, inspect, text, Table, Column, Integer, String
from sqlalchemy.exc import SQLAlchemyError

def inspect_manga_schema():
    """Try to connect to the database and inspect the manga_list table schema"""
    
    # Try to get database URI from environment variable
    database_uri = os.environ.get("DATABASE_URI")
    
    if not database_uri:
        print("DATABASE_URI environment variable not set.")
        print("Please provide the database connection string.")
        uri_input = input("Database URI (leave empty to skip DB inspection): ")
        if not uri_input.strip():
            return False
        database_uri = uri_input
    
    try:
        print(f"Connecting to database: {database_uri}")
        engine = create_engine(database_uri)
        
        # Check connection
        with engine.connect() as conn:
            print("Successfully connected to database.")
        
        # Get metadata
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        # Check if manga_list table exists
        if 'manga_list' not in metadata.tables:
            print("Warning: manga_list table not found in database.")
            # Create a fictional manga_list table for demonstration
            manga_list = Table(
                'manga_list', metadata,
                Column('id_default', Integer, primary_key=True),
                Column('id_anilist', Integer, nullable=False),
                Column('title_english', String),
                # Add other columns as needed
            )
            print("Created fictional manga_list schema for demonstration.")
        else:
            manga_list = metadata.tables['manga_list']
            print("Found manga_list table in database.")
        
        # Print column types
        print("\nColumn Types in manga_list table:")
        for column in manga_list.columns:
            python_type = "unknown"
            try:
                python_type = column.type.python_type.__name__
            except NotImplementedError:
                pass
            
            print(f"  • {column.name}: {column.type} (Python type: {python_type}, Nullable: {column.nullable})")
        
        # Find id_anilist column
        id_anilist_col = manga_list.columns.get('id_anilist')
        if id_anilist_col:
            print(f"\nid_anilist column type: {id_anilist_col.type}")
            try:
                print(f"Python type: {id_anilist_col.type.python_type.__name__}")
            except NotImplementedError:
                print("Python type: could not determine")
        
        # Try to get sample data
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM manga_list LIMIT 1")).fetchone()
                if result:
                    print("\nSample data from manga_list:")
                    for key, value in result._mapping.items():
                        print(f"  {key}: {value} (Type: {type(value).__name__})")
                else:
                    print("\nNo data found in manga_list table.")
        except Exception as e:
            print(f"Could not fetch sample data: {e}")
        
        return True
    
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return False

def print_graphql_solutions():
    """Print possible GraphQL query solutions"""
    print("\n=== GraphQL Query Solutions ===")
    
    print("\n1. Query without variables (recommended for testing):")
    print("""
query {
  manga_list(filter: { id_anilist: { _eq: 142347 } }, limit: 1) {
    id_anilist
    title_english
    is_favourite
    on_list_status
    score
    chapters_progress
    all_chapters
    volumes_progress
    all_volumes
    status
    notes
    description
    bato_link
    reread_times
    user_startedAt
    user_completedAt
    media_start_date
    media_end_date
    genres
    external_links
  }
  mangaupdates_details(filter: { anilist_id: { _eq: 142347 } }, limit: 1) {
    status
    licensed
    completed
    last_updated_timestamp
  }
}
""")
    
    print("\n2. Using variables with a string literal in the filter:")
    print("""
# Notice we're NOT using variables in the filter expression
query GetMangaDetails($id: String!) {
  manga_list(filter: { id_anilist: { _eq: 142347 } }, limit: 1) {
    id_anilist
    title_english
    # ... other fields
  }
  mangaupdates_details(filter: { anilist_id: { _eq: 142347 } }, limit: 1) {
    # ... fields
  }
}

# We still define id as a variable but don't use it in the query
Variables: { "id": "142347" }
""")
    
    print("\n3. Using integer literals in the query (no variables):")
    print("""
query {
  manga_list(filter: { id_anilist: { _eq: 142347 } }, limit: 1) {
    id_anilist
    title_english
    # ... other fields
  }
}
""")
    
    print("\n4. Get all records without filtering (to see if basic queries work):")
    print("""
query {
  manga_list(limit: 5) {
    id_anilist
    title_english
  }
}
""")

def main():
    """Main function to run the script"""
    print("=== Manga List Schema Inspector ===")
    print("This script will attempt to connect to your database and inspect the manga_list table.")
    print("It will then provide GraphQL query solutions based on the schema.")
    
    # Try to inspect database schema
    db_inspection = inspect_manga_schema()
    
    # Print GraphQL solutions
    print_graphql_solutions()
    
    # Final recommendation
    print("\n=== Recommendation ===")
    print("Based on the Directus GraphQL error message, it appears there is a type mismatch.")
    print("The best approach is to try query #1 first (no variables) to see if that works.")
    print("If it does, then you can investigate why variables aren't working as expected.")

if __name__ == "__main__":
    main()
