import os
import json
import numpy as np
from backend.app.ai_rag.embeddings import get_embedding

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ai_index")

_index = None
_metadata = None

def load_index_if_needed():
    global _index, _metadata
    if _index is None:
        import faiss
        index_path = os.path.join(INDEX_DIR, "knowledge.faiss")
        metadata_path = os.path.join(INDEX_DIR, "metadata.json")
        
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            _index = faiss.read_index(index_path)
            with open(metadata_path, 'r') as f:
                _metadata = json.load(f)
        else:
            raise FileNotFoundError("FAISS index not found. Did you run indexer.py?")

def retrieve_context(query: str, top_k: int = 5) -> str:
    try:
        load_index_if_needed()
    except FileNotFoundError:
        return "Application documentation index not found."
        
    query_vector = np.array([get_embedding(query)]).astype('float32')
    distances, indices = _index.search(query_vector, top_k)
    
    results = []
    for idx in indices[0]:
        if idx != -1:
            chunk = _metadata[str(idx)]
            results.append(f"--- Document: {chunk['file']} (Section: {chunk['section']}) ---\n{chunk['text']}")
            
    return "\n\n".join(results)
