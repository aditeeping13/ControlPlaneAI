import os
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

AUTHORITATIVE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'authoritative')

class RetrievalService:
    def __init__(self):
        self.documents = []
        self.doc_names = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        self._load_documents()

    def _load_documents(self):
        if not os.path.exists(AUTHORITATIVE_DIR):
            return
            
        for filename in os.listdir(AUTHORITATIVE_DIR):
            if filename.endswith(".txt"):
                filepath = os.path.join(AUTHORITATIVE_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Basic chunking: split by newlines for MVP
                    chunks = [c.strip() for c in content.split('\n') if c.strip()]
                    for chunk in chunks:
                        self.documents.append(chunk)
                        self.doc_names.append(filename)
                        
        if self.documents:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)

    def retrieve_relevant_chunks(self, query: str, top_k: int = 2) -> List[Tuple[str, str, float]]:
        if not self.documents or self.tfidf_matrix is None:
            return []
            
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            score = similarities[idx]
            if score > 0.1: # Minimum similarity threshold
                results.append((self.documents[idx], self.doc_names[idx], float(score)))
                
        return results

retrieval_service = RetrievalService()
