import time
from urllib.parse import quote

import httpx

from .base import Finding, Result, Source


class ArchiveSource(Source):
    name = "archive_org"
    description = "Internet Archive & Wayback Machine (historique et snapshots archivés)."
    input_types = ("domain", "username", "email", "person")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        clean = target.strip()
        result = Result(source=self.name, target=target, found=False)

        headers = {
            "User-Agent": "Eagle-OSINT-Framework/1.0",
            "Accept": "application/json",
        }

        # 1. If target is a domain or URL, query Wayback Availability API
        is_domain = "." in clean and " " not in clean and "@" not in clean
        is_email = "@" in clean

        if is_domain:
            target_url = clean if clean.startswith("http") else f"https://{clean}"
            try:
                r = await client.get(
                    "https://archive.org/wayback/available",
                    params={"url": target_url},
                    headers=headers,
                    timeout=5,
                )
                if r.status_code == 200:
                    data = r.json()
                    snapshots = data.get("archived_snapshots", {})
                    closest = snapshots.get("closest")
                    if closest and closest.get("available"):
                        result.found = True
                        timestamp = closest.get("timestamp", "")
                        formatted_date = (
                            f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                            if len(timestamp) >= 8
                            else timestamp
                        )
                        result.findings.append(
                            Finding(
                                label="Dernière capture Wayback Machine",
                                value=f"Capture disponible au {formatted_date} (Code HTTP: {closest.get('status')})",
                                url=closest.get("url"),
                                extra={
                                    "timestamp": timestamp,
                                    "status": closest.get("status"),
                                    "original_url": target_url,
                                },
                            )
                        )
            except Exception:
                pass

            # Always add full timeline link for domain
            timeline_url = f"https://web.archive.org/web/*/{clean}"
            result.findings.append(
                Finding(
                    label="Chronologie complète (Wayback Machine)",
                    value=f"Explorer toutes les versions archivées de {clean}",
                    url=timeline_url,
                )
            )
            result.found = True

        elif is_email:
            # For email: check domain part
            _, _, domain = clean.partition("@")
            result.findings.append(
                Finding(
                    label="Recherche textuelle Internet Archive",
                    value=f"Rechercher les occurrences de l'adresse email dans les archives publiques",
                    url=f"https://archive.org/search.php?query={quote(clean)}",
                )
            )
            if domain:
                result.findings.append(
                    Finding(
                        label=f"Archive du fournisseur ({domain})",
                        value=f"Consulter les snapshots du domaine @{domain}",
                        url=f"https://web.archive.org/web/*/{domain}",
                    )
                )
            result.found = True

        else:
            # Username / Person query
            archive_search_url = f"https://archive.org/search.php?query={quote(clean)}"
            result.findings.append(
                Finding(
                    label="Collections & Textes Internet Archive",
                    value=f"Recherche dans les collections ouvertes et documents d'archive : {clean}",
                    url=archive_search_url,
                )
            )

            # Social profile archives for username
            if " " not in clean:
                for platform, base in [
                    ("X / Twitter", f"https://web.archive.org/web/*/twitter.com/{clean}*"),
                    ("GitHub", f"https://web.archive.org/web/*/github.com/{clean}*"),
                    ("Instagram", f"https://web.archive.org/web/*/instagram.com/{clean}*"),
                ]:
                    result.findings.append(
                        Finding(
                            label=f"Profil archivé {platform}",
                            value=f"Historique Wayback Machine pour @{clean} sur {platform}",
                            url=base,
                        )
                    )

            result.found = True

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
