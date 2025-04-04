import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.config.supabase_config import get_supabase_client


class SupabaseVectorStore:
    """Interface to Supabase vector store for meeting data."""
    
    def __init__(self, url: str, key: str, auth: str = None):
        self.url = url
        self.key = key
        self.auth = auth
        self.client = self.create_supabase_client()
        self.logger = logging.getLogger(__name__)

    def create_supabase_client(self):
        """
        Create a Supabase client instance.
        If an auth header is provided, add it to the global headers so that row-level security (RLS)
        policies are applied using the user's context.
        """
        return get_supabase_client(self.auth)

    def get_user(self):
        """
        Retrieve the user from Supabase Auth.
        """
        token = self.auth.replace("Bearer ", "")
        user_response = self.client.auth.get_user(token)        
        return user_response.user

    def search_meetings(self, query_text: str, query_embedding: list, 
                        user_id: str, match_count: int = 20):
        """
        Perform a hybrid search on the content.
        
        Args:
            query_text: The text query.
            query_embedding: The embedding vector for the query.
            user_id: The ID of the current user.
            match_count: The maximum number of results to return.
            
        Returns:
            List of matching documents.
        """
        response = self.client.rpc("hybrid_search_meetings", {
            "query_text": query_text,
            "query_embedding": query_embedding,
            # "user_id_input": user_id,
            "match_count": match_count
        }).execute()
        return response.data
    
    def search_meetings_by_organization(self, query_text: str, query_embedding: list, 
                                        user_id: str, 
                                        organization_input: str, 
                                        match_count: int = 20):
        """
        Perform search by organization.
        
        Args:
            query_text: The text query.
            query_embedding: The embedding vector for the query.
            user_id: The ID of the current user.
            organization_input: The organization name to filter by.
            match_count: The maximum number of results to return.
            
        Returns:
            List of matching documents.
        """
        response = self.client.rpc("hybrid_search_meetings_organization", {
            "query_text": query_text,
            "query_embedding": query_embedding,
            "match_count": match_count,
            "organization_input": organization_input
            # "user_id_input": user_id,
        }).execute()
        return response.data 