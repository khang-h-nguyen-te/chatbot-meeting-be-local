from supabase import create_client, Client
from supabase.client import ClientOptions
from modules.helper import get_embedding
import logging
from datetime import datetime
from pydantic import BaseModel, Field

class SupabaseVectorStore:
    def __init__(self, url: str, key: str, auth: str = None):
        self.url = url
        self.key = key
        self.auth = auth
        self.client = self.create_supabase_client()
        self.logger = logging.getLogger(__name__)

    def create_supabase_client(self) -> Client:
        """
        Create a Supabase client instance.
        If an auth header is provided, add it to the global headers so that row-level security (RLS)
        policies are applied using the user's context.
        """
        if self.auth:
            print("Creating client with auth header")
            return create_client(self.url, self.key, options=ClientOptions(
                headers={"Authorization": self.auth},
                schema="dummy_schema",
            ))
        return create_client(self.url, self.key, options=ClientOptions(
                schema="dummy_schema",
            ))

    def get_user(self):
        """
        Retrieve the user from Supabase Auth.
        """
        token = self.auth.replace("Bearer ", "")
        user_response = self.client.auth.get_user(token)        

        return user_response.user

    def search_meetings(self, query_text: str, query_embedding: list, 
                                  user_id: str, 
                                  match_count: int = 20):
        """
        Perform a hybrid search on the content.
        """
        response = self.client.rpc("hybrid_search_meetings_v2", {
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
        Perform search by organization
        """
        response = self.client.rpc("hybrid_search_meetings_organization", {
            "query_text": query_text,
            "query_embedding": query_embedding,
            "match_count": match_count,
            "organization_input": organization_input
            # "user_id_input": user_id,
        }).execute()
        return response.data


    # Define the search tool function.
    def supabase_vector_search_tool(self, user_input: str = Field(
                description="Input from the user, please include the organization name in the user_input as well. If user mentions date range, please include the date range in the user_input as well."
            )) -> str:

        query_embedding = get_embedding(user_input)
        user = self.get_user()
        user_id = user.id
        print("User:", user)
        # Call the Supabase RPC method for hybrid search.
        results = self.search_meetings(user_input, query_embedding, user_id)
        
        # Process the returned list of documents (each a dict).
        if not results:
            return "No documents found."
        
        formatted_results = []
        for idx, doc in enumerate(results):
            doc_lines = [f"Document {idx+1}:"]
            # Iterate over dictionary items; adjust keys based on your actual document schema.
            for key, value in doc.items():
                doc_lines.append(f"  {key}: {value}")
                # print(f"  {key}: {value}")
            formatted_results.append("\n".join(doc_lines))
        
        return "\n\n".join(formatted_results)
    
    def search_meetings_by_organization_tool(self, user_input: str = Field(
                description="Input from the user, please include the organization name in the user_input as well. If user mentions date range, please include the date range in the user_input as well."
            ),
            organization_input: str = Field(
                description="The exact organization name to filter meetings by (should be validated first with ValidateOrganization)"
            )) -> str:
        query_embedding = get_embedding(user_input)
        user = self.get_user()
        user_id = user.id
        print("User:", user)
        # Call the Supabase RPC method for hybrid search.
        results = self.search_meetings_by_organization(user_input, query_embedding, user_id, organization_input)

        # Process the returned list of documents (each a dict).
        if not results:
            return "No documents found."
        
        formatted_results = []
        for idx, doc in enumerate(results):
            doc_lines = [f"Document {idx+1}:"]
            # Iterate over dictionary items; adjust keys based on your actual document schema.
            for key, value in doc.items():
                doc_lines.append(f"  {key}: {value}")
                # print(f"  {key}: {value}")
            formatted_results.append("\n".join(doc_lines))
        
        return "\n\n".join(formatted_results)

# write if run this function as main, it will run example
if __name__ == "__main__":
    # Example usage:

    # header_auth = f"Bearer {ACCESS_TOKEN}"
    # vector_store = SupabaseVectorStore(SUPABASE_URL, SUPABASE_KEY, header_auth)

    # # Get user
    # user = vector_store.get_user()
    # print("User:", user)

    # # Perform hybrid search
    # query = "Why Rural Entrepreneurs are the Backbone of America"
    # embed_query = get_embedding(query)
    # response = vector_store.search_meetings(query, embed_query)

    # response
    pass
