import os
import certifi
# Use certifi's CA bundle for SSL verification
os.environ['SSL_CERT_FILE'] = certifi.where()

# OPTIONAL: For development only. DISABLE SSL VERIFICATION (not recommended for production)
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context

from datetime import timedelta
import json
import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from database import chats_collection, users_collection
from auth import create_access_token, get_current_user, verify_password
from starlette.responses import StreamingResponse, JSONResponse
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer
from passlib.context import CryptContext
import faiss
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str

class UserRequest(BaseModel):
    email: str
    password: str

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

app = FastAPI()

# Updated CORS Middleware to include all Vercel frontend domains
origins = [
    "http://localhost:3000",
    "https://god-chatbot-frontend-dtedlz78j-oscar-candias-projects.vercel.app",
    "https://god-chatbot-frontend-8c999sdcw-oscar-candias-projects.vercel.app",
    "https://god-chatbot-frontend-pa2vbm9iy-oscar-candias-projects.vercel.app",
    "https://god-chatbot-frontend-git-master-oscar-candias-projects.vercel.app",
    "https://god-chatbot-frontend-e8hqtxicq-oscar-candias-projects.vercel.app"  # New domain added
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware successfully configured with origins: %s", origins)

# Load RAG components
INDEX_FILE = "faiss_index.bin"
METADATA_FILE = "metadata.pkl"
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Handle missing FAISS files gracefully
index = None
chunks = []
chunk_metadata = []
if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
    try:
        index = faiss.read_index(INDEX_FILE)
        with open(METADATA_FILE, "rb") as f:
            rag_data = pickle.load(f)
        chunks = rag_data["chunks"]
        chunk_metadata = rag_data["metadata"]
        logger.info("FAISS index and metadata loaded successfully")
    except Exception as e:
        logger.error(f"Error loading FAISS files: {str(e)}")
else:
    logger.warning("FAISS index or metadata not found. RAG disabled.")

def retrieve_chunks(query, k=3):
    if index is None:
        logger.info("RAG disabled, returning empty chunks")
        return [], []
    query_embedding = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, k)
    retrieved_chunks = [chunks[i] for i in indices[0]]
    retrieved_metadata = [chunk_metadata[i] for i in indices[0]]
    return retrieved_chunks, retrieved_metadata

@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "Front end is running: God AI is running"}

@app.post("/users/")
async def create_user(user: UserRequest):
    logger.info(f"Creating user with email: {user.email}")
    if users_collection.find_one({"email": user.email}):
        logger.error(f"Email already registered: {user.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = pwd_context.hash(user.password)
    user_data = {"email": user.email, "hashed_password": hashed_password}
    users_collection.insert_one(user_data)
    logger.info(f"User created successfully: {user.email}")
    return {"message": "User created successfully"}

@app.get("/check-auth")
def check_auth(current_user: dict = Depends(get_current_user)):
    logger.info(f"Authenticated user: {current_user}")
    return {"status": "authenticated", "user": current_user["email"]}

client = AsyncOpenAI(api_key=openai_api_key)

async def stream_response(messages, chat_id, retrieved_metadata):
    full_response = ""
    try:
        metadata_json = json.dumps({"sources": [meta["filename"] for meta in retrieved_metadata]})
        yield f"data: {metadata_json}\n\n"
        
        user_input = messages[-1]["content"].lower()
        response_content = ""
        if "prayer" in user_input:
            response_content = (
                "Heavenly Father, I come before You with a humble heart, seeking Your peace as we discuss faith. "
                "Bless those who seek You, as John 3:16 reminds us of Your love, and guide us with Your wisdom. "
                "Amen."
            )
        elif "what is prayer" in user_input:
            response_content = (
                "Prayer is a heartfelt conversation with God, as taught in Philippians 4:6. "
                "It’s a way to seek His guidance and express gratitude."
            )
        else:
            # Default to OpenAI for other queries
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True
            )
            async for chunk in response:
                if hasattr(chunk, "choices") and chunk.choices:
                    text = chunk.choices[0].delta.content
                    if text:
                        full_response += text
                        json_data = json.dumps({"text": text})
                        yield f"data: {json_data}\n\n"
                        await asyncio.sleep(0.01)
            response_content = full_response

        # Stream custom or OpenAI response
        if not response_content:
            response_content = "I am here to provide wisdom and truth, drawn from sacred texts (e.g., Matthew 6:33)."
        for chunk in response_content.split():
            full_response += chunk + " "
            json_data = json.dumps({"text": chunk})
            yield f"data: {json_data}\n\n"
            await asyncio.sleep(0.01)
        yield f"data: {json.dumps({'done': True})}\n\n"
        chats_collection.update_one(
            {"_id": chat_id},
            {"$set": {"bot_reply": full_response.strip()}}
        )
    except Exception as e:
        error_msg = f"OpenAI Streaming Error: {str(e)}"
        logger.error(error_msg)
        yield f"data: {json.dumps({'error': error_msg})}\n\n"

@app.post("/chat")
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_input = request.message.strip()
    if not user_input:
        logger.error("Message cannot be empty")
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        relevant_chunks, metadata = retrieve_chunks(user_input)
        context = "\n".join([f"From {meta['filename']}:\n{chunk}" for chunk, meta in zip(relevant_chunks, metadata)])

        system_message = {
            "role": "system",
            "content": (
                "You are a devout companion who speaks of God with intimate knowledge and reverence, never claiming to be God. "
                "Keep replies brief and compassionate, guiding all—believers, non-believers, atheists, and agnostics—with a focus on truth from God’s sacred words. "
                "Draw wisdom from the provided context from religious texts, referencing them naturally (e.g., 'As Jesus taught in John 16:33...'). "
                f"Context from documents:\n{context}\n"
                "Speak as one who has witnessed God’s truth, using a humble, wise tone (e.g., 'I’ve seen His peace transform lives’). "
                "Offer comfort, encourage introspection with gentle questions, and adapt to the user’s emotions as if in a sacred conversation. "
                "Avoid theological debates; guide with clarity and warmth, rooted in scriptural truth. "
                "Relate to modern events when relevant, showing God’s presence today. "
                "Let the user feel they’re speaking with a trusted friend who knows God deeply."
            )
        }
        user_message = {"role": "user", "content": user_input}

        messages = [system_message, user_message]

        chat_data = {
            "user_id": current_user["email"],
            "user_message": user_input,
            "bot_reply": "Streaming..."
        }
        result = chats_collection.insert_one(chat_data)
        chat_id = result.inserted_id

        return StreamingResponse(
            stream_response(messages, chat_id, metadata),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Chat Endpoint Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/pray")
async def pray(current_user: dict = Depends(get_current_user)):
    logger.info(f"Pray request from user: {current_user['email']}")
    metadata = [{"filename": "bible.txt"}]  # Default metadata
    response_content = (
        "Heavenly Father, I come before You with a humble heart, seeking Your peace as we discuss faith. "
        "Bless those who seek You, as John 3:16 reminds us of Your love, and guide us with Your wisdom. "
        "Amen."
    )
    chat_data = {
        "user_id": current_user["email"],
        "user_message": "Pray request",
        "bot_reply": response_content
    }
    result = chats_collection.insert_one(chat_data)
    chat_id = result.inserted_id

    async def pray_stream():
        yield f"data: {json.dumps({'sources': ['bible.txt']})}\n\n"
        for chunk in response_content.split():
            json_data = json.dumps({"text": chunk})
            yield f"data: {json_data}\n\n"
            await asyncio.sleep(0.01)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(pray_stream(), media_type="text/event-stream")

@app.get("/chat-history")
def get_chat_history(current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching chat history for user: {current_user['email']}")
    chats = list(chats_collection.find({"user_id": current_user["email"]}, {"_id": 0}))
    return {"history": chats}

@app.options("/token")
async def options_token(req: Request):
    origin = req.headers.get("origin")
    logger.info(f"Handling OPTIONS request from origin: {origin}")
    if not origin:
        logger.warning("No origin header found in OPTIONS request")
        origin = "*"  # Fallback for testing
    # Define allowed origins
    allowed_origins = [
        "http://localhost:3000",
        "https://god-chatbot-frontend-dtedlz78j-oscar-candias-projects.vercel.app",
        "https://god-chatbot-frontend-8c999sdcw-oscar-candias-projects.vercel.app",
        "https://god-chatbot-frontend-pa2vbm9iy-oscar-candias-projects.vercel.app",
        "https://god-chatbot-frontend-git-master-oscar-candias-projects.vercel.app",
        "https://god-chatbot-frontend-e8hqtxicq-oscar-candias-projects.vercel.app"
    ]
    response_origin = origin if origin in allowed_origins else "*"
    return JSONResponse(
        content={"message": "Preflight request handled"},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": response_origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
            "Access-Control-Allow-Credentials": "true"
        }
    )

@app.post("/token")
async def login(request: TokenRequest, req: Request):
    logger.info(f"Received login request from origin: {req.headers.get('origin')}")
    logger.info(f"Request headers: {dict(req.headers)}")
    user = users_collection.find_one({"email": request.email})
    if not user:
        logger.error(f"User not found: {request.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    logger.info(f"Found user: {user['email']}, Hash: {user['hashed_password']}")
    password_verified = verify_password(request.password, user["hashed_password"])
    logger.info(f"Password verification result: {password_verified}")
    if not password_verified:
        logger.error(f"Password verification failed for {request.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user["email"]}, expires_delta=timedelta(hours=1))
    logger.info(f"Login success: {request.email}, Token: {token}")
    response = {"access_token": token, "token_type": "bearer"}
    logger.info(f"Returning response with headers: {response}")
    return JSONResponse(
        content=response,
        headers={"Access-Control-Allow-Origin": req.headers.get("origin", "*")}
    )
