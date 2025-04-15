from typing import Dict, Any, Optional, List
from app.tools.base_tool import BaseTool
from app.services.embeddings import EmbeddingService
from app.vectorstore.supabase_vectorstore import SupabaseVectorStore
from datetime import datetime, date


class SearchMeetingsTool(BaseTool):
    """Tool for searching meetings in the database."""
    
    def __init__(self, vector_store: SupabaseVectorStore, embedding_service: EmbeddingService):
        super().__init__(
            name="SearchMeetings",
            description="Search for relevant meetings. Returns documents formatted from a list of dictionaries."
        )
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def __call__(self, user_input: str) -> str:
        """
        Search for meetings matching the user input.
        
        Args:
            user_input (str): Input from the user. Should include:
                            - Organization name if relevant
                            - Date range if mentioned
                            - Any specific search terms or criteria
            
        Returns:
            str: Formatted search results as a string.
            
        Example:
            >>> tool(user_input="Find meetings about budget planning in March")
            Returns meetings matching the semantic search for budget planning in March.
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
                user_input: str,
                organization_input: str) -> str:
        """
        Search for meetings by organization.
        
        Args:
            user_input (str): Input from the user. Should include:
                            - Date range if mentioned
                            - Any specific search terms or criteria
            organization_input (str): The exact organization name to filter meetings by.
                                    Should be validated first with ValidateOrganization.
            
        Returns:
            str: Formatted search results as a string.
            
        Example:
            >>> tool(user_input="Find budget meetings in Q1", organization_input="Acme Corp")
            Returns meetings for Acme Corp matching the semantic search for budget in Q1.
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


class RecentMeetingsSearchTool(BaseTool):
    """Tool for searching recent meetings within a date range."""
    
    def __init__(self, vector_store: SupabaseVectorStore):
        super().__init__(
            name="RecentMeetingsSearch",
            description="Search for meetings within a specific date range, defaulting to recent meetings from 2024-01-01 to today."
        )
        self.vector_store = vector_store
    
    def __call__(self,
                start_date_search: str = "2024-01-01",
                end_date_search: Optional[str] = None,
                limit_num_meetings: int = 10) -> str:
        """
        Search for meetings within a date range.
        
        Args:
            start_date_search (str): Start date for meeting search in YYYY-MM-DD format.
                                   Defaults to "2024-01-01".
            end_date_search (Optional[str]): End date for meeting search in YYYY-MM-DD format.
                                           Defaults to today's date if None.
            limit_num_meetings (int): Maximum number of meetings to return.
                                    Defaults to 10.
            
        Returns:
            str: Formatted search results as a string, containing meeting details sorted by date.
            
        Example:
            >>> tool(start_date_search="2024-03-01", end_date_search="2024-03-31", limit_num_meetings=5)
            Returns the 5 most recent meetings between March 1st and March 31st, 2024.
        """
        # Handle default end date
        if end_date_search is None:
            end_date_search = date.today().isoformat()
            
        user = self.vector_store.get_user()
        user_id = user.id
        
        try:
            response = (
                self.vector_store.client.table("meetings")
                .select("*")
                .eq("user_id", user_id)
                .gte("start", start_date_search)
                .lte("start", end_date_search)
                .limit(limit_num_meetings)
                .order("start", desc=True)
                .execute()
            )
            
            results = response.data
            
            if not results:
                return f"No meetings found between {start_date_search} and {end_date_search}."
            
            formatted_results = []
            for idx, meeting in enumerate(results, 1):
                doc_lines = [f"Meeting {idx}:"]
                # Format the meeting data, excluding internal fields
                display_fields = {
                    "Title": meeting.get("title", "No title"),
                    "Start Time": meeting.get("start", "No start time"),
                    "End Time": meeting.get("end", "No end time"),
                    "Organization": meeting.get("organization", "No organization"),
                    "Summary": meeting.get("summary", "No summary available")
                }
                for key, value in display_fields.items():
                    doc_lines.append(f"  {key}: {value}")
                formatted_results.append("\n".join(doc_lines))
            
            return "\n\n".join(formatted_results)
            
        except Exception as e:
            return f"Error searching meetings: {str(e)}" 