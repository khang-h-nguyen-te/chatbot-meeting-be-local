from typing import Dict, Any, Optional, List
from pydantic import Field

from app.tools.base_tool import BaseTool
from app.services.embeddings import EmbeddingService
from app.vectorstore.supabase_vectorstore import SupabaseVectorStore


class SearchMeetingsTool(BaseTool):
    """Tool for searching meetings in the database."""
    
    def __init__(self, vector_store: SupabaseVectorStore, embedding_service: EmbeddingService):
        super().__init__(
            name="SearchMeetings",
            description="Search for relevant meetings. Returns documents formatted from a list of dictionaries."
        )
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def __call__(self, user_input: str = Field(
        description="Input from the user, please include the organization name in the user_input as well. "
                    "If user mentions date range, please include the date range in the user_input as well."
    )) -> str:
        """
        Search for meetings matching the user input.
        
        Args:
            user_input: The user's query string.
            
        Returns:
            Formatted search results as a string.
        """
        query_embedding = self.embedding_service.get_embedding(user_input)
        user = self.vector_store.get_user()
        user_id = user.id
        
        # Call the Supabase RPC method for hybrid search
        results = self.vector_store.search_meetings(user_input, query_embedding, user_id)
        
        # Process the returned list of documents
        if not results:
            return "No documents found."
        
        formatted_results = []
        for idx, doc in enumerate(results):
            doc_lines = [f"Document {idx+1}:"]
            for key, value in doc.items():
                doc_lines.append(f"  {key}: {value}")
            formatted_results.append("\n".join(doc_lines))
        
        return "\n\n".join(formatted_results)


class SearchMeetingsByOrganizationTool(BaseTool):
    """Tool for searching meetings filtered by organization."""
    
    def __init__(self, vector_store: SupabaseVectorStore, embedding_service: EmbeddingService):
        super().__init__(
            name="SearchMeetingsByOrganization",
            description="Search for relevant meetings by organization. Returns documents formatted from a list of dictionaries."
        )
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def __call__(self, 
                user_input: str = Field(
                    description="Input from the user, please include the organization name in the user_input as well. "
                                "If user mentions date range, please include the date range in the user_input as well."
                ),
                organization_input: str = Field(
                    description="The exact organization name to filter meetings by (should be validated first with ValidateOrganization)"
                )) -> str:
        """
        Search for meetings by organization.
        
        Args:
            user_input: The user's query string.
            organization_input: The organization name to filter by.
            
        Returns:
            Formatted search results as a string.
        """
        query_embedding = self.embedding_service.get_embedding(user_input)
        user = self.vector_store.get_user()
        user_id = user.id
        
        # Call the Supabase RPC method for organization-specific search
        results = self.vector_store.search_meetings_by_organization(
            user_input, query_embedding, user_id, organization_input
        )
        
        # Process the returned list of documents
        if not results:
            return "No documents found."
        
        formatted_results = []
        for idx, doc in enumerate(results):
            doc_lines = [f"Document {idx+1}:"]
            for key, value in doc.items():
                doc_lines.append(f"  {key}: {value}")
            formatted_results.append("\n".join(doc_lines))
        
        return "\n\n".join(formatted_results) 