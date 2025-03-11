# modules/history_module.py
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str

class HistoryModule:
    def __init__(self, token_limit: int = 1500):
        # Use the ChatMemoryBuffer from llama_index
        from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=token_limit)
        # Initialize an internal list to store conversation history
        self.history = []

    def add_user_message(self, content: str):
        msg = ChatMessage(role="user", content=content)
        self.history.append(msg)
        # Also update the underlying memory store as a list of dicts
        self.memory.chat_store.set_messages(self.memory.chat_store_key, [m.dict() for m in self.history])

    def add_agent_message(self, content: str):
        msg = ChatMessage(role="assistant", content=content)
        self.history.append(msg)
        self.memory.chat_store.set_messages(self.memory.chat_store_key, [m.dict() for m in self.history])

    def get_history(self):
        # Return the history as a list of dicts so that it passes validation
        return [msg.dict() for msg in self.history]
