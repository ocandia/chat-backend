import os
from sentence_transformers import SentenceTransformer

MODEL_PATH = "C:/Users/ocandia/OneDrive - DXC Production/Desktop/Python Project/backend/models/all-MiniLM-L6-v2"

print(f"Model path exists: {os.path.exists(MODEL_PATH)}")
print(f"Config exists: {os.path.exists(os.path.join(MODEL_PATH, 'config.json'))}")
print(f"Model file exists: {os.path.exists(os.path.join(MODEL_PATH, 'pytorch_model.bin'))}")

try:
    model = SentenceTransformer(MODEL_PATH)
    print("Model loaded successfully!")
    embedding = model.encode("This is a test sentence.")
    print(f"Embedding shape: {embedding.shape}")
except Exception as e:
    print(f"Error loading model: {str(e)}")