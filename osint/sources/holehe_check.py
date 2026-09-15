import asyncio
import importlib
import inspect
import pkgutil
import time

import httpx

from .base import Finding, Result, Source

KNOWN_MODULES = {
    "twitter", "instagram", "snapchat", "pinterest",
    "spotify", "github", "ebay", "lastfm", "deezer",
    "imgur", "rambler", "discord", "tumblr", "flickr",
    "anydo", "amazon", "atlassian", "axonaut", "codepen",
}


def _resolve_holehe_modules():
    funcs: list[tuple[str, callable]] = []
    try:
        import holehe.modules as hm
    except ImportError:
        return funcs

    seen: set[str] = set()
    for finder, mod_name, ispkg in pkgutil.walk_packages(hm.__path__, hm.__name__ + "."):
        if ispkg:
            continue
        short = mod_name.rsplit(".", 1)[-1]
        if short not in KNOWN_MODULES or short in seen:
            continue
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, short, None)
            if fn and inspect.iscoroutinefunction(fn):
                funcs.append((short, fn))
                seen.add(short)
        except Exception:
            continue
    return funcs


class HoleheSource(Source):
    name = "holehe"
    description = "Détection de comptes via signup-probing (Twitter, Insta, Spotify, GitHub...)."
    input_types = ("email",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        funcs = _resolve_holehe_modules()
        if not funcs:
            result.error = "holehe non installé ou modules introuvables."
            result.elapsed_ms = int((time.monotonic() - start) * 1000)
            return result

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as own:

            async def run_one(short: str, fn) -> dict | None:
                out: list[dict] = []
                try:
                    await fn(target, own, out)
                except TypeError:
                    try:
                        await fn(target, own, out, hibp=False)
                    except Exception:
                        return None
                except Exception:
                    return None
                if out and out[0].get("exists"):
                    return out[0]
                return None

            gathered = await asyncio.gather(
                *(run_one(n, f) for n, f in funcs), return_exceptions=False
            )

        for r in gathered:
            if not r:
                continue
            extra = {}
            if r.get("emailrecovery"):
                extra["recovery_email"] = r["emailrecovery"]
            if r.get("phoneNumber"):
                extra["phone_hint"] = r["phoneNumber"]
            if r.get("others"):
                extra.update({k: v for k, v in r["others"].items() if v})
            result.findings.append(
                Finding(label=r.get("name", "?"), value="account exists", extra=extra)
            )

        result.found = bool(result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
