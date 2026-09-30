import os
import glob
import json
import faiss
import numpy as np
from backend.app.ai_rag.chunker import chunk_markdown_file
from backend.app.ai_rag.embeddings import get_embedding_model

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ai_knowledge")
INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ai_index")

def build_index():
    os.makedirs(INDEX_DIR, exist_ok=True)
    
    files = glob.glob(os.path.join(KNOWLEDGE_DIR, "*.md"))
    all_chunks = []
    
    for filepath in files:
        chunks = chunk_markdown_file(filepath)
        all_chunks.extend(chunks)
        
    if not all_chunks:
        print("No markdown files found to index.")
        return

    # Embed all texts
    texts = [c["text"] for c in all_chunks]
    model = get_embedding_model()
    embeddings = model.encode(texts) # numpy array
    
    # Initialize FAISS Index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    
    # Add embeddings to the index
    index.add(np.array(embeddings).astype('float32'))
    
    # Save the index
    faiss.write_index(index, os.path.join(INDEX_DIR, "knowledge.faiss"))
    
    # Save metadata mapping
    metadata = {}
    for i, chunk in enumerate(all_chunks):
        metadata[str(i)] = chunk
        
    with open(os.path.join(INDEX_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Successfully indexed {len(all_chunks)} chunks from {len(files)} files.")

if __name__ == "__main__":
    build_index()
