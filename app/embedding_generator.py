import json
import logging

import requests
from app.config import CHUNKING_OUTPUT_FILE, EMBEDDINGS_OUTPUT_FILE, OPENROUTER_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/embeddings"
MODEL = "baai/bge-m3"
BATCH_SIZE = 50
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s"
)


class EmbeddingGenerator:
    def process(self):
        with open(CHUNKING_OUTPUT_FILE, encoding="utf-8") as file:
            chunks = json.load(file)

        results = []
        total_batches = (len(chunks) - 1) // BATCH_SIZE + 1

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            batch_number = i // BATCH_SIZE + 1

            print(f"Embedding batch {batch_number}/{total_batches}")

            try:
                embeddings = self._embed_batch([item["text"] for item in batch])
            except Exception as e:
                logging.warning(
                    f"[_embed_batch] batch {batch_number} -> {type(e).__name__}: {e}"
                )
                continue

            for chunk, embedding in zip(batch, embeddings, strict=True):
                results.append(
                    {
                        **chunk,
                        "embedding": embedding,
                    }
                )

        with open(EMBEDDINGS_OUTPUT_FILE, "w", encoding="utf-8") as file:
            json.dump(results, file, ensure_ascii=False, indent=2)

        print(f"\nDone. {len(results)} embeddings saved to {EMBEDDINGS_OUTPUT_FILE}.")

    def _embed_batch(self, texts):
        response = requests.post(
            url=OPENROUTER_URL,
            headers=HEADERS,
            json={"model": MODEL, "input": texts},
        )
        response.raise_for_status()

        data = response.json()

        return [item["embedding"] for item in data["data"]]
