from passlib.context import CryptContext

# Initialize bcrypt hashing context
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to hash a password
def hash_password(password: str):
    return bcrypt_context.hash(password)

# Replace "password123" with the actual password you want to hash
raw_password = "password123"
hashed_password = hash_password(raw_password)

print(f"🔑 Hashed Password: {hashed_password}")