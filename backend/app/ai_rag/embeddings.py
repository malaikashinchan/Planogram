# Load a small, fast model for embeddings
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_embedding(text: str):
    model = get_embedding_model()
    # Return as list of floats
    return model.encode(text).tolist()
