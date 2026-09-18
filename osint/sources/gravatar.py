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
        sha256_hash = hashlib.sha256(target_norm.encode()).hexdigest()
        md5_hash = hashlib.md5(target_norm.encode()).hexdigest()

        try:
            # 1. Probe avatar existence (200 = registered, 404 = none)
            has_avatar = False
            avatar_url = f"https://gravatar.com/avatar/{sha256_hash}?s=200"
            r_av = await client.get(f"https://gravatar.com/avatar/{sha256_hash}?d=404")
            if r_av.status_code == 200:
                has_avatar = True
            else:
                r_av_md5 = await client.get(f"https://gravatar.com/avatar/{md5_hash}?d=404")
                if r_av_md5.status_code == 200:
                    has_avatar = True
                    avatar_url = f"https://gravatar.com/avatar/{md5_hash}?s=200"

            # 2. Attempt profile fetch (v3 or legacy)
            profile_data = None
            try:
                r_v3 = await client.get(f"https://api.gravatar.com/v3/profiles/{sha256_hash}")
                if r_v3.status_code == 200:
                    profile_data = r_v3.json()
            except Exception:
                pass

            if not profile_data:
                try:
                    r_legacy = await client.get(f"https://gravatar.com/{md5_hash}.json")
                    if r_legacy.status_code == 200:
                        entries = r_legacy.json().get("entry") or []
                        if entries:
                            profile_data = entries[0]
                except Exception:
                    pass

            if profile_data:
                result.found = True
                display_name = (
                    profile_data.get("display_name")
                    or profile_data.get("displayName")
                    or profile_data.get("preferredUsername")
                    or target
                )
                profile_url = profile_data.get("profile_url") or profile_data.get("profileUrl") or f"https://gravatar.com/{sha256_hash}"
                accounts = [
                    a.get("url")
                    for a in (profile_data.get("verified_accounts") or profile_data.get("accounts") or [])
                    if isinstance(a, dict) and a.get("url")
                ]
                result.findings.append(
                    Finding(
                        label="Profile Gravatar",
                        value=display_name,
                        url=profile_url,
                        extra={
                            "avatar": avatar_url,
                            "about": profile_data.get("description") or profile_data.get("aboutMe"),
                            "location": profile_data.get("location") or profile_data.get("currentLocation"),
                            "job": profile_data.get("job_title"),
                            "company": profile_data.get("company"),
                            "linked_accounts": accounts,
                        },
                    )
                )
            elif has_avatar:
                result.found = True
                result.findings.append(
                    Finding(
                        label="Avatar Gravatar",
                        value="Avatar public actif détecté",
                        url=f"https://gravatar.com/{sha256_hash}",
                        extra={
                            "avatar": avatar_url,
                            "sha256": sha256_hash,
                            "md5": md5_hash,
                        },
                    )
                )
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
