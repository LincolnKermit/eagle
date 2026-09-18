import asyncio
import time

import httpx

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


class DuckDuckGoSource(Source):
    name = "duckduckgo"
    description = "Open web search via DuckDuckGo."
    input_types = ("email", "username", "phone", "domain", "bssid", "person")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip().strip('"').strip("'")
        try:
            from ddgs import DDGS

            def _do() -> list[dict]:
                hits = []
                with DDGS() as ddgs:
                    # 1. Try quoted exact phrase search
                    try:
                        hits = list(ddgs.text(f'"{clean}"', max_results=12))
                    except Exception:
                        hits = []
                    # 2. Supplement with broad search to discover social profiles and web references
                    if len(hits) < 15:
                        try:
                            broad = list(ddgs.text(clean, max_results=20))
                            seen_hrefs = {h.get("href") for h in hits if h.get("href")}
                            for b in broad:
                                if b.get("href") and b.get("href") not in seen_hrefs:
                                    hits.append(b)
                                    seen_hrefs.add(b.get("href"))
                        except Exception:
                            pass
                return hits

            raw_hits = await asyncio.to_thread(_do)
            for h in raw_hits:
                title = h.get("title", "")[:140] or "(no title)"
                body = (h.get("body") or "")[:240]
                href = h.get("href")
                combined = f"{title} {body} {href or ''}"

                # Strict relevance check: eliminate irrelevant results
                if _is_pertinent(combined, clean):
                    extra = {}
                    from ..location import detect_location_in_text
                    loc = detect_location_in_text(combined)
                    if loc:
                        extra.update(loc)
                    result.findings.append(
                        Finding(
                            label=title,
                            value=body,
                            url=href,
                            extra=extra,
                        )
                    )
            result.found = bool(result.findings)
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result

