from typing import List
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Import from our application structure
from app.agent.agent_rag import AgentRag
from app.models.request_models import QueryRequest, SignInRequest
from app.utils.response_utils import create_response, validate_params
from app.utils.crypto_utils import encrypt_password, decrypt_password
from app.history.history_module import HistoryModule
from app.config.supabase_config import get_supabase_client
from app.config.env_config import config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="Meeting Chatbot API",
    description="API for interacting with the Meeting Chatbot",
    version="1.0.0"
)
executor = ThreadPoolExecutor(max_workers=4)

# Create Supabase client
supabase = get_supabase_client()

# Create a global HistoryModule instance
chat_history_module = HistoryModule()  # Now uses config for token limit
agent_initializer = AgentRag(history_module=chat_history_module)

# Create logger for the FastAPI app
logger = logging.getLogger(__name__)

@app.post("/authenticate/{command}")
async def authenticate(command: str, payload: SignInRequest):
    """
    Authenticate a user and initialize the agent.
    
    Args:
        command: The authentication command to execute
        payload: The authentication request payload
    
    Returns:
        Authentication response with token
    """
    params = payload.dict()

    if command == 'signInWithPassword':
        if not validate_params(params, ['email', 'password']):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        try:
            # Decrypt password if it's encrypted
            try:
                password = decrypt_password(params['password'])
            except Exception:
                # If decryption fails, use the password as is
                password = params['password']
                
            response = supabase.auth.sign_in_with_password({
                'email': params['email'],
                'password': password
            })
            agent_initializer.setup_agent(response.session.access_token)
            logger.info(f"Agent initialized for user: {params['email']}")
            return create_response(response, 200)
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    elif command == 'signUpWithPassword':
        if not validate_params(params, ['email', 'password', 'display_name']):
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        try:
            # Decrypt password if it's encrypted
            try:
                password = decrypt_password(params['password'])
            except Exception:
                # If decryption fails, use the password as is
                password = params['password']
                
            response = supabase.auth.sign_up({
                'email': params['email'],
                'password': password,
            })

            ## Not yet implemented set profile data

            logger.info(f"User account created: {params['email']}")
            return create_response(response, 200)
        
        except Exception as e:
            logger.error(f"Sign up error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(status_code=404, detail=f"Authentication type '{command}' not recognized")

# A helper function to process the query synchronously
def process_query(query: str) -> str:
    """
    Process a user query using the agent.
    
    Args:
        query: The user's question
    
    Returns:
        The agent's response
    """
    response = agent_initializer.agent_query(query)
    return response
    
# Define a POST endpoint to receive user queries
@app.post("/ask")
async def ask_query(payload: QueryRequest, request: Request):
    """
    Process a user question and return the agent's response.
    
    Args:
        payload: The query request containing the user question
        request: The FastAPI request object
    
    Returns:
        The agent's response
    """
    query = payload.query
    headers = request.headers  
    logger.debug(f"Processing query: {query}")
    
    # Offload the blocking agent call to a thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_query, query)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to process query")
    
    return {"response": result}

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint to verify the API is running."""
    return {"status": "ok"}

# ------------------------------------------------------------
# Main Function
# ------------------------------------------------------------
if __name__ == "__main__":
    # Run the FastAPI app using uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 