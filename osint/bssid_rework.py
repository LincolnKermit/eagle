import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import httpx


async def geolocate_open(client: httpx.AsyncClient, bssid: str) -> Optional[dict]:
    """Query open-source Wi-Fi geolocation (Mylnikov API) + OpenStreetMap reverse geocoding."""
    clean_bssid = bssid.strip().replace("-", ":").lower()
    try:
        r = await client.get(
            "https://api.mylnikov.org/geolocation/wifi",
            params={"v": "1.1", "data": "open", "bssid": clean_bssid},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        payload = r.json()
        if payload.get("result") != 200:
            return None
        data = payload.get("data", {})
        lat = data.get("lat")
        lon = data.get("lon")
        acc = data.get("range", 0)
        if lat is None or lon is None:
            return None

        # Reverse geocoding via OpenStreetMap
        address = None
        try:
            r_osm = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"format": "json", "lat": str(lat), "lon": str(lon)},
                headers={"User-Agent": "Eagle-OSINT-Framework/1.0"},
                timeout=6,
            )
            if r_osm.status_code == 200:
                address = r_osm.json().get("display_name")
        except Exception:
            pass

        return {
            "latitude": lat,
            "longitude": lon,
            "accuracy": acc,
            "address": address or "(address unavailable)",
            "google_maps": f"https://www.google.com/maps/search/?q={lat},{lon}",
        }
    except Exception as e:
        print(f"[-] Geolocation error: {e}", file=sys.stderr)
        return None


async def main(
    bssid: str,
    as_client: Optional[httpx.AsyncClient] = None,
    json_file: Optional[Path] = None,
):
    close_client = False
    if not as_client:
        as_client = httpx.AsyncClient(timeout=15, follow_redirects=True)
        close_client = True

    try:
        # Check vendor first
        clean_bssid = bssid.strip().replace("-", ":").lower()
        vendor = None
        try:
            r_v = await as_client.get(f"https://api.macvendors.com/{clean_bssid}")
            if r_v.status_code == 200 and r_v.text.strip():
                vendor = r_v.text.strip()
        except Exception:
            pass

        print(f"[*] Analyzing BSSID: {clean_bssid}")
        if vendor:
            print(f"[+] Vendor (OUI): {vendor}")

        # Attempt GHunt if available
        loc = None
        try:
            from ghunt.apis.geolocation import GeolocationHttp
            from ghunt.helpers import auth

            ghunt_creds = await auth.load_and_auth(as_client)
            geo_api = GeolocationHttp(ghunt_creds)
            found, resp = await geo_api.geolocate(as_client, bssid=clean_bssid)
            if found:
                loc = {
                    "latitude": resp.location.latitude,
                    "longitude": resp.location.longitude,
                    "accuracy": resp.accuracy,
                    "address": "(via GHunt)",
                    "google_maps": f"https://www.google.com/maps/search/?q={resp.location.latitude},{resp.location.longitude}",
                }
        except Exception:
            pass

        # Fallback to open Wi-Fi DB
        if not loc:
            loc = await geolocate_open(as_client, clean_bssid)

        if not loc:
            print("[-] Location not found in open databases.")
            print(f"[*] You can manually check: https://wigle.net/search?netid={clean_bssid}")
        else:
            print("📍 Location found!")
            print(f"🛣️  Accuracy: ~{loc['accuracy']}m")
            print(f"🌐 Latitude:  {loc['latitude']}")
            print(f"🌐 Longitude: {loc['longitude']}")
            print(f"🏠 Address:   {loc['address']}")
            print(f"🗺️  Maps:      {loc['google_maps']}")

        if json_file and loc:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(loc, f, indent=4)
            print(f"[+] Output written to {json_file}")

    finally:
        if close_client:
            await as_client.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eagle BSSID Locator")
    parser.add_argument("bssid", help="Target BSSID / MAC address (e.g. 00:14:22:01:23:45)")
    parser.add_argument("--json", dest="json_file", type=Path, default=None, help="JSON output file")
    args = parser.parse_args()

    asyncio.run(main(args.bssid, json_file=args.json_file))
