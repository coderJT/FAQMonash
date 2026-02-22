import os
import faiss
import json
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

model = SentenceTransformer("all-MiniLM-L6-v2")

def normalize(vectors):
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

def indexing():

    # Load cleaned data
    documents = []
    metadata = []

    # Chunking
    if not os.path.exists("data/silver"):
        print("No silver data found to index.")
        return

    # Helper to process a directory
    def process_dir(directory):
        if not os.path.exists(directory):
            return
        for filename in os.listdir(directory):
            if filename.endswith(".clean.txt"):
                with open(os.path.join(directory, filename), encoding="utf-8") as f:
                    text = f.read()

                # Chunking (500 chars per chunk with 100 char overlap)
                for i in range(0, len(text), 400):
                    chunk = text[i:i + 500]
                    if len(chunk.strip()) < 100:
                        continue
                    documents.append(chunk)
                    metadata.append({
                        "source": filename,
                        "offset": i,
                        "text": chunk
                    })

    process_dir("data/silver/cleaned")
    process_dir("data/silver/handbook")

    print(f"Embedding {len(documents)} chunks...")

    # BM25 Tokenization and Indexing
    print("Building BM25 Index...")
    tokenized_corpus = [doc.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    # Normalize the embeddings to use cosine similarity
    embeddings = normalize(model.encode(documents, show_progress_bar=True))

    # Store the embedding in FAISS
    dim = embeddings[0].shape[0]

    # Use inner product index for cosine similarity
    index = faiss.IndexFlatIP(dim)
    index.add(np.array(embeddings))

    # Save the index and metadata
    os.makedirs("data/gold/index", exist_ok=True)
    faiss.write_index(index, "data/gold/index/faiss_index")
    with open("data/gold/index/chunks_metadata.json", "w") as f:
        json.dump(metadata, f)
    with open("data/gold/index/bm25_index.pkl", "wb") as f:
        pickle.dump(bm25, f)

    print("FAISS and BM25 indices built successfully.")
