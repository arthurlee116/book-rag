import os
import requests
from sentence_transformers import SentenceTransformer

# Explicitly set proxy to what user provided
# os.environ["https_proxy"] = "http://127.0.0.1:10808"
# os.environ["http_proxy"] = "http://127.0.0.1:10808"

print("Testing connection to huggingface.co...")
try:
    resp = requests.head("https://huggingface.co", timeout=5)
    print(f"Status: {resp.status_code}")
except Exception as e:
    print(f"Direct request failed: {e}")

print("\nTesting model download...")
try:
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    print("Model downloaded successfully!")
except Exception as e:
    print(f"Model download failed: {e}")
