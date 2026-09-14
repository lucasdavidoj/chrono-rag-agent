import logging
import time

import requests
from app.config import REQUEST_DELAY, WIKI_BASE_URL, WIKI_HEADERS

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s"
)

ROOT_CATEGORY = "Category:Chrono_Trigger"
NON_CT_CATEGORIES = {
    "Category:Dragons",
    "Category:Fiends",
    "Category:Time Travelers",
    "Category:Robots",
}
MANUAL_KEEP_ARTICLES = {"Mammon Machine"}


class WikiExplorer:
    def __init__(self):
        self.categories = {ROOT_CATEGORY}
        self.articles = []
        self.errors = []

    def process(self):
        self._explore_category(ROOT_CATEGORY)
        self._explore_articles()

        self.log_errors()

    def log_errors(self):
        for error in self.errors:
            function = error["function"]
            item = error["item"]
            message = error["message"]
            logging.warning(f"[{function}] Item: {item} -> {message}")

    def _explore_category(self, category):
        sub_categories = self._get_sub_categories(category)

        for sub_category in sub_categories:
            if sub_category not in self.categories:
                self.categories.add(sub_category)

                self._explore_category(sub_category)

    def _get_sub_categories(self, category) -> list:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "subcat",
            "cmnamespace": "14",
            "cmlimit": "500",
            "format": "json",
        }

        try:
            response = requests.get(
                url=WIKI_BASE_URL,
                params=params,
                headers=WIKI_HEADERS,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.errors.append(
                {"message": e, "function": "_get_sub_categories", "item": category}
            )

            return []

        time.sleep(REQUEST_DELAY)

        data = response.json()
        categories = data["query"]["categorymembers"]

        return [item["title"] for item in categories]

    def _explore_articles(self):
        articles = [
            article
            for category in self.categories
            for article in self._get_articles(category)
        ]

        grouped = {}

        for article in articles:
            title = article["title"]

            if title not in grouped:
                grouped[title] = {"title": title, "categories": set()}

            grouped[title]["categories"].add(article["category"])

        unfiltered_articles = list(grouped.values())

        self._filter_articles(unfiltered_articles)

    def _get_articles(self, category):
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmnamespace": "0",
            "cmlimit": "500",
            "format": "json",
        }

        try:
            response = requests.get(
                url=WIKI_BASE_URL,
                params=params,
                headers=WIKI_HEADERS,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.errors.append(
                {"message": e, "function": "_get_articles", "item": category}
            )

            return []

        time.sleep(REQUEST_DELAY)

        data = response.json()

        articles = data["query"]["categorymembers"]

        return [
            {"title": article["title"], "category": category} for article in articles
        ]

    def _filter_articles(self, unfiltered_articles):
        for article in unfiltered_articles:
            art_categories = article["categories"]

            n_prohibited_categories = self._count_prohibited_categories(article)

            if len(art_categories) == n_prohibited_categories:
                if article["title"] not in MANUAL_KEEP_ARTICLES:
                    continue

            self.articles.append(article)

    def _count_prohibited_categories(self, article):
        return len(article["categories"] & NON_CT_CATEGORIES)


if __name__ == "__main__":
    explorer = WikiExplorer()

    explorer.process()
