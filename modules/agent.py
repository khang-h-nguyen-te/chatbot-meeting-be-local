from llama_index.core.tools import FunctionTool
from llama_index.agent.openai import OpenAIAgent
from llama_index.core import PromptTemplate
from llama_index.llms.openai import OpenAI
from modules.prompt_template import SYSTEM_TEMPLATE
import os
from modules.supabase_vectorstore import SupabaseVectorStore
from modules.history_module import HistoryModule  # now with pydantic ChatMessage
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer

SUPABASE_URL = os.environ.get("VITE_PUBLIC_BASE_URL")
SUPABASE_KEY = os.environ.get("VITE_VITE_APP_SUPABASE_ANON_KEY")

class AgentRag:
    def __init__(self, history_module: HistoryModule):
        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        self.qa_template = PromptTemplate(SYSTEM_TEMPLATE)
        self.gpt4_llm = OpenAI(model="gpt-4")
        self.vector_store = None
        self.vector_search_tool = None
        self.agent = None
        # self.history_module = history_module

    def setup_agent(self, auth: str):
        self.vector_store = SupabaseVectorStore(url=SUPABASE_URL, key=SUPABASE_KEY, auth=auth)
        self.vector_search_tool = FunctionTool.from_defaults(
            name="SupabaseVectorSearch",
            fn=self.vector_store.supabase_vector_search_tool,
            description="Search for relevant meetings. Returns documents formatted from a list of dictionaries."
        )
        memory = ChatMemoryBuffer.from_defaults(token_limit=20000)

        self.agent = OpenAIAgent.from_tools(
            tools=[self.vector_search_tool],
            llm=self.gpt4_llm,
            memory=memory,
            verbose=True
            , system_prompt=SYSTEM_TEMPLATE
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
