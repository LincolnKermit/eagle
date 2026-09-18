import time
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from .base import Finding, Result, Source


import re


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
    return all(tok in text_clean for tok in tokens)


class GoogleSource(Source):
    name = "google"
    description = "Custom Google SERP scraper (sans API)."
    input_types = ("email", "username", "phone", "domain", "person")

    BASE = "https://www.google.com/search"

    def _build_query(self, target: str) -> str:
        return f'"{target}"'

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip().strip('"').strip("'")
        q = self._build_query(clean)
        bot_challenged = False
        try:
            r = await client.get(
                self.BASE,
                params={"q": q, "hl": "en", "num": 20, "pws": 0},
            )
            if r.status_code != 200:
                bot_challenged = True
            elif (
                "/sorry/" in str(r.url)
                or "detected unusual traffic" in r.text.lower()
                or "/httpservice/retry" in r.text
                or "enablejs" in r.text.lower()
            ):
                bot_challenged = True
            else:
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
                        result.findings.append(
                            Finding(label=title or "(untitled)", value=snippet, url=href)
                        )

            # If web SERP blocked or returned no hits, query Google News RSS
            if not result.findings:
                import urllib.parse
                r_news = await client.get(
                    f"https://news.google.com/rss/search?q={urllib.parse.quote(clean)}&hl=en-US&gl=US&ceid=US:en"
                )
                if r_news.status_code == 200:
                    news_soup = BeautifulSoup(r_news.text, "xml")
                    for item in news_soup.find_all("item")[:20]:
                        title = item.title.text if item.title else "(untitled)"
                        link = item.link.text if item.link else None
                        pub_date = item.pubDate.text if item.pubDate else ""
                        if _is_pertinent(f"{title} {pub_date} {link or ''}", clean):
                            result.findings.append(
                                Finding(label=title, value=pub_date, url=link)
                            )

            result.found = bool(result.findings)
            if not result.found and bot_challenged:
                result.error = "Google requiert l'exécution de JavaScript ou a bloqué la requête."
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
