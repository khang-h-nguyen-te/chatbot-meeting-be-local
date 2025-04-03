from typing import Dict, List, Optional
import os
import pandas as pd

from llama_index.llms.openai import OpenAI as OpenAI_LLAMA
from llama_index.agent.openai import OpenAIAgent
from llama_index.core import PromptTemplate
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool

from app.history.history_module import HistoryModule
from app.templates.prompt_templates import SYSTEM_TEMPLATE
from app.services.embeddings import EmbeddingService
from app.vectorstore.supabase_vectorstore import SupabaseVectorStore
from app.tools.date.date_tool import DateExtractionTool
from app.tools.organization.organization_tool import OrganizationValidationTool
from app.tools.search.search_tools import SearchMeetingsTool, SearchMeetingsByOrganizationTool
from app.config.env_config import config


class AgentRag:
    """
    RAG (Retrieval-Augmented Generation) agent for meeting queries.
    This agent integrates multiple tools and uses a vector store for document retrieval.
    """
    
    def __init__(self, history_module: HistoryModule):
        self.qa_template = PromptTemplate(SYSTEM_TEMPLATE)
        self.gpt4_llm = OpenAI_LLAMA(model=config.llm_model)
        self.vector_store = None
        self.agent = None
        self.embedding_service = EmbeddingService()
        self._load_organizations()
    
    def _load_organizations(self):
        """Load organizations from CSV file."""
        try:
            df = pd.read_csv('data/Organizations-All Organizations.csv')
            # Get unique organization names, excluding empty values
            self.organizations = df['Account'].dropna().unique().tolist()
        except Exception as e:
            print(f"Error loading organizations: {e}")
            self.organizations = [
                '5 Elements Brewery', 'Absher Construction', 'Accel Scaling',
                'AFG VIETNAM', 'AI-Assisted Coaching and Mentoring Tools', 'Aim up Vietnam', 
                'Alchemy', 'Alchemy Asia', 'Aquila', 'Avision Young', 'Avison Young', 
                'Brooks AI', 'Brooks.ai', 'Caram Gems', 
                'CASH Financial Services Group Limited', 'CGM', 'Chikita Restaurant', 
                'Common Metal', 'Compass Events Pte Ltd', 'Dao Nguyen Legal', 
                'Delight Labs PR', 'Design X', 'DFDL Lawfirm', 'Digital Trends Media Group', 
                'Doxa Talent', 'Edge8', 'Eric Enriquez', 'Fairview International School', 
                'GRADY GOLF', 'Grit Volleyball', 'Hermes Landscaping', 'Hit Lights LED', 
                'HITlights', 'IFP Partners Limited', 'Ikaria Group', 'Invest Migrate', 
                'IPPG Vietnam', 'Kation', 'Kyungbang Vietnam', 'MomentsWare', 
                'On Target by Abound Health', 'Oseran Hahn', 'Pho 24', 'Power of 3', 
                'Qualicious', 'Rock Hill Asia', 'Single Grain', 'Socket', 'Sound Acoustic', 
                'Studio 3', 'Studio3eight', 'Surrogate First', 'TAL Apparel', 'Tartine Saigon', 
                'The Icarus Institute', 'The Problem Solver', 'Unlock Venture Partners', 
                'Veracity ', 'Vespa Adventures', 'Vietrose Internatinal', 
                'Vietrose International Vietnam', 'Vulcan Lab', 'Wareease', 'West Coast Dental', 
                'Westcoast International Dental Clinic', 'Wink Hotel Group', 
                'Work Healthy Australia', 'YPO Gold Forum', 'Grady Golf'
            ]
    
    def setup_agent(self, auth: str):
        """
        Set up the agent with necessary tools and configurations.
        
        Args:
            auth: Authentication token for Supabase.
        """
        # Initialize vector store
        self.vector_store = SupabaseVectorStore(
            url=config.supabase_url,
            key=config.supabase_anon_key,
            auth=auth
        )
        
        # Create tools
        date_tool = DateExtractionTool()
        organization_tool = OrganizationValidationTool(organizations=self.organizations)
        search_tool = SearchMeetingsTool(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service
        )
        search_by_org_tool = SearchMeetingsByOrganizationTool(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service
        )
        
        # Create llama_index FunctionTool objects
        search_function_tool = FunctionTool.from_defaults(
            name=search_tool.name,
            description=search_tool.description,
            fn=search_tool.__call__
        )
        
        search_by_org_function_tool = FunctionTool.from_defaults(
            name=search_by_org_tool.name,
            description=search_by_org_tool.description,
            fn=search_by_org_tool.__call__
        )
        
        date_function_tool = FunctionTool.from_defaults(
            name=date_tool.name,
            description=date_tool.description,
            fn=date_tool.__call__
        )
        
        organization_function_tool = FunctionTool.from_defaults(
            name=organization_tool.name,
            description=organization_tool.description,
            fn=organization_tool.__call__
        )
        
        # Set up memory with configurable token limit
        memory = ChatMemoryBuffer.from_defaults(token_limit=config.memory_token_limit)
        
        # Initialize agent with tools
        self.agent = OpenAIAgent.from_tools(
            tools=[
                search_function_tool,
                search_by_org_function_tool,
                date_function_tool,
                organization_function_tool
            ],
            llm=self.gpt4_llm,
            memory=memory,
            verbose=True,
            system_prompt=SYSTEM_TEMPLATE
        )
    
    def agent_query(self, query: str) -> str:
        """
        Query the agent with a user question.
        
        Args:
            query: The user's question.
            
        Returns:
            The agent's response.
        """
        response = self.agent.chat(query)
        print("Chat history:", self.agent.chat_history)
        return response 