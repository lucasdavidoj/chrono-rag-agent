import json

import numpy as np
import requests
from app.config import EMBEDDINGS_OUTPUT_FILE, OPENROUTER_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/embeddings"
MODEL = "baai/bge-m3"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}


class VectorSearch:
    def __init__(self):
        with open(EMBEDDINGS_OUTPUT_FILE, encoding="utf-8") as file:
            self.chunks = json.load(file)

        self.vectors = np.array([chunk["embedding"] for chunk in self.chunks])
        self.norms = np.linalg.norm(self.vectors, axis=1)

    def search(self, query, top_k=5):
        query_vector = np.array(self._embed_query(query))

        similarities = (
            self.vectors @ query_vector / (self.norms * np.linalg.norm(query_vector))
        )

        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            {
                "chunk_id": self.chunks[i]["chunk_id"],
                "article_title": self.chunks[i]["article_title"],
                "categories": self.chunks[i]["categories"],
                "text": self.chunks[i]["text"],
                "similarity": float(similarities[i]),
            }
            for i in top_indices
        ]

    def _embed_query(self, query):
        response = requests.post(
            url=OPENROUTER_URL,
            headers=HEADERS,
            json={"model": MODEL, "input": [query]},
        )
        response.raise_for_status()

        data = response.json()

        return data["data"][0]["embedding"]


if __name__ == "__main__":
    search = VectorSearch()

    query = "What weapon does Crono use?"
    results = search.search(query, top_k=3)

    for r in results:
        print(f"{r['similarity']:.4f} | {r['chunk_id']}")
        print(r["text"][:200])
        print()
