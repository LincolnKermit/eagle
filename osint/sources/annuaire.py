import re
import time
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from .base import Finding, Result, Source

# Regional coordinates for French geographic phone prefixes
FRENCH_PREFIX_GEO = {
    "01": {"region": "Île-de-France / Paris", "lat": 48.8566, "lon": 2.3522},
    "02": {"region": "Nord-Ouest (Bretagne, Normandie, Pays de la Loire, Centre)", "lat": 48.1173, "lon": -1.6778},
    "03": {"region": "Nord-Est (Grand Est, Hauts-de-France, Bourgogne)", "lat": 48.5734, "lon": 7.7521},
    "04": {"region": "Sud-Est (Auvergne-Rhône-Alpes, PACA, Corse)", "lat": 45.7640, "lon": 4.8357},
    "05": {"region": "Sud-Ouest (Nouvelle-Aquitaine, Occitanie)", "lat": 43.6047, "lon": 1.4442},
    "06": {"region": "Mobile France (National)", "lat": 46.6033, "lon": 1.8883},
    "07": {"region": "Mobile France (National)", "lat": 46.6033, "lon": 1.8883},
    "09": {"region": "VoIP / Ligne IP France (Non-géographique)", "lat": 46.6033, "lon": 1.8883},
}


class AnnuaireSource(Source):
    name = "annuaire_118712"
    description = "Annuaire téléphonique et répertoire public 118 712 & PagesBlanches."
    input_types = ("phone", "person", "username")

    BASE_URL = "https://www.118712.fr/recherche"

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        clean = target.strip()
        result = Result(source=self.name, target=target, found=False)

        search_url = f"{self.BASE_URL}?s={quote(clean)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        # Check for geographic prefix if target looks like a French phone number
        digits = re.sub(r"\D", "", clean)
        french_local = None
        if digits.startswith("33") and len(digits) >= 11:
            french_local = "0" + digits[2:11]
        elif digits.startswith("0") and len(digits) >= 10:
            french_local = digits[:10]

        geo_info = None
        if french_local:
            prefix = french_local[:2]
            if prefix in FRENCH_PREFIX_GEO:
                geo_info = FRENCH_PREFIX_GEO[prefix]

        try:
            r = await client.get(search_url, headers=headers, timeout=8)
            if r.status_code == 200 and "challenge" not in r.text.lower():
                soup = BeautifulSoup(r.text, "lxml")
                # Look for result cards
                items = soup.select(".item, .resultat, .block-item, .vcard")
                for item in items[:5]:
                    name_el = item.select_one(".titre, .nom, h2, h3, .fn")
                    addr_el = item.select_one(".adresse, .address, .street-address")
                    tel_el = item.select_one(".tel, .telephone, .phone")

                    name = name_el.get_text(strip=True) if name_el else "Résultat 118 712"
                    addr = addr_el.get_text(" ", strip=True) if addr_el else ""
                    tel = tel_el.get_text(strip=True) if tel_el else ""

                    extra = {}
                    if addr:
                        extra["adresse"] = addr
                    if tel:
                        extra["telephone"] = tel

                    # Attempt Nominatim geocoding if address is found
                    if addr:
                        try:
                            r_geo = await client.get(
                                "https://nominatim.openstreetmap.org/search",
                                params={"q": addr, "format": "json", "limit": 1},
                                headers={"User-Agent": "Eagle-OSINT-Framework/1.0"},
                                timeout=4,
                            )
                            if r_geo.status_code == 200 and r_geo.json():
                                geo = r_geo.json()[0]
                                extra["latitude"] = float(geo["lat"])
                                extra["longitude"] = float(geo["lon"])
                        except Exception:
                            pass

                    result.findings.append(
                        Finding(
                            label=name,
                            value=f"{tel} · {addr}".strip(" · "),
                            url=search_url,
                            extra=extra,
                        )
                    )

            # If automated scraping is blocked by anti-bot/WAF (standard for 118 712 / PagesJaunes)
            # or no items were parsed, provide structured query access and zone intel
            if not result.findings:
                extra = {
                    "source": "118712.fr",
                    "type_recherche": "Inversée (téléphone)" if french_local else "Nom / Particulier",
                }
                if geo_info:
                    extra["zone_geographique"] = geo_info["region"]
                    extra["latitude"] = geo_info["lat"]
                    extra["longitude"] = geo_info["lon"]

                result.findings.append(
                    Finding(
                        label="Annuaire 118 712 (Portail France)",
                        value=(
                            f"Lien de recherche directe sur l'annuaire 118 712"
                            + (f" [Zone estimée : {geo_info['region']}]" if geo_info else "")
                        ),
                        url=search_url,
                        extra=extra,
                    )
                )

                # Also add PagesBlanches / PagesJaunes reference link
                pages_url = f"https://www.pagesjaunes.fr/pagesblanches/recherche?quoiqui={quote(clean)}"
                result.findings.append(
                    Finding(
                        label="PagesBlanches (Alternative France)",
                        value=f"Recherche annuaire particuliers sur PagesBlanches : {clean}",
                        url=pages_url,
                        extra={"notice": "Protection Cloudflare/WAF active sur les annuaires FR — accès direct navigateur recommandé"},
                    )
                )

            result.found = bool(result.findings)
        except Exception as e:
            result.error = str(e)

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
