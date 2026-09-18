import re
import time

import httpx

from .base import Finding, Result, Source


def _is_pertinent(text: str, target: str) -> bool:
    clean = target.strip().strip('"').strip("'").lower()
    text_lower = text.lower()
    text_clean = re.sub(r"[^a-z0-9]", " ", text_lower)
    tokens = [t for t in re.findall(r"[a-z0-9]+", clean) if len(t) > 1]
    if not tokens:
        return clean in text_lower
    return all(tok in text_clean for tok in tokens)


class WikipediaSource(Source):
    name = "wikipedia"
    description = "Recherche de notices biographiques et encyclopédiques (Wikipédia FR/EN)."
    input_types = ("username", "domain", "person")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip()
        headers = {"User-Agent": "Eagle-OSINT-Framework/1.0"}

        seen_urls = set()
        for lang in ("fr", "en"):
            try:
                r = await client.get(
                    f"https://{lang}.wikipedia.org/w/api.php",
                    params={
                        "action": "opensearch",
                        "search": clean,
                        "limit": "5",
                        "format": "json",
                    },
                    headers=headers,
                    timeout=6,
                )
                if r.status_code == 200:
                    data = r.json()
                    titles = data[1] if len(data) > 1 else []
                    snippets = data[2] if len(data) > 2 else []
                    urls = data[3] if len(data) > 3 else []

                    for t, s, u in zip(titles, snippets, urls):
                        if u not in seen_urls and _is_pertinent(f"{t} {s} {u}", clean):
                            seen_urls.add(u)
                            result.findings.append(
                                Finding(
                                    label=f"[{lang.upper()}] {t}",
                                    value=s or f"Article Wikipédia pour {t}",
                                    url=u,
                                )
                            )
            except Exception:
                pass

        result.found = bool(result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
