from passlib.context import CryptContext
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["chat_app"]  # Matches .env
users_collection = db["users"]

# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

plain_password = "password123"
email = "user123@example.com"

hashed_password = pwd_context.hash(plain_password)

users_collection.update_one(
    {"email": email},
    {"$set": {"email": email, "hashed_password": hashed_password}},
    upsert=True
)

print(f"🔑 Hashed Password: {hashed_password}")
print(f"✅ User '{email}' added/updated in MongoDB")