"""
Batotwo GraphQL API Client
==========================

Kompletny klient do komunikacji z GraphQL API batotwo.com.
Pozwala pobierać dane o manhwa, rozdziałach, autorach i więcej!

Author: Shiro (for Madrus)
Date: 2025-10-20
"""

import requests
import json
import argparse
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from pathlib import Path


class BatotwoGraphQLClient:
    """
    Professional GraphQL client for Batotwo API.
    
    Discovers and uses the /apo/ endpoint which is their main GraphQL API.
    """
    
    def __init__(self, session_cookie: Optional[str] = None, verbose: bool = False):
        """
        Initialize the GraphQL client.
        
        Args:
            session_cookie: Optional session cookie for authenticated requests
            verbose: Enable verbose logging
        """
        self.endpoint = "https://batotwo.com/apo/"
        self.session = requests.Session()
        self.verbose = verbose
        
        # Set headers (based on discovered curl request)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': '*/*',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Content-Type': 'application/json',
            'Origin': 'https://batotwo.com',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        
        if session_cookie:
            self.session.headers['Cookie'] = session_cookie
        else:
            self.session.headers['Cookie'] = 'theme=dark'
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[DEBUG] {message}")
    
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Response data as dictionary
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        self._log(f"Executing query with variables: {variables}")
        
        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data:
                print(f"⚠️  GraphQL errors: {json.dumps(data['errors'], indent=2)}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            raise
    
    def introspect_schema(self) -> Dict[str, Any]:
        """
        Introspect the GraphQL schema to discover available queries.
        
        Note: Schema introspection is DISABLED on batotwo.com.
        This method will fail. Use the documented queries instead.
        """
        print("⚠️  Schema introspection is disabled on batotwo.com")
        print("    Use documented queries: get_content_comicNode, get_content_chapterList")
        
        query = """
        {
          __schema {
            queryType {
              name
              fields {
                name
                description
                args {
                  name
                  description
                  type {
                    name
                    kind
                    ofType {
                      name
                      kind
                    }
                  }
                }
              }
            }
            types {
              name
              description
              kind
              fields {
                name
                description
              }
            }
          }
        }
        """
        
        return self.execute_query(query)
    
    def get_comic_chapters(self, comic_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get chapter list for a comic.
        
        This uses the working query from the GraphQL scraper.
        """
        query = """
        query getChapters($comicId: ID!) {
          get_content_chapterList(comicId: $comicId) {
            id
            data {
              id
              dname
              title
              urlPath
              stat_count_views_guest
              stat_count_views_login
              stat_count_post_reply
              dateCreate
              datePublic
            }
          }
        }
        """
        
        variables = {"comicId": str(comic_id)}
        
        result = self.execute_query(query, variables)
        return result.get('data', {})
    
    def get_user_mylists(self, comic_id: int, limit: int = 5) -> Dict[str, Any]:
        """
        Get user mylists for a comic.
        
        This is the exact query discovered from network analysis.
        """
        query = """
        query get_marking_mylistList($select: Mylist_Select) {
          get_marking_mylistList(select: $select) {
            reqStart reqLimit newStart
            paging { 
              total pages page init size skip limit
            }
            items {
              id hash
              data {
                id
                hash
                dateCreate
                userId 
                name
                isPublic 
                count_comicIds
                count_vote_up count_vote_dn count_vote_ab
                urlPath
                stat_followers
                count_forum_child
                count_forum_reply
                userNode { 
                  id 
                  data {
                    id
                    name
                    uniq
                    avatarUrl 
                    urlPath
                    dateCreate
                    dateOnline
                    is_adm is_mod is_vip
                    is_verified is_deleted
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "select": {
                "where": "comicPage",
                "comicId": comic_id,
                "start": None,
                "limit": limit
            }
        }
        
        result = self.execute_query(query, variables)
        return result.get('data', {})
    
    def search_comics(self, search_term: str) -> Dict[str, Any]:
        """
        Search for comics by name.
        
        Note: Search functionality may not be available via GraphQL API.
        Use get_comic_details() if you know the comic ID.
        
        Args:
            search_term: Search query string
        """
        # Note: The search query structure is not confirmed to work
        # If this fails, you need to use the web interface or get_comic_details with known IDs
        query = """
        query SearchComics($search: String!) {
          search(
            text: $search
            scope: "comic"
          ) {
            items {
              id
              name
              urlPath
            }
          }
        }
        """
        
        variables = {"search": search_term}
        
        result = self.execute_query(query, variables)
        return result.get('data', {})
    
    def get_comic_basic_info(self, comic_id: int) -> Dict[str, Any]:
        """
        Get basic comic information.
        
        Args:
            comic_id: The comic ID
        """
        query = """
        query GetComicInfo($id: ID!) {
          get_content_comicNode(id: $id) {
            id
            data {
              id
              name
              urlPath
            }
          }
        }
        """
        
        variables = {"id": str(comic_id)}
        
        result = self.execute_query(query, variables)
        return result.get('data', {})
    
    def custom_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a custom GraphQL query.
        
        This allows you to experiment with your own queries!
        
        Args:
            query: Custom GraphQL query string
            variables: Optional variables
        """
        return self.execute_query(query, variables)


class BatotwoCLI:
    """Command-line interface for Batotwo API."""
    
    def __init__(self):
        self.client = None
        self.output_dir = Path("batotwo_data")
        self.output_dir.mkdir(exist_ok=True)
    
    def setup_client(self, cookie: Optional[str] = None, verbose: bool = False):
        """Setup the API client."""
        self.client = BatotwoGraphQLClient(session_cookie=cookie, verbose=verbose)
    
    def save_to_file(self, data: Any, filename: str):
        """Save data to JSON file."""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to: {filepath}")
    
    def cmd_introspect(self, args):
        """Introspect the GraphQL schema."""
        print("🔍 Introspecting GraphQL schema...")
        print("=" * 80)
        
        schema = self.client.introspect_schema()
        
        # Extract available queries
        query_type = schema.get('data', {}).get('__schema', {}).get('queryType', {})
        queries = query_type.get('fields', [])
        
        print(f"\n📋 Found {len(queries)} available queries:\n")
        
        for query in queries:
            name = query.get('name', 'N/A')
            desc = query.get('description', 'No description')
            args = query.get('args', [])
            
            print(f"  • {name}")
            if desc and desc != 'No description':
                print(f"    Description: {desc}")
            if args:
                print(f"    Arguments: {', '.join(arg['name'] for arg in args)}")
            print()
        
        # Save full schema
        self.save_to_file(schema, 'schema_introspection.json')
        
        return schema
    
    def cmd_get_chapters(self, args):
        """Get chapters for a comic."""
        print(f"📖 Fetching chapters for comic ID: {args.comic_id}")
        print("=" * 80)
        
        data = self.client.get_comic_chapters(args.comic_id, limit=args.limit)
        
        if data:
            chapters_list = data.get('get_content_chapterList', [])
            print(f"\n✅ Found {len(chapters_list)} chapters!")
            
            # Show first 5 chapters as preview
            if chapters_list:
                print(f"\nFirst {min(5, len(chapters_list))} chapters:")
                for i, chapter_node in enumerate(chapters_list[:5]):
                    chapter_data = chapter_node.get('data', {})
                    print(f"  {i+1}. {chapter_data.get('dname', 'N/A')}")
                    if chapter_data.get('title'):
                        print(f"     {chapter_data.get('title')}")
            
            self.save_to_file(data, f'comic_{args.comic_id}_chapters.json')
        else:
            print("⚠️  No data returned")
        
        return data
    
    def cmd_get_mylists(self, args):
        """Get user mylists for a comic."""
        print(f"📝 Fetching mylists for comic ID: {args.comic_id}")
        print("=" * 80)
        
        data = self.client.get_user_mylists(args.comic_id, limit=args.limit)
        
        if data:
            items = data.get('get_marking_mylistList', {}).get('items', [])
            print(f"\n✅ Found {len(items)} mylists:")
            
            for item in items:
                list_data = item.get('data', {})
                user_data = list_data.get('userNode', {}).get('data', {})
                
                print(f"\n  • {list_data.get('name', 'N/A')}")
                print(f"    By: {user_data.get('name', 'N/A')}")
                print(f"    Comics: {list_data.get('count_comicIds', 0)}")
                print(f"    Followers: {list_data.get('stat_followers', 0)}")
                print(f"    Public: {list_data.get('isPublic', False)}")
            
            self.save_to_file(data, f'comic_{args.comic_id}_mylists.json')
        else:
            print("⚠️  No data returned")
        
        return data
    
    def cmd_search(self, args):
        """Search for comics."""
        print(f"🔍 Searching for: {args.query}")
        print("=" * 80)
        
        data = self.client.search_comics(args.query)
        
        if data:
            print(f"\n✅ Response received!")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            self.save_to_file(data, f'search_{args.query.replace(" ", "_")}.json')
        else:
            print("⚠️  No data returned")
        
        return data
    
    def cmd_get_comic_info(self, args):
        """Get basic comic information."""
        print(f"📚 Fetching info for comic ID: {args.comic_id}")
        print("=" * 80)
        
        data = self.client.get_comic_basic_info(args.comic_id)
        
        if data:
            comic_node = data.get('get_content_comicNode', {})
            comic_data = comic_node.get('data', {})
            
            print(f"\n✅ Response received!")
            if comic_data:
                print(f"\nComic: {comic_data.get('name', 'N/A')}")
                print(f"ID: {comic_data.get('id', 'N/A')}")
                print(f"URL: https://batotwo.com{comic_data.get('urlPath', '')}")
            
            print(f"\nFull response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            self.save_to_file(data, f'comic_{args.comic_id}_info.json')
        else:
            print("⚠️  No data returned")
        
        return data
    
    def cmd_custom_query(self, args):
        """Execute a custom GraphQL query."""
        print("🔧 Executing custom query...")
        print("=" * 80)
        
        # Load query from file if provided
        if args.query_file:
            with open(args.query_file, 'r', encoding='utf-8') as f:
                query = f.read()
        else:
            query = args.query
        
        # Load variables from file if provided
        variables = None
        if args.variables_file:
            with open(args.variables_file, 'r', encoding='utf-8') as f:
                variables = json.load(f)
        elif args.variables:
            variables = json.loads(args.variables)
        
        data = self.client.custom_query(query, variables)
        
        print(f"\n✅ Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_to_file(data, f'custom_query_{timestamp}.json')
        
        return data
    
    def run(self):
        """Run the CLI."""
        parser = argparse.ArgumentParser(
            description='Batotwo GraphQL API Client - Explore and query batotwo.com API',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Get basic comic info (RECOMMENDED - use this to verify comic ID)
  python batotwo_client.py info 110100
  
  # Get chapters for a comic
  python batotwo_client.py chapters 110100
  
  # Get mylists for a comic
  python batotwo_client.py mylists 110100
  
  # Search for comics (may not work - search is not available in GraphQL API)
  python batotwo_client.py search "villainess stationery"
  
  # Execute custom query from file
  python batotwo_client.py custom --query-file my_query.graphql --variables-file vars.json
  
  # Enable verbose logging
  python batotwo_client.py chapters 110100 --verbose
  
  # NOTE: Introspection is disabled - use documented queries instead
            """
        )
        
        parser.add_argument('--cookie', help='Session cookie for authenticated requests')
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Introspect command
        introspect_parser = subparsers.add_parser('introspect', help='Introspect GraphQL schema')
        
        # Chapters command
        chapters_parser = subparsers.add_parser('chapters', help='Get chapters for a comic')
        chapters_parser.add_argument('comic_id', type=int, help='Comic ID')
        chapters_parser.add_argument('--limit', type=int, default=100, help='Max chapters to fetch')
        
        # Mylists command
        mylists_parser = subparsers.add_parser('mylists', help='Get mylists for a comic')
        mylists_parser.add_argument('comic_id', type=int, help='Comic ID')
        mylists_parser.add_argument('--limit', type=int, default=5, help='Max lists to fetch')
        
        # Search command
        search_parser = subparsers.add_parser('search', help='Search for comics')
        search_parser.add_argument('query', help='Search query')
        
        # Info command
        info_parser = subparsers.add_parser('info', help='Get basic comic info')
        info_parser.add_argument('comic_id', type=int, help='Comic ID')
        
        # Custom query command
        custom_parser = subparsers.add_parser('custom', help='Execute custom GraphQL query')
        custom_parser.add_argument('--query', help='GraphQL query string')
        custom_parser.add_argument('--query-file', help='Path to file containing GraphQL query')
        custom_parser.add_argument('--variables', help='JSON string of variables')
        custom_parser.add_argument('--variables-file', help='Path to JSON file with variables')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # Setup client
        self.setup_client(cookie=args.cookie, verbose=args.verbose)
        
        # Execute command
        commands = {
            'introspect': self.cmd_introspect,
            'chapters': self.cmd_get_chapters,
            'mylists': self.cmd_get_mylists,
            'search': self.cmd_search,
            'info': self.cmd_get_comic_info,
            'custom': self.cmd_custom_query,
        }
        
        try:
            command_func = commands.get(args.command)
            if command_func:
                command_func(args)
            else:
                print(f"❌ Unknown command: {args.command}")
                parser.print_help()
        except Exception as e:
            print(f"❌ Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point."""
    print("=" * 80)
    print("🚀 Batotwo GraphQL API Client")
    print("=" * 80)
    print()
    
    cli = BatotwoCLI()
    cli.run()


if __name__ == "__main__":
    main()
