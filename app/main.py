import json
import logging
from pathlib import Path

from app.article_fetcher import ArticleFetcher
from app.config import (
    ARTICLES_OUTPUT_FILE,
    CHUNKING_OUTPUT_FILE,
    EMBEDDINGS_OUTPUT_FILE,
)
from app.data_chunker import DataChunker
from app.embedding_generator import EmbeddingGenerator
from app.wiki_explorer import WikiExplorer

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s"
)


def fetch_articles():
    explorer = WikiExplorer()
    explorer.process()

    total = len(explorer.articles)
    print(f"{total} articles found by WikiExplorer.")

    fetcher = ArticleFetcher()
    results = []
    failed = []

    for i, article in enumerate(explorer.articles, start=1):
        title = article["title"]

        print(f"Processing {i}/{total}: {title}")

        try:
            text = fetcher.process(title)
        except Exception as e:
            logging.warning(f"[process] Item: {title} -> {type(e).__name__}: {e}")
            failed.append(title)
            continue

        results.append(
            {
                "title": title,
                "categories": sorted(article["categories"]),
                "text": text,
            }
        )

    with open(ARTICLES_OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(results)} articles saved to {ARTICLES_OUTPUT_FILE}.")
    print(f"{len(failed)} articles failed.")

    if failed:
        print("Failed articles:")
        for title in failed:
            print(f" - {title}")


def main():
    if Path(ARTICLES_OUTPUT_FILE).exists():
        print(f"{ARTICLES_OUTPUT_FILE} already exists, skipping article fetching.")
    else:
        fetch_articles()

    if Path(CHUNKING_OUTPUT_FILE).exists():
        print(f"{CHUNKING_OUTPUT_FILE} already exists, skipping chunking.")
    else:
        DataChunker().process()

    if Path(EMBEDDINGS_OUTPUT_FILE).exists():
        print(f"{EMBEDDINGS_OUTPUT_FILE} already exists, skipping embedding.")
    else:
        EmbeddingGenerator().process()


if __name__ == "__main__":
    main()
