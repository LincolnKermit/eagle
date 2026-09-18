import re
import time
from urllib.parse import quote, urlparse

import httpx
from bs4 import BeautifulSoup

from .base import Finding, Result, Source


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


class YandexSource(Source):
    name = "yandex"
    description = "Recherche web internationale et index Yandex."
    input_types = ("email", "username", "phone", "domain", "person")

    BASE_URL = "https://yandex.com/search/"

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        clean = target.strip().strip('"').strip("'")
        result = Result(source=self.name, target=target, found=False)
        query = f'"{clean}"'
        search_url = f"{self.BASE_URL}?text={quote(query)}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,ru;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        bot_challenged = False
        try:
            r = await client.get(
                self.BASE_URL,
                params={"text": query, "lang": "en"},
                headers=headers,
                timeout=8,
            )

            if r.status_code == 302 or "captcha" in str(r.url).lower() or "showcaptchafast" in r.text:
                bot_challenged = True
            elif r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                # Look for search result items
                items = soup.select("li.serp-item, .Organic, .organic")
                seen = set()
                for item in items[:15]:
                    a = item.select_one("a.OrganicTitle-Link, a[href^='http']")
                    if not a or not a.get("href"):
                        continue
                    href = a["href"]
                    if href in seen or "yabs.yandex" in href:
                        continue
                    seen.add(href)

                    title_el = item.select_one(".OrganicTitle-LinkText, h2, h3, .OrganicTitle")
                    title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)

                    snip_el = item.select_one(".OrganicText, .organic__text, .extended-text")
                    snippet = snip_el.get_text(" ", strip=True) if snip_el else ""

                    if _is_pertinent(f"{title} {snippet} {href}", clean):
                        result.findings.append(
                            Finding(label=title or "(untitled)", value=snippet[:240], url=href)
                        )

            if not result.findings:
                # Provide direct search query link
                result.findings.append(
                    Finding(
                        label="Yandex Search Index",
                        value=f"Consulter les résultats Yandex pour la requête : {query}",
                        url=search_url,
                        extra={
                            "service": "Yandex.com",
                            "challenge_detected": bot_challenged,
                            "notice": (
                                "SmartCaptcha activé côté Yandex pour requêtes automatisées — lien direct prêt à l'emploi."
                                if bot_challenged
                                else "Requête exécutée."
                            ),
                        },
                    )
                )

            result.found = bool(result.findings)
        except Exception as e:
            result.error = str(e)

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
