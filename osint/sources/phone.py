import time
from urllib.parse import quote

import httpx

from .base import Finding, Result, Source

FRENCH_PREFIX_GEO = {
    "01": {"region": "Île-de-France (Paris)", "lat": 48.8566, "lon": 2.3522},
    "02": {"region": "Nord-Ouest (Bretagne, Normandie, Pays de la Loire)", "lat": 48.1173, "lon": -1.6778},
    "03": {"region": "Nord-Est (Grand Est, Hauts-de-France, Bourgogne)", "lat": 48.5734, "lon": 7.7521},
    "04": {"region": "Sud-Est (Auvergne-Rhône-Alpes, PACA, Corse)", "lat": 45.7640, "lon": 4.8357},
    "05": {"region": "Sud-Ouest (Nouvelle-Aquitaine, Occitanie)", "lat": 43.6047, "lon": 1.4442},
    "06": {"region": "Mobile France (National)", "lat": 46.6033, "lon": 1.8883},
    "07": {"region": "Mobile France (National)", "lat": 46.6033, "lon": 1.8883},
    "09": {"region": "VoIP / Ligne IP France", "lat": 46.6033, "lon": 1.8883},
}


class PhoneInfoSource(Source):
    name = "phone_info"
    description = "Validation, pays, opérateur, fuseau horaire et géolocalisation estimée."
    input_types = ("phone",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        try:
            import phonenumbers
            from phonenumbers import carrier, geocoder, timezone

            num = None
            try:
                num = phonenumbers.parse(target, None)
            except phonenumbers.NumberParseException:
                if target.strip().startswith("0"):
                    try:
                        num = phonenumbers.parse(target, "FR")
                    except Exception:
                        pass

            if not num or not phonenumbers.is_valid_number(num):
                result.error = "Numéro invalide ou format non reconnu (essayez avec indicatif, ex: +33...)."
            else:
                country = geocoder.description_for_number(num, "fr")
                op = carrier.name_for_number(num, "fr")
                tz = timezone.time_zones_for_number(num)
                fmt_intl = phonenumbers.format_number(
                    num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
                fmt_e164 = phonenumbers.format_number(
                    num, phonenumbers.PhoneNumberFormat.E164
                )
                line_type = phonenumbers.number_type(num)
                line_names = {
                    0: "FIXED_LINE", 1: "MOBILE", 2: "FIXED_LINE_OR_MOBILE",
                    3: "TOLL_FREE", 4: "PREMIUM_RATE", 5: "SHARED_COST",
                    6: "VOIP", 7: "PERSONAL_NUMBER", 8: "PAGER",
                    9: "UAN", 10: "UNKNOWN", 27: "EMERGENCY",
                }
                result.found = True
                result.findings.append(Finding(label="Pays / Région", value=country or "(inconnu)"))
                result.findings.append(Finding(label="Opérateur", value=op or "(inconnu)"))
                result.findings.append(Finding(label="Type", value=line_names.get(line_type, str(line_type))))
                result.findings.append(Finding(label="Fuseaux", value=", ".join(tz)))
                result.findings.append(Finding(label="Format international", value=fmt_intl))
                result.findings.append(Finding(label="Format E.164", value=fmt_e164))

                # Estimate probable location coordinates for map
                loc_name = country or ""
                lat, lon = None, None

                # Check French prefix first
                national_num = str(num.national_number)
                if num.country_code == 33 and len(national_num) >= 9:
                    prefix = "0" + national_num[0]
                    if prefix in FRENCH_PREFIX_GEO:
                        geo_p = FRENCH_PREFIX_GEO[prefix]
                        lat, lon = geo_p["lat"], geo_p["lon"]
                        loc_name = geo_p["region"]

                # If no regional prefix, geocode country or city via Nominatim
                if lat is None and loc_name:
                    try:
                        r_nom = await client.get(
                            "https://nominatim.openstreetmap.org/search",
                            params={"q": loc_name, "format": "json", "limit": 1},
                            headers={"User-Agent": "Eagle-OSINT-Framework/1.0"},
                            timeout=4,
                        )
                        if r_nom.status_code == 200 and r_nom.json():
                            g = r_nom.json()[0]
                            lat, lon = float(g["lat"]), float(g["lon"])
                    except Exception:
                        pass

                if lat is not None and lon is not None:
                    result.findings.append(
                        Finding(
                            label="Localisation probable estimée",
                            value=f"{loc_name} ({lat}, {lon})",
                            url=f"https://www.google.com/maps/search/?q={lat},{lon}",
                            extra={
                                "region": loc_name,
                                "latitude": lat,
                                "longitude": lon,
                                "source": "phonenumbers + geocoding",
                            },
                        )
                    )

        except ImportError:
            result.error = "phonenumbers non installé."
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
