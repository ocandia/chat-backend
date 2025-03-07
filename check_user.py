from pymongo import MongoClient
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["GodChatbot"]
users_collection = db["users"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

email = "user123@example.com"  # Updated to email
user = users_collection.find_one({"email": email})

if user:
    stored_hashed_password = user["hashed_password"]
    print(f"🔹 Stored Hashed Password for {email}: {stored_hashed_password}")

    test_password = "password123"
    if pwd_context.verify(test_password, stored_hashed_password):
        print("✅ Password verification successful!")
    else:
        print("❌ Password does NOT match!")
else:
    print(f"❌ User '{email}' not found in database.")