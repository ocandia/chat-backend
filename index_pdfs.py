import os
import PyPDF2
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from tqdm import tqdm

# Paths
PDF_DIR = "pdfs"
INDEX_FILE = "faiss_index.bin"
METADATA_FILE = "metadata.pkl"
MODEL_PATH = "C:/Users/ocandia/OneDrive - DXC Production/Desktop/Python Project/backend/models/all-MiniLM-L6-v2"

# Load sentence transformer model from local path
model = SentenceTransformer(MODEL_PATH)

# Function to extract text from PDFs
def extract_text_from_pdfs(pdf_dir, existing_files=None):
    documents = []
    metadata = []
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    total_pdfs = len(pdf_files)

    if total_pdfs == 0:
        tqdm.write("No PDFs found in directory.")
        return documents, metadata

    # Filter out already processed files if provided
    if existing_files:
        pdf_files = [f for f in pdf_files if f not in existing_files]
        if not pdf_files:
            tqdm.write("No new PDFs to process.")
            return documents, metadata

    # Progress bar for PDF extraction
    for filename in tqdm(pdf_files, desc="Extracting text from new PDFs"):
        pdf_path = os.path.join(pdf_dir, filename)
        try:
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                documents.append(text)
                metadata.append({"filename": filename})
                tqdm.write(f"Extracted text from {filename} ({len(reader.pages)} pages)")
        except Exception as e:
            tqdm.write(f"Error processing {filename}: {str(e)}")
    
    return documents, metadata

# Function to chunk text
def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

# Index documents incrementally
def create_or_update_index(documents, metadata):
    all_chunks = []
    chunk_metadata = []

    # Load existing index and metadata if they exist
    if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
        index = faiss.read_index(INDEX_FILE)
        with open(METADATA_FILE, "rb") as f:
            data = pickle.load(f)
            existing_chunks = data["chunks"]
            existing_metadata = data["metadata"]
        tqdm.write(f"Loaded existing index with {len(existing_chunks)} chunks.")
    else:
        # Create new index if none exists
        dimension = model.encode(["test"], convert_to_numpy=True).shape[1]  # Get embedding dimension
        index = faiss.IndexFlatL2(dimension)
        existing_chunks = []
        existing_metadata = []
        tqdm.write("Created new FAISS index.")

    # Get list of already processed filenames
    existing_files = {meta["filename"] for meta in existing_metadata}

    # Extract text from new PDFs only
    new_documents, new_metadata = extract_text_from_pdfs(PDF_DIR, existing_files)

    if not new_documents:
        return  # No new PDFs to process

    # Chunk new documents
    for doc, meta in tqdm(zip(new_documents, new_metadata), total=len(new_documents), desc="Chunking new documents"):
        chunks = chunk_text(doc)
        all_chunks.extend(chunks)
        chunk_metadata.extend([meta] * len(chunks))

    if all_chunks:
        # Generate embeddings for new chunks
        tqdm.write("Generating embeddings for new chunks...")
        new_embeddings = model.encode(all_chunks, convert_to_numpy=True)
        index.add(new_embeddings)
        
        # Combine existing and new data
        all_chunks = existing_chunks + all_chunks
        all_metadata = existing_metadata + chunk_metadata
        
        # Save updated index and metadata
        faiss.write_index(index, INDEX_FILE)
        with open(METADATA_FILE, "wb") as f:
            pickle.dump({"chunks": all_chunks, "metadata": all_metadata}, f)
        tqdm.write(f"Updated index with {len(all_chunks)} total chunks ({len(new_documents)} new PDFs).")
    else:
        tqdm.write("No new chunks to index.")

if __name__ == "__main__":
    create_or_update_index([], [])  # Initial call with empty args; logic handles loading