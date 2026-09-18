import asyncio
import re
import time
from urllib.parse import quote

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


class GoogleActivitySource(Source):
    name = "google_activity"
    description = "Activité publique Google (Maps Reviews/Contrib, YouTube, Docs, Scholar, Calendar)."
    input_types = ("email", "username")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip()
        is_email = "@" in clean

        # 1. Check Google Calendar (if email)
        if is_email:
            try:
                cal_url = f"https://calendar.google.com/calendar/htmlembed?src={quote(clean)}"
                r_cal = await client.get(cal_url, timeout=5)
                if r_cal.status_code == 200 and "not found" not in r_cal.text.lower():
                    result.found = True
                    result.findings.append(
                        Finding(
                            label="Google Calendar Public",
                            value="Calendrier public accessible sans mot de passe",
                            url=cal_url,
                        )
                    )
            except Exception:
                pass

        # 2. Check YouTube Channel (if username)
        if not is_email and " " not in clean:
            try:
                yt_url = f"https://www.youtube.com/@{clean}"
                r_yt = await client.get(yt_url, timeout=6)
                if r_yt.status_code == 200 and "consent.youtube" not in str(r_yt.url):
                    result.found = True
                    result.findings.append(
                        Finding(
                            label=f"Chaîne YouTube @{clean}",
                            value="Profil / Chaîne YouTube active",
                            url=yt_url,
                        )
                    )
            except Exception:
                pass

        # 3. Google Maps Reviews & Contributions search
        try:
            from ddgs import DDGS

            def _search_maps() -> list[dict]:
                with DDGS() as ddgs:
                    hits = []
                    # Query Google Maps contrib
                    try:
                        hits.extend(list(ddgs.text(f'site:google.com/maps/contrib/ "{clean}"', max_results=5)))
                    except Exception:
                        pass
                    # Query Google Docs / Drive
                    try:
                        hits.extend(list(ddgs.text(f'site:docs.google.com "{clean}"', max_results=5)))
                    except Exception:
                        pass
                    # Query Google Scholar
                    try:
                        hits.extend(list(ddgs.text(f'site:scholar.google.com/citations "{clean}"', max_results=5)))
                    except Exception:
                        pass
                    return hits

            ddg_hits = await asyncio.to_thread(_search_maps)
            for h in ddg_hits:
                title = h.get("title", "")
                snippet = h.get("body", "")
                href = h.get("href", "")
                combined = f"{title} {snippet} {href}"

                # Strict relevance check
                if _is_pertinent(combined, clean):
                    result.findings.append(
                        Finding(
                            label=title[:120] or "Google Activity",
                            value=snippet[:240],
                            url=href,
                        )
                    )
        except Exception:
            pass

        result.found = bool(result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
