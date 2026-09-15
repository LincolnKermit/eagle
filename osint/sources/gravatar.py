import hashlib
import time

import httpx

from .base import Finding, Result, Source


class GravatarSource(Source):
    name = "gravatar"
    description = "Gravatar public profile lookup by email hash."
    input_types = ("email",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        target_norm = target.strip().lower()
        h = hashlib.md5(target_norm.encode()).hexdigest()
        try:
            r = await client.get(f"https://gravatar.com/{h}.json")
            if r.status_code == 200:
                data = r.json()
                entries = data.get("entry") or []
                if entries:
                    entry = entries[0]
                    result.found = True
                    accounts = [a.get("url") for a in entry.get("accounts", []) if a.get("url")]
                    result.findings.append(
                        Finding(
                            label="Profile",
                            value=entry.get("displayName")
                            or entry.get("preferredUsername")
                            or "(unnamed)",
                            url=entry.get("profileUrl"),
                            extra={
                                "avatar": f"https://gravatar.com/avatar/{h}?s=200",
                                "about": entry.get("aboutMe"),
                                "location": entry.get("currentLocation"),
                                "linked_accounts": accounts,
                            },
                        )
                    )
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
