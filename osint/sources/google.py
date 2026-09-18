import time
import urllib.parse
from urllib.parse import parse_qs, urlparse
import re

import httpx
from bs4 import BeautifulSoup

from .base import Finding, Result, Source
from ..location import detect_location_in_text


def _is_pertinent(text: str, target: str) -> bool:
    clean = target.strip().strip('"').strip("'").lower()
    text_lower = text.lower()
    text_clean = re.sub(r"[^a-z0-9]", " ", text_lower)

    if "@" in clean:
        local, _, domain = clean.partition("@")
        return clean in text_lower or (local in text_clean and domain in text_clean)

    tokens = [t for t in re.findall(r"[a-z0-9]+", clean) if len(t) > 1]
    if not tokens:
        return clean in text_lower
    return any(tok in text_clean for tok in tokens)


class GoogleSource(Source):
    name = "google"
    description = "Google Search Index, Actualités & Suggestions OSINT."
    input_types = ("email", "username", "phone", "domain", "person")

    BASE = "https://www.google.com/search"

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip().strip('"').strip("'")
        query = f'"{clean}"'
        encoded_q = urllib.parse.quote(clean)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        # 1. Attempt standard Google SERP scraping
        try:
            r = await client.get(
                self.BASE,
                params={"q": query, "hl": "fr", "num": 20, "pws": 0},
                headers=headers,
                timeout=8,
            )
            if r.status_code == 200 and not (
                "/sorry/" in str(r.url)
                or "detected unusual traffic" in r.text.lower()
                or "/httpservice/retry" in r.text
                or "enablejs" in r.text.lower()
            ):
                soup = BeautifulSoup(r.text, "lxml")
                seen = set()
                for h3 in soup.select("h3"):
                    a = h3.find_parent("a")
                    if not a or not a.get("href"):
                        continue
                    href = a["href"]
                    if href.startswith("/url?"):
                        qs = parse_qs(urlparse(href).query)
                        href = qs.get("q", [href])[0]
                    if not href.startswith("http") or href in seen:
                        continue
                    seen.add(href)
                    title = h3.get_text(strip=True)
                    snippet = ""
                    container = h3.find_parent("div")
                    if container:
                        for s in container.select("div"):
                            t = s.get_text(" ", strip=True)
                            if t and t != title and len(t) > 30:
                                snippet = t[:240]
                                break
                    if _is_pertinent(f"{title} {snippet} {href}", clean):
                        extra = {}
                        loc = detect_location_in_text(f"{title} {snippet}")
                        if loc:
                            extra.update(loc)
                        result.findings.append(
                            Finding(label=title or "(untitled)", value=snippet, url=href, extra=extra)
                        )
        except Exception:
            pass

        # 2. Query Google News RSS (FR & Global)
        try:
            for feed_url in [
                f"https://news.google.com/rss/search?q={encoded_q}&hl=fr&gl=FR&ceid=FR:fr",
                f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en",
            ]:
                try:
                    r_news = await client.get(feed_url, headers=headers, timeout=6)
                    if r_news.status_code == 200:
                        news_soup = BeautifulSoup(r_news.text, "xml")
                        items = news_soup.find_all("item")
                        for item in items[:10]:
                            title = item.title.text if item.title else "(untitled)"
                            link = item.link.text if item.link else None
                            pub_date = item.pubDate.text if item.pubDate else ""
                            src = item.source.text if item.source else "Google News"
                            desc = f"{src} · {pub_date}".strip(" · ")
                            if _is_pertinent(f"{title} {desc} {link or ''}", clean):
                                extra = {}
                                loc = detect_location_in_text(f"{title} {desc}")
                                if loc:
                                    extra.update(loc)
                                result.findings.append(
                                    Finding(label=title, value=desc, url=link, extra=extra)
                                )
                except Exception:
                    continue
        except Exception:
            pass

        # 3. Query Google Autocomplete / Suggest API
        try:
            sug_url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={encoded_q}"
            r_sug = await client.get(sug_url, headers=headers, timeout=5)
            if r_sug.status_code == 200:
                sug_data = r_sug.json()
                if len(sug_data) > 1 and isinstance(sug_data[1], list):
                    suggestions = [s for s in sug_data[1] if s.lower() != clean.lower()]
                    if suggestions:
                        result.findings.append(
                            Finding(
                                label="Google Suggest (Termes associés)",
                                value=", ".join(suggestions[:8]),
                                url=f"https://www.google.com/search?q={encoded_q}",
                                extra={"source": "Google Suggest API", "suggestions_count": len(suggestions)},
                            )
                        )
        except Exception:
            pass

        # 4. If no organic SERP scraped, provide direct Google search & curated OSINT dorks
        if not any(f.url and "google.com/search" not in f.url for f in result.findings):
            main_search_url = f"https://www.google.com/search?q={encoded_q}"
            result.findings.append(
                Finding(
                    label="Google Web Search",
                    value=f"Recherche Google directe pour : {clean}",
                    url=main_search_url,
                    extra={
                        "dork_social": f"https://www.google.com/search?q={urllib.parse.quote(f'site:linkedin.com OR site:twitter.com OR site:instagram.com \"{clean}\"')}",
                        "dork_documents": f"https://www.google.com/search?q={urllib.parse.quote(f'filetype:pdf OR filetype:doc \"{clean}\"')}",
                    },
                )
            )

        result.found = bool(result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
