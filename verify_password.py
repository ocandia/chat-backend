from passlib.context import CryptContext

# Initialize bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Stored hashed password from MongoDB
stored_hashed_password = "$2b$12$q5IgBkuCLs/Dz8bOCEVzkee9w5j5fj4ju/752pX9826nhavlHe08G"

# Test password
test_password = "password123"

# Verify password
is_valid = pwd_context.verify(test_password, stored_hashed_password)
print("✅ Password matches!" if is_valid else "❌ Password does NOT match!")