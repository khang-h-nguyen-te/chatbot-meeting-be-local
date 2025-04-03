from llama_index.core.tools import FunctionTool
from llama_index.agent.openai import OpenAIAgent
from llama_index.core import PromptTemplate
from llama_index.llms.openai import OpenAI as OpenAI_LLAMA
from modules.prompt_template import SYSTEM_TEMPLATE
import os
import pandas as pd
from modules.supabase_vectorstore import SupabaseVectorStore
from modules.history_module import HistoryModule  # now with pydantic ChatMessage
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from pydantic import BaseModel, Field
from typing import Optional, Annotated
from openai import OpenAI

class OrganizationValidation(BaseModel):
    """Pydantic model for organization validation output"""
    organization_name: Optional[str] = Field(description="The exact organization name if found, None if not found")

SUPABASE_URL = os.environ.get("VITE_PUBLIC_BASE_URL")
SUPABASE_KEY = os.environ.get("VITE_VITE_APP_SUPABASE_ANON_KEY")

class AgentRag:
    def __init__(self, history_module: HistoryModule):
        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        self.qa_template = PromptTemplate(SYSTEM_TEMPLATE)
        self.gpt4_llm = OpenAI_LLAMA(model="gpt-4o")
        self.openai_client = OpenAI(api_key=self.OPENAI_API_KEY)
        self.vector_store = None
        self.vector_search_tool = None
        self.agent = None
        self.extract_current_date_tool = None
        self.organization_validation_tool = None
        self.organizations = self._load_organizations()
        # self.history_module = history_module

    def _load_organizations(self):
        """Load organizations from CSV file"""
        try:
            df = pd.read_csv('data/Organizations-All Organizations.csv')
            # Get unique organization names, excluding empty values
            organizations = df['Account'].dropna().unique().tolist()
            return organizations
        except Exception as e:
            print(f"Error loading organizations: {e}")
            return []

    def validate_organization(
        self,
        organization_input: str = Field(
            description="The organization name provided by the user, which needs to be validated against our database of organizations."
        )
    ) -> OrganizationValidation:
        """
        Validate and extract the correct organization name from the input.
        Returns a Pydantic model with the organization name.
        """
        if not self.organizations:
            return OrganizationValidation(organization_name=None)

        try:
            completion = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an organization validator. Given a list of valid organizations, find the exact match for the input.
                        Valid organizations: {', '.join(self.organizations)}
                        
                        Rules:
                        1. Return ONLY the exact organization name from the list
                        2. If no good match is found, return null
                        3. Do not add any explanation or additional text"""
                    },
                    {
                        "role": "user",
                        "content": f"Find the matching organization for: {organization_input}"
                    }
                ],
                response_format=OrganizationValidation
            )

            return completion.choices[0].message.parsed

        except Exception as e:
            return OrganizationValidation(organization_name=None)

    # Custom function to extract the current date/time
    def extract_current_date(self) -> str:
        """Returns the current date/time, allowing you to interpret requests like 'last week' or 'two months ago.'"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    

    def setup_agent(self, auth: str):
        self.vector_store = SupabaseVectorStore(url=SUPABASE_URL, key=SUPABASE_KEY, auth=auth)
        self.vector_search_tool = FunctionTool.from_defaults(
            name="SearchMeetings",
            fn=self.vector_store.supabase_vector_search_tool,
            description="Search for relevant meetings. Returns documents formatted from a list of dictionaries."
        )

        # Create a tool to extract current date/time
        self.extract_current_date_tool = FunctionTool.from_defaults(
            name="ExtractCurrentDate",
            fn=self.extract_current_date,
            description="Returns the current date/time, allowing you to interpret requests like 'last week' or 'two months ago.'"
        )

        # Create organization validation tool
        self.organization_validation_tool = FunctionTool.from_defaults(
            name="ValidateOrganization",
            fn=self.validate_organization,
            description="Validates and extracts the correct organization name from the input. Returns the exact organization name if found, or an error message if not found."
        )

        self.search_meetings_by_organization_tool = FunctionTool.from_defaults(
            name="SearchMeetingsByOrganization",
            fn=self.vector_store.search_meetings_by_organization_tool,
            description="Search for relevant meetings by organization. Returns documents formatted from a list of dictionaries."
        )

        memory = ChatMemoryBuffer.from_defaults(token_limit=100000)

        self.agent = OpenAIAgent.from_tools(
            tools=[
                self.vector_search_tool, 
                self.search_meetings_by_organization_tool, 
                self.extract_current_date_tool,
                self.organization_validation_tool
            ],
            llm=self.gpt4_llm,
            memory=memory,
            verbose=True,
            system_prompt=SYSTEM_TEMPLATE
        )

    def agent_query(self, query: str) -> str:
        # Add the user's query to the history
        # self.history_module.add_user_message(query)
        # # Retrieve the history (as a list of dictionaries) to pass as context
        # history_context = self.history_module.get_history()
        # Query the agent, passing the chat history
        response = self.agent.chat(query)
        print("Chat history:", self.agent.chat_history)
        # Add the agent's response to the history
        # self.history_module.add_agent_message(response)
        return response
