import os
import faiss
import json
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

def rewrite_query(question: str, chat_history: list, model) -> str:
    """Rewrite query using chat history context"""
    if not chat_history:
        return question
        
    memory_str = "\n".join([f"{msg['role']}: {msg['text']}" for msg in chat_history[-4:]]) # Last 2 turns
    prompt = f"""Given the following conversation history and a follow up question, rephrase the follow up question to be a standalone question.
    Chat History:
    {memory_str}
    
    Follow Up Input: {question}
    Standalone question:"""
    
    response = model.generate_content(prompt)
    if response and response.text:
        return response.text.strip()
    return question

def reciprocal_rank_fusion(faiss_ranks, bm25_ranks, k=60):
    """Combine ranks from multiple retrievers using RRF"""
    scores = {}
    
    for rank, doc_idx in enumerate(faiss_ranks):
        scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 / (k + rank + 1)
        
    for rank, doc_idx in enumerate(bm25_ranks):
        scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 / (k + rank + 1)
        
    sorted_indices = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [idx for idx, score in sorted_indices]

def evaluate(question: str, chat_history: list = None):
    chat_history = chat_history or []
    
    # Configure Gemini API key
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise EnvironmentError("Please set your Google API key in the environment as GOOGLE_API_KEY")
    genai.configure(api_key=GOOGLE_API_KEY)

    # Load Gemini model
    rag_model = genai.GenerativeModel("gemini-2.5-flash")

    # Load embedding model
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    # Load indices and metadata
    index = faiss.read_index("data/gold/index/faiss_index")
    with open("data/gold/index/chunks_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    with open("data/gold/index/bm25_index.pkl", "rb") as f:
        bm25 = pickle.load(f)

    # Normalize helper
    def normalize(vectors):
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    # 1. Query Rewriting
    standalone_query = rewrite_query(question, chat_history, rag_model)
    print(f"Original query: {question}")
    print(f"Rewritten query: {standalone_query}")

    # 2. FAISS Retrieval (Dense)
    query_vec = embed_model.encode([standalone_query])
    query_vec = normalize(query_vec)
    D, faiss_indices = index.search(query_vec.astype("float32"), k=5)
    faiss_ranks = faiss_indices[0].tolist()

    # 3. BM25 Retrieval (Sparse/Keyword)
    tokenized_query = standalone_query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    bm25_ranks = np.argsort(bm25_scores)[::-1][:5].tolist()

    # 4. Reciprocal Rank Fusion
    fused_indices = reciprocal_rank_fusion(faiss_ranks, bm25_ranks)
    top_k_indices = fused_indices[:4] # Take top 4 after fusion
    
    top_chunks = []
    sources = []
    for idx in top_k_indices:
        chunk_text = metadata[idx]["text"]
        source = metadata[idx]["source"]
        top_chunks.append(f"[Source: {source}]\n{chunk_text}")
        if source not in sources:
            sources.append(source)

    # Prepare prompt
    context = "\n\n---\n\n".join(top_chunks)
    memory_str = "\n".join([f"{msg['role']}: {msg['text']}" for msg in chat_history]) if chat_history else "No previous conversation found."

    prompt = f"""
    You are a helpful assistant answering student admin questions at Monash University.

    Answer the following question using ONLY the context provided below. 
    Make sure to explicitly cite the source filenames at the end of your response, e.g., "Sources: course-dates.clean.txt, fees.clean.txt".
    -------------------
    ### Context:
    {context}

    -------------------
    ### Memory:
    {memory_str}

    -------------------

    ### User Question:
    {question}
    """

    # Generate streamed response
    response_stream = rag_model.generate_content(prompt, stream=True)

    for chunk in response_stream:
        try:
            if hasattr(chunk, "parts") and chunk.parts:
                text = ''.join([p.text for p in chunk.parts if hasattr(p, "text")])
                yield text
        except Exception as e:
            print(f"Warning: Skipped invalid chunk: {e}")
