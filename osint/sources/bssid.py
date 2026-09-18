import time
from urllib.parse import quote

import httpx

from .base import Finding, Result, Source


class BssidSource(Source):
    name = "bssid_info"
    description = "Résolution fabricant OUI + géolocalisation Wi-Fi (Mylnikov, OSM)."
    input_types = ("bssid",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        clean_mac = target.strip().replace("-", ":").lower()

        # 1. Vendor / OUI lookup
        vendor = None
        try:
            r_vendor = await client.get(f"https://api.macvendors.com/{clean_mac}", timeout=5)
            if r_vendor.status_code == 200 and r_vendor.text.strip():
                vendor = r_vendor.text.strip()
            else:
                r_co = await client.get(f"https://macvendors.co/api/{clean_mac}", timeout=5)
                if r_co.status_code == 200:
                    data = r_co.json()
                    vendor = (data.get("result") or {}).get("company")
        except Exception:
            pass

        if vendor:
            result.found = True
            result.findings.append(
                Finding(
                    label="Fabricant (OUI)",
                    value=vendor,
                    url=f"https://macvendors.com/?query={quote(clean_mac)}",
                )
            )

        # 2. Geolocation via open Wi-Fi DB (Mylnikov)
        try:
            r_geo = await client.get(
                "https://api.mylnikov.org/geolocation/wifi",
                params={"v": "1.1", "data": "open", "bssid": clean_mac},
                timeout=8,
            )
            if r_geo.status_code == 200:
                geo_json = r_geo.json()
                if geo_json.get("result") == 200:
                    geo_data = geo_json.get("data", {})
                    lat = geo_data.get("lat")
                    lon = geo_data.get("lon")
                    accuracy = geo_data.get("range", 0)

                    if lat is not None and lon is not None:
                        result.found = True
                        maps_url = f"https://www.google.com/maps/search/?q={lat},{lon}"
                        osm_url = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}"

                        # Reverse geocoding via Nominatim
                        address = None
                        nom_country = None
                        nom_city = None
                        flag = "📍"
                        try:
                            headers = {"User-Agent": "Eagle-OSINT-Framework/1.0"}
                            r_nom = await client.get(
                                "https://nominatim.openstreetmap.org/reverse",
                                params={"format": "json", "lat": str(lat), "lon": str(lon), "addressdetails": 1},
                                headers=headers,
                                timeout=6,
                            )
                            if r_nom.status_code == 200:
                                nom_data = r_nom.json()
                                address = nom_data.get("display_name")
                                addr_obj = nom_data.get("address", {})
                                nom_country = addr_obj.get("country")
                                nom_city = addr_obj.get("city") or addr_obj.get("town") or addr_obj.get("village") or addr_obj.get("municipality")
                                from ..location import COUNTRY_FLAGS
                                if nom_country:
                                    flag = COUNTRY_FLAGS.get(nom_country.lower().strip(), "📍")
                        except Exception:
                            pass

                        display_loc = (
                            f"{nom_city}, {nom_country}" if nom_city and nom_country
                            else (nom_country or nom_city or address or "")
                        )
                        if flag != "📍" and display_loc:
                            display_loc = f"{flag} {display_loc}"

                        result.findings.append(
                            Finding(
                                label="Coordonnées GPS",
                                value=f"Lat: {lat}, Lon: {lon} (précision ~{accuracy}m)",
                                url=maps_url,
                                extra={
                                    "latitude": lat,
                                    "longitude": lon,
                                    "country": nom_country or "",
                                    "city": nom_city or "",
                                    "flag": flag,
                                    "location": display_loc,
                                    "accuracy": f"{accuracy}m",
                                    "osm_url": osm_url,
                                },
                            )
                        )

                        if address:
                            result.findings.append(
                                Finding(
                                    label="Adresse estimée",
                                    value=address,
                                    url=maps_url,
                                )
                            )
        except Exception:
            pass

        # 3. WiGLE cross-reference link
        wigle_url = f"https://wigle.net/search?netid={quote(clean_mac)}"
        result.findings.append(
            Finding(
                label="Base WiGLE",
                value=f"Rechercher le BSSID {clean_mac} sur wigle.net",
                url=wigle_url,
            )
        )
        result.found = True

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
