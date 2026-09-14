import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

WIKI_BASE_URL = "https://chrono.fandom.com/api.php"
WIKI_CONTACT_EMAIL = os.environ["WIKI_CONTACT_EMAIL"]
WIKI_HEADERS = {"User-Agent": f"chrono-rag-agent/1.0 ({WIKI_CONTACT_EMAIL})"}
ARTICLES_OUTPUT_FILE = STORAGE_DIR / "articles.json"
CHUNKING_OUTPUT_FILE = STORAGE_DIR / "chunks.json"
EMBEDDINGS_OUTPUT_FILE = STORAGE_DIR / "embeddings.json"
REQUEST_DELAY = 0.5
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
