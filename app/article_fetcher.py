import logging
import time

import mwparserfromhell
import requests
import wikitextparser as wtp
from app.config import HEADERS, REQUEST_DELAY, WIKI_BASE_URL

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s"
)

SKIP_SECTIONS = {"gallery", "site navigation"}
SKIP_INFOBOX_PARAMS = {"image", "img", "caption"}
SKIP_LINE_PREFIXES = ("es:", "pt-br:", "it:", "fr:", "de:", "Category:")
SKIP_TEMPLATES_EXACT = {"chrono trigger", "chrono series"}
SKIP_TEMPLATE_PREFIXES = ("ct ", "map:")
SKIP_TEMPLATE_SUFFIXES = ("-stub",)


class ArticleFetcher:
    def process(self, article):
        raw_wikitext = self._fetch_wikitext(article)

        wikicode = mwparserfromhell.parse(raw_wikitext)

        infobox_text, infobox_template = self._extract_infobox(wikicode)

        if infobox_template is not None:
            wikicode.remove(infobox_template)

        self._clean_templates(wikicode)

        text_without_infobox = str(wikicode)

        expanded_text = self._expand_templates(text_without_infobox, article)

        tables_text, text_without_tables = self._extract_tables(expanded_text)

        final_text = self._clean_prose(text_without_tables)

        sections = [text for text in [infobox_text, final_text, tables_text] if text]

        return "\n\n".join(sections)

    def _fetch_wikitext(self, article):
        params = {
            "action": "query",
            "prop": "revisions",
            "titles": article,
            "rvslots": "main",
            "rvprop": "content",
            "format": "json",
        }

        response = requests.get(WIKI_BASE_URL, params=params, headers=HEADERS)
        response.raise_for_status()

        time.sleep(REQUEST_DELAY)

        data = response.json()
        pages = data["query"]["pages"]
        page = next(iter(pages.values()))

        return page["revisions"][0]["slots"]["main"]["*"]

    def _extract_infobox(self, wikicode):
        infobox_lines = []
        infobox_template = None

        for template in wikicode.filter_templates():
            name = self._normalize_template_name(template)

            if name.lower().startswith("infobox"):
                infobox_template = template

                for param in template.params:
                    key = str(param.name).strip()

                    if key.lower() in SKIP_INFOBOX_PARAMS:
                        continue

                    value = (
                        mwparserfromhell.parse(str(param.value)).strip_code().strip()
                    )

                    if value:
                        infobox_lines.append(f"{key}: {value}")

                break

        if not infobox_lines:
            return "", infobox_template

        return "Details\n" + "\n".join(infobox_lines), infobox_template

    def _expand_templates(self, text, article):
        params = {
            "action": "expandtemplates",
            "text": text,
            "title": article,
            "prop": "wikitext",
            "format": "json",
        }

        response = requests.post(
            WIKI_BASE_URL,
            data=params,
            headers=HEADERS,
        )
        response.raise_for_status()

        time.sleep(REQUEST_DELAY)

        data = response.json()

        return data.get("expandtemplates", {}).get("wikitext", "")

    def _extract_tables(self, text):
        sections = wtp.parse(text).get_sections()
        results = []
        seen_spans = set()

        for section in reversed(sections):
            for table in section.tables:
                if table.span in seen_spans:
                    continue

                seen_spans.add(table.span)

                title = section.title.strip() if section.title else "Tabela"
                table_text = self._clean_table(title, table)

                if table_text:
                    results.append(table_text)

                text = text.replace(str(table), "")

        return "\n\n".join(results), text

    def _clean_table(self, title, table):
        rows = table.data(span=True)

        if not rows:
            return None

        headers = rows[0]
        lines = []

        for row in rows[1:]:
            pairs = []

            for header, value in zip(headers, row, strict=True):
                header_clean = mwparserfromhell.parse(str(header)).strip_code().strip()
                value_clean = mwparserfromhell.parse(str(value)).strip_code().strip()

                if header_clean and value_clean:
                    pairs.append(f"{header_clean}: {value_clean}")

            if pairs:
                lines.append(", ".join(pairs))

        if not lines:
            return None

        return f"{title}:\n" + "\n".join(lines)

    def _clean_prose(self, text):
        text = self._clean_skip_sections(text)

        wikicode = mwparserfromhell.parse(text)

        heading_titles = {str(h.title).strip() for h in wikicode.filter_headings()}

        self._clean_galleries(wikicode)

        self._clean_links(wikicode)

        prose = wikicode.strip_code()

        lines = [line.strip() for line in prose.split("\n")]
        lines = [
            line for line in lines if line and not line.startswith(SKIP_LINE_PREFIXES)
        ]

        result_lines = self._clean_lines(lines, heading_titles)

        return "\n".join(result_lines)

    def _clean_skip_sections(self, text) -> str:
        sections = wtp.parse(text).get_sections()
        cut = None

        for section in sections:
            if section.title and section.title.strip().lower() in SKIP_SECTIONS:
                start = section.span[0]
                if cut is None or start < cut:
                    cut = start

        if cut is not None:
            text = text[:cut]

        return text

    def _clean_galleries(self, wikicode) -> None:
        for gallery in wikicode.filter_tags(matches=lambda n: n.tag == "gallery"):
            wikicode.remove(gallery)

    def _clean_links(self, wikicode) -> None:
        for link in wikicode.filter_wikilinks():
            title = str(link.title).strip()
            if title.lower().startswith(("file:", "image:")):
                wikicode.remove(link)

    def _clean_lines(self, lines, heading_titles):
        result_lines = []

        for i, line in enumerate(lines):
            is_heading = line in heading_titles

            if is_heading:
                next_is_heading_or_end = (
                    i + 1 >= len(lines) or lines[i + 1] in heading_titles
                )

                if next_is_heading_or_end:
                    continue

                if result_lines:
                    result_lines.append("")

            result_lines.append(line)

        return result_lines

    def _clean_templates(self, wikicode) -> None:
        for template in wikicode.filter_templates():
            name = self._normalize_template_name(template)

            if (
                name in SKIP_TEMPLATES_EXACT
                or name.startswith(SKIP_TEMPLATE_PREFIXES)
                or name.endswith(SKIP_TEMPLATE_SUFFIXES)
            ):
                wikicode.remove(template)

    def _normalize_template_name(self, template) -> str:
        name = str(template.name).strip().lower()

        if name.startswith("template:"):
            name = name[len("template:") :].strip()

        return name
