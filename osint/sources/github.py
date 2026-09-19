import time

import httpx
from bs4 import BeautifulSoup

from .base import Finding, Result, Source

RESERVED_GITHUB = {
    "about", "pricing", "features", "marketplace", "topics", "collections",
    "trending", "events", "community", "enterprise", "customer-stories",
    "security", "login", "join", "signup", "settings", "notifications",
    "explore", "search", "pulls", "issues", "codespaces", "sponsors"
}


class GitHubUsernameSource(Source):
    name = "github"
    description = "Vérifie l'existence d'un profil GitHub (scraping)."
    input_types = ("username", "person")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip()
        if " " in clean:
            import re
            clean = re.sub(r"[^a-zA-Z0-9]", "", clean).lower()
        if not clean or clean.lower() in RESERVED_GITHUB:
            result.elapsed_ms = int((time.monotonic() - start) * 1000)
            return result
        url = f"https://github.com/{clean}"
        try:
            r = await client.get(url)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                name_el = soup.select_one("span.p-name")
                bio_el = soup.select_one("div.user-profile-bio")
                org_el = soup.select_one("li[itemprop='worksFor']")
                loc_el = soup.select_one("li[itemprop='homeLocation']")
                avatar = soup.select_one("img.avatar-user")
                has_profile = bool(
                    avatar
                    or name_el
                    or soup.select_one(".vcard-names")
                    or soup.select_one(".user-profile-nav")
                    or soup.select_one("div.org-header")
                )
                if has_profile:
                    result.found = True
                    result.findings.append(
                        Finding(
                            label=name_el.get_text(strip=True) if name_el else target,
                            value=(bio_el.get_text(strip=True) if bio_el else "(no bio)"),
                            url=url,
                            extra={
                                "avatar": avatar["src"] if avatar and avatar.get("src") else None,
                                "company": org_el.get_text(strip=True) if org_el else None,
                                "location": loc_el.get_text(strip=True) if loc_el else None,
                            },
                        )
                    )
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
