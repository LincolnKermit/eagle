import time
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from .base import Finding, Result, Source


class GoogleSource(Source):
    name = "google"
    description = "Custom Google SERP scraper (sans API)."
    input_types = ("email", "username", "phone", "domain")

    BASE = "https://www.google.com/search"

    def _build_query(self, target: str) -> str:
        return f'"{target}"'

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        q = self._build_query(target)
        try:
            r = await client.get(
                self.BASE,
                params={"q": q, "hl": "en", "num": 20, "pws": 0},
            )
            if r.status_code != 200:
                result.error = f"HTTP {r.status_code}"
            elif "/sorry/" in str(r.url) or "detected unusual traffic" in r.text.lower():
                result.error = "Google a bloqué la requête (captcha)."
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
                    result.findings.append(
                        Finding(label=title or "(untitled)", value=snippet, url=href)
                    )
                result.found = bool(result.findings)
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
