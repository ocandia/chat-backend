import os
import ssl
from sentence_transformers import SentenceTransformer, models
import faiss
import pickle
from tqdm import tqdm
import urllib3

# Paths
INDEX_FILE = "faiss_index.bin"
METADATA_FILE = "metadata.pkl"
MODEL_PATH = "C:/Users/ocandia/OneDrive - DXC Production/Desktop/Python Project/backend/models/sentence-transformers_all-MiniLM-L6-v2"

# Load model
transformer = models.Transformer(MODEL_PATH)
pooling = models.Pooling(transformer.get_word_embedding_dimension(), pooling_mode="mean")
model = SentenceTransformer(modules=[transformer, pooling])

# Dummy data
documents = ["For God so loved the world - John 3:16", "The Lord is my shepherd - Psalm 23"]
metadata = [{"filename": "bible.txt"}, {"filename": "bible.txt"}]

# Function to chunk text
def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

# Index documents
def create_or_update_index(documents, metadata):
    all_chunks = []
    chunk_metadata = []

    if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
        index = faiss.read_index(INDEX_FILE)
        with open(METADATA_FILE, "rb") as f:
            data = pickle.load(f)
            existing_chunks = data["chunks"]
            existing_metadata = data["metadata"]
        tqdm.write(f"Loaded existing index with {len(existing_chunks)} chunks.")
    else:
        dimension = model.encode(["test"], convert_to_numpy=True).shape[1]
        index = faiss.IndexFlatL2(dimension)
        existing_chunks = []
        existing_metadata = []
        tqdm.write("Created new FAISS index.")

    for doc, meta in tqdm(zip(documents, metadata), total=len(documents), desc="Chunking documents"):
        chunks = chunk_text(doc)
        all_chunks.extend(chunks)
        chunk_metadata.extend([meta] * len(chunks))

    if all_chunks:
        tqdm.write("Generating embeddings...")
        embeddings = model.encode(all_chunks, convert_to_numpy=True)
        index.add(embeddings)

        all_chunks = existing_chunks + all_chunks
        all_metadata = existing_metadata + chunk_metadata

        faiss.write_index(index, INDEX_FILE)
        with open(METADATA_FILE, "wb") as f:
            pickle.dump({"chunks": all_chunks, "metadata": all_metadata}, f)
        tqdm.write(f"Saved index with {len(all_chunks)} chunks.")
    else:
        tqdm.write("No chunks to index.")

if __name__ == "__main__":
    create_or_update_index(documents, metadata)