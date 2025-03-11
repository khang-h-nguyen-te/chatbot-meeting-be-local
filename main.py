from typing import List
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
from modules.agent import AgentRag
from supabase import create_client, Client
import os
import logging
from llama_index.core.memory import (
    VectorMemory,
    SimpleComposableMemory,
    ChatMemoryBuffer,
)

# load_env()
import os
from dotenv import load_dotenv

load_dotenv()

# Import our HistoryModule
from modules.history_module import HistoryModule


app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)

# Supabase API URL and keys
SUPABASE_URL = os.environ.get("VITE_PUBLIC_BASE_URL")
SUPABASE_KEY = os.environ.get("VITE_VITE_APP_SUPABASE_ANON_KEY")

# Create Supabase clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create a global HistoryModule instance
chat_history_module = HistoryModule(token_limit=1500)
agent_initializer = AgentRag(history_module=chat_history_module)

# Create logger for the FastAPI app.
logger = logging.getLogger(__name__)

# Define the request payload schema.
class QueryRequest(BaseModel):
    query: str



class SignInRequest(BaseModel):
    email: str
    password: str

def create_response(message, status_code, error=False):
    return {"message": message, "status_code": status_code, "error": error}

def validate_params(params, required_params):
    for param in required_params:
        if param not in params:
            return False
    return True

@app.post("/authenticate/{command}")
async def authenticate(command: str, payload: SignInRequest):
    params = payload.dict()

    if command == 'signInWithPassword':
        if not validate_params(params, ['email', 'password']):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        try:
            response = supabase.auth.sign_in_with_password({
                'email': params['email'],
                'password': params['password']
            })
            agent_initializer.setup_agent( response.session.access_token)
            print("Agent Initialized: ", agent_initializer.agent.chat_history)
            return create_response(response, 200)
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(status_code=404, detail=f"Authentication type '{command}' not recognized")


# A helper function to process the query synchronously.
def process_query(query: str) -> str:

        # query = "What is excerpt of the post Harnessing Data for Business Transformation"
        response = agent_initializer.agent_query(query)

        return response
    

# Define a POST endpoint to receive user queries.
@app.post("/ask")
async def ask_query(payload: QueryRequest, request: Request):
    query = payload.query
    headers = request.headers  
    print(headers)
    # Offload the blocking agent call to a thread pool to avoid blocking the event loop.
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_query, query)
    if not result:
        raise HTTPException(status_code=500, detail=result)
    return {"response": result}

# ------------------------------------------------------------
# Main Function
# # ------------------------------------------------------------
# if __name__ == "__main__":
#     # Run the FastAPI app using uvicorn.
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)