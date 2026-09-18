import re
from typing import Optional

# Country flag emojis
COUNTRY_FLAGS = {
    "france": "🇫🇷",
    "algeria": "🇩🇿",
    "algérie": "🇩🇿",
    "algerie": "🇩🇿",
    "morocco": "🇲🇦",
    "maroc": "🇲🇦",
    "tunisia": "🇹🇳",
    "tunisie": "🇹🇳",
    "united states": "🇺🇸",
    "usa": "🇺🇸",
    "états-unis": "🇺🇸",
    "etats-unis": "🇺🇸",
    "united kingdom": "🇬🇧",
    "uk": "🇬🇧",
    "royaume-uni": "🇬🇧",
    "belgium": "🇧🇪",
    "belgique": "🇧🇪",
    "switzerland": "🇨🇭",
    "suisse": "🇨🇭",
    "germany": "🇩🇪",
    "allemagne": "🇩🇪",
    "canada": "🇨🇦",
    "spain": "🇪🇸",
    "espagne": "🇪🇸",
    "italy": "🇮🇹",
    "italie": "🇮🇹",
    "japan": "🇯🇵",
    "japon": "🇯🇵",
    "united arab emirates": "🇦🇪",
    "uae": "🇦🇪",
    "émirats arabes unis": "🇦🇪",
    "netherlands": "🇳🇱",
    "pays-bas": "🇳🇱",
    "brazil": "🇧🇷",
    "brésil": "🇧🇷",
    "portugal": "🇵🇹",
    "senegal": "🇸🇳",
    "sénégal": "🇸🇳",
    "turkey": "🇹🇷",
    "turquie": "🇹🇷",
    "mexico": "🇲🇽",
    "mexique": "🇲🇽",
    "australia": "🇦🇺",
    "australie": "🇦🇺",
    "india": "🇮🇳",
    "inde": "🇮🇳",
    "china": "🇨🇳",
    "chine": "🇨🇳",
    "russia": "🇷🇺",
    "russie": "🇷🇺",
    "côte d'ivoire": "🇨🇮",
    "cote d'ivoire": "🇨🇮",
    "ivory coast": "🇨🇮",
    "cameroon": "🇨🇲",
    "cameroun": "🇨🇲",
    "egypt": "🇪🇬",
    "égypte": "🇪🇬",
    "egypte": "🇪🇬",
}

# Pre-compiled database of common French & International cities with coordinates
CITY_COORDINATES = {
    # French major cities
    "lyon": {"city": "Lyon", "country": "France", "flag": "🇫🇷", "lat": 45.764043, "lon": 4.835659},
    "villeurbanne": {"city": "Villeurbanne", "country": "France", "flag": "🇫🇷", "lat": 45.771944, "lon": 4.890278},
    "paris": {"city": "Paris", "country": "France", "flag": "🇫🇷", "lat": 48.856614, "lon": 2.3522219},
    "marseille": {"city": "Marseille", "country": "France", "flag": "🇫🇷", "lat": 43.296482, "lon": 5.36978},
    "toulouse": {"city": "Toulouse", "country": "France", "flag": "🇫🇷", "lat": 43.604652, "lon": 1.444209},
    "nice": {"city": "Nice", "country": "France", "flag": "🇫🇷", "lat": 43.710173, "lon": 7.261953},
    "nantes": {"city": "Nantes", "country": "France", "flag": "🇫🇷", "lat": 47.218371, "lon": -1.553621},
    "strasbourg": {"city": "Strasbourg", "country": "France", "flag": "🇫🇷", "lat": 48.573405, "lon": 7.752111},
    "montpellier": {"city": "Montpellier", "country": "France", "flag": "🇫🇷", "lat": 43.610769, "lon": 3.876716},
    "bordeaux": {"city": "Bordeaux", "country": "France", "flag": "🇫🇷", "lat": 44.837789, "lon": -0.57918},
    "lille": {"city": "Lille", "country": "France", "flag": "🇫🇷", "lat": 50.62925, "lon": 3.057256},
    "rennes": {"city": "Rennes", "country": "France", "flag": "🇫🇷", "lat": 48.117266, "lon": -1.677793},
    "reims": {"city": "Reims", "country": "France", "flag": "🇫🇷", "lat": 49.258329, "lon": 4.031696},
    "saint-etienne": {"city": "Saint-Étienne", "country": "France", "flag": "🇫🇷", "lat": 45.439695, "lon": 4.387178},
    "saint-étienne": {"city": "Saint-Étienne", "country": "France", "flag": "🇫🇷", "lat": 45.439695, "lon": 4.387178},
    "toulon": {"city": "Toulon", "country": "France", "flag": "🇫🇷", "lat": 43.124228, "lon": 5.928364},
    "grenoble": {"city": "Grenoble", "country": "France", "flag": "🇫🇷", "lat": 45.188529, "lon": 5.724524},
    "dijon": {"city": "Dijon", "country": "France", "flag": "🇫🇷", "lat": 47.322047, "lon": 5.04148},
    "angers": {"city": "Angers", "country": "France", "flag": "🇫🇷", "lat": 47.478419, "lon": -0.563166},
    "nimes": {"city": "Nîmes", "country": "France", "flag": "🇫🇷", "lat": 43.836699, "lon": 4.360054},
    "nîmes": {"city": "Nîmes", "country": "France", "flag": "🇫🇷", "lat": 43.836699, "lon": 4.360054},
    "clermont-ferrand": {"city": "Clermont-Ferrand", "country": "France", "flag": "🇫🇷", "lat": 45.777222, "lon": 3.087025},
    "le mans": {"city": "Le Mans", "country": "France", "flag": "🇫🇷", "lat": 48.00611, "lon": 0.199556},
    "aix-en-provence": {"city": "Aix-en-Provence", "country": "France", "flag": "🇫🇷", "lat": 43.529742, "lon": 5.447427},
    "brest": {"city": "Brest", "country": "France", "flag": "🇫🇷", "lat": 48.390394, "lon": -4.486076},
    "tours": {"city": "Tours", "country": "France", "flag": "🇫🇷", "lat": 47.394144, "lon": 0.68484},
    "amiens": {"city": "Amiens", "country": "France", "flag": "🇫🇷", "lat": 49.894067, "lon": 2.295753},
    "limoges": {"city": "Limoges", "country": "France", "flag": "🇫🇷", "lat": 45.833619, "lon": 1.261105},
    "annecy": {"city": "Annecy", "country": "France", "flag": "🇫🇷", "lat": 45.899247, "lon": 6.129384},
    "perpignan": {"city": "Perpignan", "country": "France", "flag": "🇫🇷", "lat": 42.688659, "lon": 2.894833},
    "boulogne-billancourt": {"city": "Boulogne-Billancourt", "country": "France", "flag": "🇫🇷", "lat": 48.839695, "lon": 2.239913},
    "metz": {"city": "Metz", "country": "France", "flag": "🇫🇷", "lat": 49.119308, "lon": 6.175716},
    "besancon": {"city": "Besançon", "country": "France", "flag": "🇫🇷", "lat": 47.237829, "lon": 6.024054},
    "besançon": {"city": "Besançon", "country": "France", "flag": "🇫🇷", "lat": 47.237829, "lon": 6.024054},
    "rouen": {"city": "Rouen", "country": "France", "flag": "🇫🇷", "lat": 49.443232, "lon": 1.099971},
    "caen": {"city": "Caen", "country": "France", "flag": "🇫🇷", "lat": 49.182863, "lon": -0.370679},
    "mulhouse": {"city": "Mulhouse", "country": "France", "flag": "🇫🇷", "lat": 47.750839, "lon": 7.335888},
    "nancy": {"city": "Nancy", "country": "France", "flag": "🇫🇷", "lat": 48.692054, "lon": 6.184417},

    # International hubs
    "london": {"city": "London", "country": "United Kingdom", "flag": "🇬🇧", "lat": 51.507351, "lon": -0.127758},
    "bruxelles": {"city": "Bruxelles", "country": "Belgium", "flag": "🇧🇪", "lat": 50.850346, "lon": 4.351721},
    "brussels": {"city": "Brussels", "country": "Belgium", "flag": "🇧🇪", "lat": 50.850346, "lon": 4.351721},
    "geneve": {"city": "Genève", "country": "Switzerland", "flag": "🇨🇭", "lat": 46.204391, "lon": 6.143158},
    "geneva": {"city": "Geneva", "country": "Switzerland", "flag": "🇨🇭", "lat": 46.204391, "lon": 6.143158},
    "new york": {"city": "New York", "country": "United States", "flag": "🇺🇸", "lat": 40.712776, "lon": -74.005974},
    "san francisco": {"city": "San Francisco", "country": "United States", "flag": "🇺🇸", "lat": 37.774929, "lon": -122.419416},
    "montreal": {"city": "Montréal", "country": "Canada", "flag": "🇨🇦", "lat": 45.501689, "lon": -73.567256},
    "berlin": {"city": "Berlin", "country": "Germany", "flag": "🇩🇪", "lat": 52.520007, "lon": 13.404954},
    "tokyo": {"city": "Tokyo", "country": "Japan", "flag": "🇯🇵", "lat": 35.676192, "lon": 139.650311},
    "alger": {"city": "Alger", "country": "Algeria", "flag": "🇩🇿", "lat": 36.753768, "lon": 3.058778},
    "algiers": {"city": "Algiers", "country": "Algeria", "flag": "🇩🇿", "lat": 36.753768, "lon": 3.058778},
    "casablanca": {"city": "Casablanca", "country": "Morocco", "flag": "🇲🇦", "lat": 33.57311, "lon": -7.589843},
    "tunis": {"city": "Tunis", "country": "Tunisia", "flag": "🇹🇳", "lat": 36.806495, "lon": 10.181532},
    "dubai": {"city": "Dubai", "country": "United Arab Emirates", "flag": "🇦🇪", "lat": 25.204849, "lon": 55.270783},
}

# Regex to match location phrases like "Lieu : Lyon", "à Lyon", "#Lyon", "académie de Lyon", etc.
LOCATION_PATTERNS = [
    re.compile(r"(?:lieu|location|ville|city|résidant à|habite à|situé à)\s*[:\-]?\s*([a-zA-ZÀ-ÿ\s\-]+)", re.I),
    re.compile(r"(?:à|in|at|sur|de|#)\s+([a-zA-ZÀ-ÿ\-]+)", re.I),
    re.compile(r"(?:académie de|iut|université de|lycée)\s+([a-zA-ZÀ-ÿ\-]+)", re.I),
]


# Pre-compiled database of country center coordinates and flags
COUNTRY_COORDINATES = {
    "france": {"country": "France", "flag": "🇫🇷", "lat": 46.603354, "lon": 1.888334},
    "algeria": {"country": "Algérie", "flag": "🇩🇿", "lat": 28.033886, "lon": 1.659626},
    "algérie": {"country": "Algérie", "flag": "🇩🇿", "lat": 28.033886, "lon": 1.659626},
    "algerie": {"country": "Algérie", "flag": "🇩🇿", "lat": 28.033886, "lon": 1.659626},
    "morocco": {"country": "Maroc", "flag": "🇲🇦", "lat": 31.791702, "lon": -7.09262},
    "maroc": {"country": "Maroc", "flag": "🇲🇦", "lat": 31.791702, "lon": -7.09262},
    "tunisia": {"country": "Tunisie", "flag": "🇹🇳", "lat": 33.886917, "lon": 9.537499},
    "tunisie": {"country": "Tunisie", "flag": "🇹🇳", "lat": 33.886917, "lon": 9.537499},
    "united states": {"country": "États-Unis", "flag": "🇺🇸", "lat": 37.09024, "lon": -95.712891},
    "usa": {"country": "États-Unis", "flag": "🇺🇸", "lat": 37.09024, "lon": -95.712891},
    "états-unis": {"country": "États-Unis", "flag": "🇺🇸", "lat": 37.09024, "lon": -95.712891},
    "etats-unis": {"country": "États-Unis", "flag": "🇺🇸", "lat": 37.09024, "lon": -95.712891},
    "united kingdom": {"country": "Royaume-Uni", "flag": "🇬🇧", "lat": 55.378051, "lon": -3.435973},
    "uk": {"country": "Royaume-Uni", "flag": "🇬🇧", "lat": 55.378051, "lon": -3.435973},
    "royaume-uni": {"country": "Royaume-Uni", "flag": "🇬🇧", "lat": 55.378051, "lon": -3.435973},
    "belgium": {"country": "Belgique", "flag": "🇧🇪", "lat": 50.503887, "lon": 4.469936},
    "belgique": {"country": "Belgique", "flag": "🇧🇪", "lat": 50.503887, "lon": 4.469936},
    "switzerland": {"country": "Suisse", "flag": "🇨🇭", "lat": 46.818188, "lon": 8.227512},
    "suisse": {"country": "Suisse", "flag": "🇨🇭", "lat": 46.818188, "lon": 8.227512},
    "germany": {"country": "Allemagne", "flag": "🇩🇪", "lat": 51.165691, "lon": 10.451526},
    "allemagne": {"country": "Allemagne", "flag": "🇩🇪", "lat": 51.165691, "lon": 10.451526},
    "canada": {"country": "Canada", "flag": "🇨🇦", "lat": 56.130366, "lon": -106.346771},
    "spain": {"country": "Espagne", "flag": "🇪🇸", "lat": 40.463667, "lon": -3.74922},
    "espagne": {"country": "Espagne", "flag": "🇪🇸", "lat": 40.463667, "lon": -3.74922},
    "italy": {"country": "Italie", "flag": "🇮🇹", "lat": 41.87194, "lon": 12.56738},
    "italie": {"country": "Italie", "flag": "🇮🇹", "lat": 41.87194, "lon": 12.56738},
    "japan": {"country": "Japon", "flag": "🇯🇵", "lat": 36.204824, "lon": 138.252924},
    "japon": {"country": "Japon", "flag": "🇯🇵", "lat": 36.204824, "lon": 138.252924},
    "united arab emirates": {"country": "Émirats Arabes Unis", "flag": "🇦🇪", "lat": 23.424076, "lon": 53.847818},
    "uae": {"country": "Émirats Arabes Unis", "flag": "🇦🇪", "lat": 23.424076, "lon": 53.847818},
    "émirats arabes unis": {"country": "Émirats Arabes Unis", "flag": "🇦🇪", "lat": 23.424076, "lon": 53.847818},
    "netherlands": {"country": "Pays-Bas", "flag": "🇳🇱", "lat": 52.132633, "lon": 5.291266},
    "pays-bas": {"country": "Pays-Bas", "flag": "🇳🇱", "lat": 52.132633, "lon": 5.291266},
    "brazil": {"country": "Brésil", "flag": "🇧🇷", "lat": -14.235004, "lon": -51.92528},
    "brésil": {"country": "Brésil", "flag": "🇧🇷", "lat": -14.235004, "lon": -51.92528},
    "portugal": {"country": "Portugal", "flag": "🇵🇹", "lat": 39.399872, "lon": -8.224454},
    "senegal": {"country": "Sénégal", "flag": "🇸🇳", "lat": 14.497401, "lon": -14.452362},
    "sénégal": {"country": "Sénégal", "flag": "🇸🇳", "lat": 14.497401, "lon": -14.452362},
    "turkey": {"country": "Turquie", "flag": "🇹🇷", "lat": 38.963745, "lon": 35.243322},
    "turquie": {"country": "Turquie", "flag": "🇹🇷", "lat": 38.963745, "lon": 35.243322},
    "mexico": {"country": "Mexique", "flag": "🇲🇽", "lat": 23.634501, "lon": -102.552784},
    "mexique": {"country": "Mexique", "flag": "🇲🇽", "lat": 23.634501, "lon": -102.552784},
    "australia": {"country": "Australie", "flag": "🇦🇺", "lat": -25.274398, "lon": 133.775136},
    "australie": {"country": "Australie", "flag": "🇦🇺", "lat": -25.274398, "lon": 133.775136},
    "india": {"country": "Inde", "flag": "🇮🇳", "lat": 20.593684, "lon": 78.96288},
    "inde": {"country": "Inde", "flag": "🇮🇳", "lat": 20.593684, "lon": 78.96288},
    "china": {"country": "Chine", "flag": "🇨🇳", "lat": 35.86166, "lon": 104.195397},
    "chine": {"country": "Chine", "flag": "🇨🇳", "lat": 35.86166, "lon": 104.195397},
    "russia": {"country": "Russie", "flag": "🇷🇺", "lat": 61.52401, "lon": 105.318756},
    "russie": {"country": "Russie", "flag": "🇷🇺", "lat": 61.52401, "lon": 105.318756},
    "côte d'ivoire": {"country": "Côte d'Ivoire", "flag": "🇨🇮", "lat": 7.539989, "lon": -5.54708},
    "cote d'ivoire": {"country": "Côte d'Ivoire", "flag": "🇨🇮", "lat": 7.539989, "lon": -5.54708},
    "ivory coast": {"country": "Côte d'Ivoire", "flag": "🇨🇮", "lat": 7.539989, "lon": -5.54708},
    "cameroon": {"country": "Cameroun", "flag": "🇨🇲", "lat": 7.369722, "lon": 12.354722},
    "cameroun": {"country": "Cameroun", "flag": "🇨🇲", "lat": 7.369722, "lon": 12.354722},
    "egypt": {"country": "Égypte", "flag": "🇪🇬", "lat": 26.820553, "lon": 30.802498},
    "égypte": {"country": "Égypte", "flag": "🇪🇬", "lat": 26.820553, "lon": 30.802498},
    "egypte": {"country": "Égypte", "flag": "🇪🇬", "lat": 26.820553, "lon": 30.802498},
}


def detect_location_in_text(text: str) -> Optional[dict]:
    """Scan text for explicit city names, hashtags, country names or location patterns."""
    if not text:
        return None

    text_lower = text.lower()

    # 1. Check direct matches for known city names (with word boundaries)
    sorted_cities = sorted(CITY_COORDINATES.keys(), key=len, reverse=True)
    for city_key in sorted_cities:
        pattern = rf"(?:\b|#){re.escape(city_key)}(?:\b|\s)"
        if re.search(pattern, text_lower):
            info = CITY_COORDINATES[city_key]
            flag = info.get("flag", "📍")
            return {
                "city": info["city"],
                "country": info["country"],
                "flag": flag,
                "location": f"{flag} {info['city']}, {info['country']}",
                "latitude": info["lat"],
                "longitude": info["lon"],
            }

    # 2. Check location regex patterns
    for pat in LOCATION_PATTERNS:
        match = pat.search(text)
        if match:
            candidate = match.group(1).strip().lower()
            candidate = re.sub(r"[^\w\s\-]", "", candidate).strip()
            if candidate in CITY_COORDINATES:
                info = CITY_COORDINATES[candidate]
                flag = info.get("flag", "📍")
                return {
                    "city": info["city"],
                    "country": info["country"],
                    "flag": flag,
                    "location": f"{flag} {info['city']}, {info['country']}",
                    "latitude": info["lat"],
                    "longitude": info["lon"],
                }
            elif candidate in COUNTRY_COORDINATES:
                info = COUNTRY_COORDINATES[candidate]
                flag = info.get("flag", "📍")
                return {
                    "city": "",
                    "country": info["country"],
                    "flag": flag,
                    "location": f"{flag} {info['country']}",
                    "latitude": info["lat"],
                    "longitude": info["lon"],
                }

    # 3. Check direct matches for country names when no city is found
    sorted_countries = sorted(COUNTRY_COORDINATES.keys(), key=len, reverse=True)
    for c_key in sorted_countries:
        pattern = rf"(?:\b|#){re.escape(c_key)}(?:\b|\s)"
        if re.search(pattern, text_lower):
            info = COUNTRY_COORDINATES[c_key]
            flag = info.get("flag", "📍")
            return {
                "city": "",
                "country": info["country"],
                "flag": flag,
                "location": f"{flag} {info['country']}",
                "latitude": info["lat"],
                "longitude": info["lon"],
            }

    return None
