import asyncio
import re
import time
from typing import Optional

import httpx

from .base import Finding, Result, Source

# Core social platforms with validation strategy
# (Name, URL Template, Check Type)
# Check types:
#   "status": 200-299 = exists, 404 = missing
#   ("marker_missing", text): if text in response -> missing, else exists
#   ("marker_present", text): if text in response -> exists, else missing
PLATFORMS: list[tuple[str, str, object]] = [
    ("GitHub", "https://github.com/{u}", "status"),
    ("Instagram", "https://www.instagram.com/{u}/", "status"),
    ("Twitter/X", "https://x.com/{u}", ("marker_missing", "This account doesn’t exist")),
    ("LinkedIn", "https://www.linkedin.com/in/{u}", "status"),
    ("Reddit", "https://www.reddit.com/user/{u}", ("marker_missing", "Nobody on Reddit goes by that name")),
    ("TikTok", "https://www.tiktok.com/@{u}", ("marker_missing", "Couldn't find this account")),
    ("YouTube", "https://www.youtube.com/@{u}", "status"),
    ("Telegram", "https://t.me/{u}", ("marker_present", "tgme_page_extra")),
    ("Pinterest", "https://www.pinterest.com/{u}/", ("marker_missing", "<title></title>")),
    ("Twitch", "https://www.twitch.tv/{u}", "status"),
    ("GitLab", "https://gitlab.com/{u}", "status"),
    ("SoundCloud", "https://soundcloud.com/{u}", "status"),
    ("Medium", "https://medium.com/@{u}", "status"),
    ("Steam", "https://steamcommunity.com/id/{u}", ("marker_missing", "The specified profile could not be found")),
    ("Linktree", "https://linktr.ee/{u}", "status"),
    ("Chess.com", "https://www.chess.com/member/{u}", "status"),
    ("DEV.to", "https://dev.to/{u}", "status"),
    ("HackerNews", "https://news.ycombinator.com/user?id={u}", ("marker_missing", "No such user.")),
    ("Keybase", "https://keybase.io/{u}", "status"),
    ("Dribbble", "https://dribbble.com/{u}", "status"),
    ("Behance", "https://www.behance.net/{u}", "status"),
    ("Last.fm", "https://www.last.fm/user/{u}", "status"),
]


class UsernameSitesSource(Source):
    name = "username_sites"
    description = "Vérification systématique de présence sur 20+ réseaux sociaux majeurs."
    input_types = ("username", "person")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip()

        # Derive candidate usernames (e.g. 'John Doe' -> 'johndoe', 'john.doe')
        candidates = []
        if " " in clean:
            slug = re.sub(r"[^a-zA-Z0-9]", "", clean).lower()
            dot = re.sub(r"\s+", ".", clean).lower()
            if slug:
                candidates.append(slug)
            if dot and dot != slug:
                candidates.append(dot)
        else:
            candidates.append(clean.lower())

        if not candidates:
            result.elapsed_ms = int((time.monotonic() - start) * 1000)
            return result

        primary_u = candidates[0]
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        sem = asyncio.Semaphore(12)

        async def check_platform(name: str, tmpl: str, kind: object) -> Finding:
            best_url = tmpl.format(u=primary_u)
            found = False

            # Test primary candidate, and fallback to dot candidate if not found
            for u in candidates:
                url = tmpl.format(u=u)
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=6, follow_redirects=True)
                        if kind == "status":
                            if 200 <= r.status_code < 300:
                                found = True
                                best_url = url
                                break
                        elif isinstance(kind, tuple):
                            ktype, marker = kind
                            if 200 <= r.status_code < 300:
                                if ktype == "marker_missing" and marker not in r.text:
                                    found = True
                                    best_url = url
                                    break
                                elif ktype == "marker_present" and marker in r.text:
                                    found = True
                                    best_url = url
                                    break
                    except Exception:
                        continue

            return Finding(
                label=name,
                value="Profil détecté" if found else "Non trouvé",
                url=best_url,
                extra={
                    "platform": name,
                    "exists": found,
                    "category": "social",
                    "checked": True,
                },
            )

        tasks = [check_platform(name, tmpl, kind) for name, tmpl, kind in PLATFORMS]
        findings = await asyncio.gather(*tasks, return_exceptions=True)

        for f in findings:
            if isinstance(f, Finding):
                result.findings.append(f)

        result.found = any(f.extra.get("exists") for f in result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
