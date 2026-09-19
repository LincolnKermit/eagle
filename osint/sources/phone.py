import time
from urllib.parse import quote

import httpx

from .base import Finding, Result, Source

FRENCH_PREFIX_GEO = {
    "01": {"region": "Île-de-France", "city": "Paris", "lat": 48.8566, "lon": 2.3522, "country_level": False},
    "02": {"region": "Nord-Ouest", "city": "Rennes", "lat": 48.1173, "lon": -1.6778, "country_level": False},
    "03": {"region": "Nord-Est", "city": "Strasbourg", "lat": 48.5734, "lon": 7.7521, "country_level": False},
    "04": {"region": "Sud-Est", "city": "Lyon", "lat": 45.7640, "lon": 4.8357, "country_level": False},
    "05": {"region": "Sud-Ouest", "city": "Toulouse", "lat": 43.6047, "lon": 1.4442, "country_level": False},
    "06": {"region": "France", "city": "", "lat": 46.6033, "lon": 1.8883, "country_level": True},
    "07": {"region": "France", "city": "", "lat": 46.6033, "lon": 1.8883, "country_level": True},
    "09": {"region": "France", "city": "", "lat": 46.6033, "lon": 1.8883, "country_level": True},
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
                country = geocoder.country_name_for_number(num, "fr") or geocoder.description_for_number(num, "fr") or ""
                region = geocoder.description_for_number(num, "fr") or ""
                pays_label = f"{region}, {country}" if region and region != country else (country or "(inconnu)")

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
                result.findings.append(Finding(label="Pays / Région", value=pays_label))
                result.findings.append(Finding(label="Opérateur", value=op or "(inconnu)"))
                result.findings.append(Finding(label="Type", value=line_names.get(line_type, str(line_type))))
                result.findings.append(Finding(label="Fuseaux", value=", ".join(tz)))
                result.findings.append(Finding(label="Format international", value=fmt_intl))
                result.findings.append(Finding(label="Format E.164", value=fmt_e164))

                # Estimate probable location coordinates for map
                city = ""
                is_country_level = True
                loc_name = country or ""
                lat, lon = None, None

                # Check French prefix first
                national_num = str(num.national_number)
                if num.country_code == 33 and len(national_num) >= 9:
                    prefix = "0" + national_num[0]
                    if prefix in FRENCH_PREFIX_GEO:
                        geo_p = FRENCH_PREFIX_GEO[prefix]
                        lat, lon = geo_p["lat"], geo_p["lon"]
                        city = geo_p.get("city", "")
                        is_country_level = geo_p.get("country_level", False)
                        loc_name = f"{city}, {country}" if city and country else (city or country or geo_p["region"])
                elif region and region.lower() != country.lower() and not any(k in region.lower() for k in ["mobile", "national", "cellular"]):
                    city = region
                    is_country_level = False
                    loc_name = f"{city}, {country}" if country else city
                else:
                    is_country_level = True
                    loc_name = country

                # If no regional prefix, check CITY_COORDINATES, then COUNTRY_COORDINATES, then Nominatim
                if lat is None and loc_name:
                    from ..location import CITY_COORDINATES, COUNTRY_COORDINATES
                    city_key = city.lower().strip() if city else ""
                    loc_key = loc_name.lower().strip()
                    country_key = country.lower().strip() if country else ""

                    if city_key and city_key in CITY_COORDINATES:
                        c_info = CITY_COORDINATES[city_key]
                        lat, lon = c_info["lat"], c_info["lon"]
                    elif is_country_level and country_key in COUNTRY_COORDINATES:
                        c_info = COUNTRY_COORDINATES[country_key]
                        lat, lon = c_info["lat"], c_info["lon"]
                    elif loc_key in COUNTRY_COORDINATES:
                        c_info = COUNTRY_COORDINATES[loc_key]
                        lat, lon = c_info["lat"], c_info["lon"]
                    else:
                        try:
                            query_term = city if (city and not is_country_level) else (country or loc_name)
                            r_nom = await client.get(
                                "https://nominatim.openstreetmap.org/search",
                                params={"q": query_term, "format": "json", "limit": 1},
                                headers={"User-Agent": "Eagle-OSINT-Framework/1.0"},
                                timeout=4,
                            )
                            if r_nom.status_code == 200 and r_nom.json():
                                g = r_nom.json()[0]
                                lat, lon = float(g["lat"]), float(g["lon"])
                        except Exception:
                            pass

                if lat is not None and lon is not None:
                    from ..location import COUNTRY_FLAGS
                    country_str = country or loc_name or ""
                    flag = COUNTRY_FLAGS.get(country_str.lower().strip(), "📍")
                    display_loc = f"{flag} {city}, {country}" if city and country else (f"{flag} {loc_name}" if flag != "📍" else loc_name)
                    finding_val = f"{city}, {country}" if city and country else (f"{country} (Zone nationale)" if is_country_level else loc_name)

                    result.findings.append(
                        Finding(
                            label="Localisation probable estimée",
                            value=finding_val,
                            url=f"https://www.google.com/maps/search/?q={lat},{lon}",
                            extra={
                                "country": country or "France",
                                "region": loc_name,
                                "city": city,
                                "is_country_level": is_country_level,
                                "location": display_loc,
                                "flag": flag,
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
