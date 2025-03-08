# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for pymongo, faiss, and cryptography
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code and RAG components
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy the application code and RAG components
COPY main.py .
COPY database.py .
COPY auth.py .
COPY .env .
COPY faiss_index.bin .
COPY metadata.pkl .
COPY models/ ./models/
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Expose the port the app runs on
EXPOSE 8000
