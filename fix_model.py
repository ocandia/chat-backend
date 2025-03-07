from sentence_transformers import SentenceTransformer, models
import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define the model directory relative to the script
model_dir = os.path.join(script_dir, "models", "all-MiniLM-L6-v2")

# Check if the directory exists
if not os.path.exists(model_dir):
    raise FileNotFoundError(f"Directory {model_dir} does not exist. Ensure model files are included in deployment.")

# Load the transformer model from the local directory
transformer = models.Transformer(model_dir)

# Load the pooling layer
pooling = models.Pooling(transformer.get_word_embedding_dimension(), pooling_mode="mean")

# Combine into a SentenceTransformer model
model = SentenceTransformer(modules=[transformer, pooling])

print("Model loaded successfully!")