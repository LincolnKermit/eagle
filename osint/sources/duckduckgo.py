import asyncio
import time

import httpx

from .base import Finding, Result, Source


class DuckDuckGoSource(Source):
    name = "duckduckgo"
    description = "Open web search via DuckDuckGo."
    input_types = ("email", "username", "phone", "domain")

    def _build_query(self, target: str) -> str:
        return f'"{target}"'

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        q = self._build_query(target)
        try:
            from ddgs import DDGS

            def _do() -> list[dict]:
                with DDGS() as ddgs:
                    return list(ddgs.text(q, max_results=12))

            hits = await asyncio.to_thread(_do)
            for h in hits:
                result.findings.append(
                    Finding(
                        label=h.get("title", "")[:140] or "(no title)",
                        value=(h.get("body") or "")[:240],
                        url=h.get("href"),
                    )
                )
            result.found = bool(result.findings)
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
