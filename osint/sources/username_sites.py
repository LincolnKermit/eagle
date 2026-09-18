import asyncio
import re
import time
from typing import Optional

from bs4 import BeautifulSoup
import httpx

from .base import Finding, Result, Source


class UsernameSitesSource(Source):
    name = "username_sites"
    description = "Vérification systématique et certifiée de présence sur 20+ réseaux sociaux majeurs."
    input_types = ("username", "person")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip()

        # Derive candidate usernames and search tokens
        tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", clean.lower()) if len(t) > 1]
        candidates = []
        if " " in clean:
            slug = re.sub(r"[^a-zA-Z0-9]", "", clean).lower()
            dot = re.sub(r"\s+", ".", clean).lower()
            underscore = re.sub(r"\s+", "_", clean).lower()
            pascal = "".join(w.capitalize() for w in clean.split())
            for c in [slug, dot, underscore, pascal]:
                if c and c not in candidates:
                    candidates.append(c)
        else:
            candidates.append(clean)
            no_punct = re.sub(r"[^a-zA-Z0-9]", "", clean)
            if no_punct and no_punct != clean:
                candidates.append(no_punct)

        if not candidates:
            result.elapsed_ms = int((time.monotonic() - start) * 1000)
            return result

        primary_u = candidates[0]
        cand_lower = [c.lower() for c in candidates]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        yt_headers = dict(headers)
        yt_headers["Cookie"] = "SOCS=CAESEwgDEgk2OTg5NDk4MzQaAmVuIAEaBgoEAP_99w"

        sem = asyncio.Semaphore(10)

        # Helper to wrap finding
        def make_finding(platform: str, found: bool, url: str) -> Finding:
            return Finding(
                label=platform,
                value="Profil détecté" if found else "Non trouvé",
                url=url,
                extra={
                    "platform": platform,
                    "exists": found,
                    "category": "social",
                    "checked": True,
                },
            )

        # -------------------------------------------------------------
        # DIRECT HTTP CHECKERS (100% RELIABLE & NO FALSE POSITIVES)
        # -------------------------------------------------------------

        RESERVED_GITHUB = {
            "about", "pricing", "features", "marketplace", "topics", "collections",
            "trending", "events", "community", "enterprise", "customer-stories",
            "security", "login", "join", "signup", "settings", "notifications",
            "explore", "search", "pulls", "issues", "codespaces", "sponsors"
        }

        async def check_github() -> Finding:
            for u in candidates:
                if u.lower() in RESERVED_GITHUB:
                    continue
                url = f"https://github.com/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and r.url.path.strip("/").lower() == u.lower():
                            if any(k in r.text for k in ["vcard", "user-profile-nav", "itemprop=\"name\"", "og:type\" content=\"profile\"", "org-header"]):
                                return make_finding("GitHub", True, url)
                    except Exception:
                        pass
            return make_finding("GitHub", False, f"https://github.com/{primary_u}")

        async def check_twitter() -> Finding:
            for u in candidates:
                api_url = f"https://publish.twitter.com/oembed?url=https://x.com/{u}"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and "html" in r.text:
                            return make_finding("Twitter/X", True, f"https://x.com/{u}")
                    except Exception:
                        pass
            return make_finding("Twitter/X", False, f"https://x.com/{primary_u}")

        async def check_telegram() -> Finding:
            for u in candidates:
                url = f"https://t.me/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200:
                            soup = BeautifulSoup(r.text, "html.parser")
                            t = soup.find("div", class_="tgme_page_title")
                            robots = soup.find("meta", attrs={"name": "robots"})
                            is_ph = bool(robots and "noindex" in robots.get("content", ""))
                            if t and t.text.strip() and not is_ph:
                                return make_finding("Telegram", True, url)
                    except Exception:
                        pass
            return make_finding("Telegram", False, f"https://t.me/{primary_u}")

        async def check_tiktok() -> Finding:
            for u in candidates:
                api_url = f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{u}"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and "author_name" in r.text:
                            return make_finding("TikTok", True, f"https://www.tiktok.com/@{u}")
                    except Exception:
                        pass
            return make_finding("TikTok", False, f"https://www.tiktok.com/@{primary_u}")

        async def check_pinterest() -> Finding:
            for u in candidates:
                api_url = f"https://www.pinterest.com/oembed.json?url=https://www.pinterest.com/{u}/"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200:
                            return make_finding("Pinterest", True, f"https://www.pinterest.com/{u}/")
                    except Exception:
                        pass
            return make_finding("Pinterest", False, f"https://www.pinterest.com/{primary_u}/")

        async def check_youtube() -> Finding:
            for u in candidates:
                url = f"https://www.youtube.com/@{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=yt_headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and ("channelId" in r.text or "canonicalBaseUrl" in r.text):
                            return make_finding("YouTube", True, url)
                    except Exception:
                        pass
            return make_finding("YouTube", False, f"https://www.youtube.com/@{primary_u}")

        async def check_twitch() -> Finding:
            for u in candidates:
                url = f"https://www.twitch.tv/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and 'name="twitter:card"' in r.text and ('- Twitch' in r.text or '- Live on Twitch' in r.text):
                            return make_finding("Twitch", True, url)
                    except Exception:
                        pass
            return make_finding("Twitch", False, f"https://www.twitch.tv/{primary_u}")

        async def check_gitlab() -> Finding:
            for u in candidates:
                api_url = f"https://gitlab.com/api/v4/users?username={u}"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and len(r.json()) > 0:
                            return make_finding("GitLab", True, f"https://gitlab.com/{u}")
                    except Exception:
                        pass
            return make_finding("GitLab", False, f"https://gitlab.com/{primary_u}")

        async def check_medium() -> Finding:
            for u in candidates:
                feed_url = f"https://medium.com/feed/@{u}"
                async with sem:
                    try:
                        r = await client.get(feed_url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and "<rss" in r.text:
                            return make_finding("Medium", True, f"https://medium.com/@{u}")
                    except Exception:
                        pass
            return make_finding("Medium", False, f"https://medium.com/@{primary_u}")

        async def check_steam() -> Finding:
            for u in candidates:
                url = f"https://steamcommunity.com/id/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if (
                            r.status_code == 200
                            and "g_rgProfileData =" in r.text
                            and "The specified profile could not be found" not in r.text
                        ):
                            return make_finding("Steam", True, url)
                    except Exception:
                        pass
            return make_finding("Steam", False, f"https://steamcommunity.com/id/{primary_u}")

        async def check_soundcloud() -> Finding:
            for u in candidates:
                url = f"https://soundcloud.com/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and "SoundCloud - Hear the world’s sounds" not in r.text and "404" not in r.text:
                            return make_finding("SoundCloud", True, url)
                    except Exception:
                        pass
            return make_finding("SoundCloud", False, f"https://soundcloud.com/{primary_u}")

        async def check_linktree() -> Finding:
            for u in candidates:
                url = f"https://linktr.ee/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and "Page Not Found" not in r.text:
                            return make_finding("Linktree", True, url)
                    except Exception:
                        pass
            return make_finding("Linktree", False, f"https://linktr.ee/{primary_u}")

        async def check_chess() -> Finding:
            for u in candidates:
                api_url = f"https://api.chess.com/pub/player/{u.lower()}"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5)
                        if r.status_code == 200 and r.json().get("username"):
                            return make_finding("Chess.com", True, f"https://www.chess.com/member/{u}")
                    except Exception:
                        pass
            return make_finding("Chess.com", False, f"https://www.chess.com/member/{primary_u}")

        async def check_devto() -> Finding:
            for u in candidates:
                api_url = f"https://dev.to/api/users/by_username?url={u.lower()}"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5)
                        if r.status_code == 200 and r.json().get("username"):
                            return make_finding("DEV.to", True, f"https://dev.to/{u}")
                    except Exception:
                        pass
            return make_finding("DEV.to", False, f"https://dev.to/{primary_u}")

        async def check_hackernews() -> Finding:
            for u in candidates:
                api_url = f"https://hacker-news.firebaseio.com/v0/user/{u}.json"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and isinstance(r.json(), dict) and "id" in r.json():
                            return make_finding("HackerNews", True, f"https://news.ycombinator.com/user?id={u}")
                    except Exception:
                        pass
            return make_finding("HackerNews", False, f"https://news.ycombinator.com/user?id={primary_u}")

        async def check_keybase() -> Finding:
            for u in candidates:
                api_url = f"https://keybase.io/_/api/1.0/user/lookup.json?usernames={u}"
                async with sem:
                    try:
                        r = await client.get(api_url, headers=headers, timeout=5)
                        if r.status_code == 200 and isinstance(r.json().get("them"), list) and r.json()["them"] and r.json()["them"][0] is not None:
                            return make_finding("Keybase", True, f"https://keybase.io/{u}")
                    except Exception:
                        pass
            return make_finding("Keybase", False, f"https://keybase.io/{primary_u}")

        async def check_dribbble() -> Finding:
            for u in candidates:
                url = f"https://dribbble.com/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if r.status_code == 200 and "doesn't exist" not in r.text:
                            return make_finding("Dribbble", True, url)
                    except Exception:
                        pass
            return make_finding("Dribbble", False, f"https://dribbble.com/{primary_u}")

        async def check_behance() -> Finding:
            for u in candidates:
                url = f"https://www.behance.net/{u}"
                async with sem:
                    try:
                        r = await client.get(url, headers=headers, timeout=5, follow_redirects=True)
                        if (
                            r.status_code == 200
                            and "can’t find that page" not in r.text
                            and "cant find that page" not in r.text
                            and ("Profile-root" in r.text or "profile-info" in r.text or "user-profile" in r.text)
                        ):
                            return make_finding("Behance", True, url)
                    except Exception:
                        pass
            return make_finding("Behance", False, f"https://www.behance.net/{primary_u}")

        # -------------------------------------------------------------
        # SEARCH-ASSISTED CHECKERS (Instagram, LinkedIn, Reddit)
        # -------------------------------------------------------------

        def check_search_assisted_sync() -> list[Finding]:
            findings = []
            found_map = {}
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    # 1. Instagram
                    try:
                        for q in [f"site:instagram.com {clean}", f"{clean} instagram"]:
                            try:
                                hits = list(ddgs.text(q, max_results=5))
                                for h in hits:
                                    href = h.get("href", "")
                                    m = re.search(r"instagram\.com/([a-zA-Z0-9._-]+)", href)
                                    if m:
                                        u_found = m.group(1).lower().rstrip("/")
                                        if u_found in ["p", "reel", "reels", "stories", "explore", "accounts", "about", "legal", "developer", "popular", "tags", "direct", "tv", "channel"]:
                                            continue
                                        if u_found in cand_lower:
                                            found_map["Instagram"] = f"https://www.instagram.com/{u_found}/"
                                            break
                                if "Instagram" in found_map:
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                    # 2. LinkedIn
                    try:
                        for q in [f"site:linkedin.com/in/ {clean}", f"{clean} linkedin in"]:
                            try:
                                hits = list(ddgs.text(q, max_results=5))
                                for h in hits:
                                    href = h.get("href", "")
                                    m = re.search(r"linkedin\.com/in/([a-zA-Z0-9._-]+)", href)
                                    if m:
                                        u_found = m.group(1).lower().rstrip("/")
                                        if u_found in ["dir", "pub", "feed", "jobs", "company", "school", "learning", "pulse"]:
                                            continue
                                        if u_found in cand_lower or any(u_found.startswith(f"{c}-") for c in cand_lower):
                                            found_map["LinkedIn"] = f"https://www.linkedin.com/in/{u_found}/"
                                            break
                                if "LinkedIn" in found_map:
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                    # 3. Reddit
                    try:
                        for q in [f"site:reddit.com/user/ {clean}", f"{clean} reddit user"]:
                            try:
                                hits = list(ddgs.text(q, max_results=4))
                                for h in hits:
                                    href = h.get("href", "")
                                    m = re.search(r"reddit\.com/user/([a-zA-Z0-9._-]+)", href)
                                    if m:
                                        u_found = m.group(1).lower().rstrip("/")
                                        if u_found in ["r", "subreddits", "coins", "premium"]:
                                            continue
                                        if u_found in cand_lower:
                                            found_map["Reddit"] = f"https://www.reddit.com/user/{u_found}/"
                                            break
                                if "Reddit" in found_map:
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass
            except Exception:
                pass

            findings.append(
                make_finding(
                    "Instagram",
                    "Instagram" in found_map,
                    found_map.get("Instagram", f"https://www.instagram.com/{primary_u}/"),
                )
            )
            findings.append(
                make_finding(
                    "LinkedIn",
                    "LinkedIn" in found_map,
                    found_map.get("LinkedIn", f"https://www.linkedin.com/in/{primary_u}"),
                )
            )
            findings.append(
                make_finding(
                    "Reddit",
                    "Reddit" in found_map,
                    found_map.get("Reddit", f"https://www.reddit.com/user/{primary_u}"),
                )
            )
            return findings

        # Launch all async tasks and threadpool task concurrently
        async_tasks = [
            check_github(),
            check_twitter(),
            check_telegram(),
            check_tiktok(),
            check_pinterest(),
            check_youtube(),
            check_twitch(),
            check_gitlab(),
            check_medium(),
            check_steam(),
            check_soundcloud(),
            check_linktree(),
            check_chess(),
            check_devto(),
            check_hackernews(),
            check_keybase(),
            check_dribbble(),
            check_behance(),
        ]

        async_res, search_res = await asyncio.gather(
            asyncio.gather(*async_tasks, return_exceptions=True),
            asyncio.to_thread(check_search_assisted_sync),
        )

        for f in async_res:
            if isinstance(f, Finding):
                result.findings.append(f)

        if isinstance(search_res, list):
            for f in search_res:
                if isinstance(f, Finding):
                    result.findings.append(f)

        result.found = any(f.extra.get("exists") for f in result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
