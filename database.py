import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("❌ MONGO_URI is not set in environment variables")

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    print("✅ Successfully connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB connection failed: {str(e)}")
    raise

# Define Database and Collections
db = client["chat_app"]  # Matches .env MONGO_URI
users_collection = db["users"]
chats_collection = db["chats"]