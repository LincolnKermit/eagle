import asyncio
import time

import httpx

from .base import Finding, Result, Source

SITES: list[tuple[str, str, object]] = [
    ("GitHub", "https://github.com/{u}", "status"),
    ("Twitter/X", "https://twitter.com/{u}", "status"),
    ("GitLab", "https://gitlab.com/{u}", "status"),
    ("Pinterest", "https://www.pinterest.com/{u}/", ("marker_missing", "<title></title>")),
    ("SoundCloud", "https://soundcloud.com/{u}", "status"),
    ("Medium", "https://medium.com/@{u}", "status"),
    ("HackerNews", "https://news.ycombinator.com/user?id={u}", ("marker_missing", "No such user.")),
    ("DEV.to", "https://dev.to/{u}", "status"),
    ("Keybase", "https://keybase.io/{u}", "status"),
    ("Replit", "https://replit.com/@{u}", "status"),
    ("Behance", "https://www.behance.net/{u}", "status"),
    ("Dribbble", "https://dribbble.com/{u}", "status"),
    ("Vimeo", "https://vimeo.com/{u}", "status"),
    ("Mastodon", "https://mastodon.social/@{u}", "status"),
    ("ProductHunt", "https://www.producthunt.com/@{u}", "status"),
    ("Last.fm", "https://www.last.fm/user/{u}", "status"),
    ("Steam", "https://steamcommunity.com/id/{u}", ("marker_missing", "The specified profile could not be found")),
    ("Roblox", "https://www.roblox.com/users/profile?username={u}", "status"),
    ("itch.io", "https://{u}.itch.io/", "status"),
    ("HackerOne", "https://hackerone.com/{u}", "status"),
    ("Linktree", "https://linktr.ee/{u}", "status"),
    ("Chess.com", "https://www.chess.com/member/{u}", "status"),
]


class UsernameSitesSource(Source):
    name = "username_sites"
    description = "Présence du username sur 25+ plateformes."
    input_types = ("username",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip()
        if " " in clean:
            # Usernames cannot contain spaces
            result.elapsed_ms = int((time.monotonic() - start) * 1000)
            return result

        async def check(name: str, pattern: str, kind):
            url = pattern.format(u=target)
            try:
                r = await client.get(url, timeout=10)
            except Exception:
                return None

            if kind == "status":
                if 200 <= r.status_code < 300:
                    return Finding(label=name, value="profile exists", url=url)
                return None

            if isinstance(kind, tuple):
                ktype, marker = kind
                if r.status_code != 200:
                    return None
                text = r.text
                if ktype == "marker_missing" and marker in text:
                    return None
                if ktype == "marker_present" and marker not in text:
                    return None
                return Finding(label=name, value="profile exists", url=url)
            return None

        sem = asyncio.Semaphore(10)

        async def bounded(item):
            async with sem:
                return await check(*item)

        findings = await asyncio.gather(*(bounded(s) for s in SITES))
        for f in findings:
            if f:
                result.findings.append(f)
        result.found = bool(result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
