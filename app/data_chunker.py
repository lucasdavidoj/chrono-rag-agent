import json

from app.config import ARTICLES_OUTPUT_FILE, CHUNKING_OUTPUT_FILE

SKIP_LINE_PREFIXES = {"__TOC__"}


class DataChunker:
    def process(self):
        with open(ARTICLES_OUTPUT_FILE, encoding="utf-8") as file:
            articles = json.load(file)

        chunks = []

        for article in articles:
            title = article["title"]
            categories = article["categories"]
            text_chunks = article["text"].split("\n\n")

            for index, text_chunk in enumerate(text_chunks):
                text_chunk = self._clean_chunk(text_chunk)

                if not text_chunk or text_chunk.lower().startswith("redirect "):
                    continue

                chunk_id = f"{title}::{index}"

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "article_title": title,
                        "categories": categories,
                        "text": text_chunk,
                    }
                )

        with open(CHUNKING_OUTPUT_FILE, "w", encoding="utf-8") as file:
            json.dump(chunks, file, ensure_ascii=False, indent=2)

    def _clean_chunk(self, text):
        lines = [
            line for line in text.split("\n") if line.strip() not in SKIP_LINE_PREFIXES
        ]

        return "\n".join(lines).strip()
