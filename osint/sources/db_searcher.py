import os
import time
from urllib.parse import quote

import httpx

from .base import Finding, Result, Source


class DBSearcherSource(Source):
    name = "db_searcher"
    description = "Recherche de fuites de données, info-stealers et HaveIBeenPwned."
    input_types = ("email", "username", "person")

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean = target.strip()
        is_email = "@" in clean

        # 1. LeakCheck public API
        try:
            r = await client.get(
                "https://leakcheck.io/api/public",
                params={"check": clean},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success") and data.get("sources"):
                    sources = data.get("sources", [])
                    breach_names = [s.get("name") for s in sources if s.get("name")]
                    result.found = True
                    result.findings.append(
                        Finding(
                            label=f"Fuites de données (LeakCheck - {len(sources)} sources)",
                            value=", ".join(breach_names[:10]) + ("..." if len(breach_names) > 10 else ""),
                            url="https://leakcheck.io/",
                            extra={
                                "total_sources": len(sources),
                                "breaches_list": breach_names[:30],
                            },
                        )
                    )
        except Exception:
            pass

        # 2. Hudson Rock Cavalier Free OSINT API
        try:
            hr_url = (
                "https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email"
                if is_email
                else "https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-username"
            )
            param_key = "email" if is_email else "username"

            r_hr = await client.get(hr_url, params={param_key: clean}, timeout=10)
            if r_hr.status_code == 200:
                hr_data = r_hr.json()
                stealers = hr_data.get("stealers") or []
                if stealers:
                    result.found = True
                    total_user = hr_data.get("total_user_services", 0)
                    total_corp = hr_data.get("total_corporate_services", 0)
                    dates = [s.get("date_compromised") for s in stealers if s.get("date_compromised")]
                    result.findings.append(
                        Finding(
                            label="Info-Stealer Malware (Hudson Rock)",
                            value=f"{len(stealers)} infection(s) détectée(s) · {total_user} identifiants utilisateur compromis",
                            url="https://www.hudsonrock.com/free-tools",
                            extra={
                                "infections_count": len(stealers),
                                "compromised_user_services": total_user,
                                "compromised_corporate_services": total_corp,
                                "recent_dates": dates[:5],
                            },
                        )
                    )
        except Exception:
            pass

        # 3. Have I Been Pwned (HIBP)
        hibp_api_key = os.getenv("HIBP_API_KEY")
        if is_email and hibp_api_key:
            try:
                r_hibp = await client.get(
                    f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(clean)}",
                    params={"truncateResponse": "false"},
                    headers={
                        "hibp-api-key": hibp_api_key,
                        "user-agent": "Eagle-OSINT-Framework",
                    },
                    timeout=8,
                )
                if r_hibp.status_code == 200:
                    breaches = r_hibp.json()
                    breach_titles = [b.get("Title") for b in breaches if b.get("Title")]
                    result.found = True
                    result.findings.append(
                        Finding(
                            label=f"Have I Been Pwned ({len(breaches)} brèches confirmées)",
                            value=", ".join(breach_titles[:10]),
                            url=f"https://haveibeenpwned.com/account/{clean}",
                            extra={
                                "breaches_count": len(breaches),
                                "breaches": breach_titles[:25],
                            },
                        )
                    )
                elif r_hibp.status_code == 404:
                    pass  # No breach found
            except Exception:
                pass
        elif is_email:
            # Provide direct HIBP lookup link if no commercial API key configured
            result.findings.append(
                Finding(
                    label="Have I Been Pwned (Vérification manuelle)",
                    value=f"Consulter les brèches répertoriées pour {clean} sur haveibeenpwned.com",
                    url=f"https://haveibeenpwned.com/account/{quote(clean)}",
                    extra={"notice": "Définir HIBP_API_KEY pour l'interrogation automatique de l'API v3"},
                )
            )
            result.found = True

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
