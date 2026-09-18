import asyncio
import re
import time
import urllib.parse

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


class YandexSource(Source):
    name = "yandex"
    description = "Recherche web internationale, index Yandex & analyse de contenu."
    input_types = ("email", "username", "phone", "domain", "person")

    BASE_URL = "https://yandex.com/search/"

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        clean = target.strip().strip('"').strip("'")
        result = Result(source=self.name, target=target, found=False)
        query = f'"{clean}"'
        search_url = f"{self.BASE_URL}?text={urllib.parse.quote(query)}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # 1. Query Yandex Suggest API for relevant keywords & completions
        yandex_suggestions = []
        try:
            r_sug = await client.get(
                "https://suggest.yandex.com/suggest-ya.cgi",
                params={"part": clean, "v": 4},
                headers=headers,
                timeout=4,
            )
            if r_sug.status_code == 200:
                sug_data = r_sug.json()
                if len(sug_data) > 1 and isinstance(sug_data[1], list):
                    yandex_suggestions = [s for s in sug_data[1] if s.lower() != clean.lower()]
        except Exception:
            pass

        # 2. Scrape search SERP: first try Yandex, then fallback to multi-engine index
        items_to_scrape: list[dict] = []
        bot_challenged = False

        try:
            r_yan = await client.get(
                self.BASE_URL,
                params={"text": query, "lang": "en"},
                headers=headers,
                timeout=5,
                follow_redirects=True,
            )
            if "captcha" in str(r_yan.url).lower() or "showcaptchafast" in r_yan.text:
                bot_challenged = True
            elif r_yan.status_code == 200:
                soup = BeautifulSoup(r_yan.text, "lxml")
                for item in soup.select("li.serp-item, .Organic, .organic")[:10]:
                    a = item.select_one("a.OrganicTitle-Link, a[href^='http']")
                    if not a or not a.get("href"):
                        continue
                    href = a["href"]
                    if "yabs.yandex" in href:
                        continue
                    title_el = item.select_one(".OrganicTitle-LinkText, h2, h3, .OrganicTitle")
                    title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
                    snip_el = item.select_one(".OrganicText, .organic__text, .extended-text")
                    snippet = snip_el.get_text(" ", strip=True) if snip_el else ""
                    if _is_pertinent(f"{title} {snippet} {href}", clean):
                        items_to_scrape.append({"title": title, "url": href, "snippet": snippet})
        except Exception:
            bot_challenged = True

        # If Yandex SERP was bot-challenged or empty, scrape web index fallback
        if not items_to_scrape:
            try:
                yahoo_url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}"
                r_web = await client.get(yahoo_url, headers=headers, timeout=6, follow_redirects=True)
                if r_web.status_code == 200:
                    soup = BeautifulSoup(r_web.text, "lxml")
                    seen_urls = set()
                    for div in soup.select("div.algo, li div.dd"):
                        a = div.select_one("h3 a, a.d-ib")
                        if not a or not a.get("href"):
                            continue
                        href = a["href"]
                        if "/RU=" in href:
                            m = re.search(r"/RU=([^/]+)/", href)
                            if m:
                                href = urllib.parse.unquote(m.group(1))
                        if not href.startswith("http") or "yahoo.com" in href or href in seen_urls:
                            continue
                        seen_urls.add(href)
                        desc_el = div.select_one(".compText, p, .fc-2nd")
                        snip = desc_el.get_text(" ", strip=True) if desc_el else ""
                        title = a.get_text(strip=True)
                        if _is_pertinent(f"{title} {snip} {href}", clean):
                            items_to_scrape.append({"title": title, "url": href, "snippet": snip})
            except Exception:
                pass

        # 3. Deep scrape of destination URLs with BeautifulSoup
        async def scrape_target_page(item: dict) -> Finding:
            url = item["url"]
            fallback_title = item["title"]
            fallback_snip = item["snippet"]
            scraped_content = fallback_snip
            page_title = fallback_title

            try:
                r_page = await client.get(url, headers=headers, timeout=4, follow_redirects=True)
                if r_page.status_code == 200:
                    p_soup = BeautifulSoup(r_page.text, "lxml")
                    if p_soup.title and p_soup.title.get_text(strip=True):
                        page_title = p_soup.title.get_text(strip=True)
                    # Extract meta description
                    meta_tag = (
                        p_soup.find("meta", attrs={"name": "description"})
                        or p_soup.find("meta", attrs={"property": "og:description"})
                        or p_soup.find("meta", attrs={"name": "twitter:description"})
                    )
                    meta_desc = meta_tag["content"].strip() if meta_tag and meta_tag.get("content") else ""
                    # Extract body text snippet
                    body_paragraphs = [
                        p.get_text(strip=True)
                        for p in p_soup.select("main p, article p, p, h1, h2, h3")
                        if len(p.get_text(strip=True)) > 20
                    ]
                    body_text = " ".join(body_paragraphs[:4])

                    if meta_desc:
                        scraped_content = meta_desc
                    elif body_text:
                        scraped_content = body_text[:280]
            except Exception:
                pass

            # Detect probable location from title, snippet and scraped content
            combined_text = f"{page_title} {fallback_snip} {scraped_content}"
            loc = detect_location_in_text(combined_text)

            extra: dict = {
                "source_engine": "Yandex / Web SERP Scraper",
                "direct_url": url,
            }
            if loc:
                extra["city"] = loc["city"]
                extra["country"] = loc["country"]
                extra["location"] = loc["location"]
                extra["latitude"] = loc["latitude"]
                extra["longitude"] = loc["longitude"]

            return Finding(
                label=page_title[:140] or "(page sans titre)",
                value=scraped_content[:320] or fallback_snip[:320] or "(contenu extrait)",
                url=url,
                extra=extra,
            )

        if items_to_scrape:
            # Scrape up to 5 top items concurrently with bs4
            tasks = [scrape_target_page(it) for it in items_to_scrape[:5]]
            findings = await asyncio.gather(*tasks, return_exceptions=True)
            for f in findings:
                if isinstance(f, Finding):
                    result.findings.append(f)

        # 4. Add Yandex Suggest findings if any
        if yandex_suggestions:
            result.findings.append(
                Finding(
                    label="Yandex Suggestions",
                    value=", ".join(yandex_suggestions[:6]),
                    url=search_url,
                    extra={"source": "Yandex Suggest API"},
                )
            )

        # 5. Always include structured Yandex query link
        if not result.findings:
            result.findings.append(
                Finding(
                    label="Index de recherche Yandex",
                    value=f"Consulter les résultats directs sur Yandex : {query}",
                    url=search_url,
                    extra={"challenge_detected": bot_challenged},
                )
            )

        result.found = bool(result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
