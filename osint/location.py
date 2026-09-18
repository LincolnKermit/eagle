import re
from typing import Optional

# Pre-compiled database of common French & International cities with coordinates
CITY_COORDINATES = {
    # French major cities
    "lyon": {"city": "Lyon", "country": "France", "lat": 45.764043, "lon": 4.835659},
    "villeurbanne": {"city": "Villeurbanne", "country": "France", "lat": 45.771944, "lon": 4.890278},
    "paris": {"city": "Paris", "country": "France", "lat": 48.856614, "lon": 2.3522219},
    "marseille": {"city": "Marseille", "country": "France", "lat": 43.296482, "lon": 5.36978},
    "toulouse": {"city": "Toulouse", "country": "France", "lat": 43.604652, "lon": 1.444209},
    "nice": {"city": "Nice", "country": "France", "lat": 43.710173, "lon": 7.261953},
    "nantes": {"city": "Nantes", "country": "France", "lat": 47.218371, "lon": -1.553621},
    "strasbourg": {"city": "Strasbourg", "country": "France", "lat": 48.573405, "lon": 7.752111},
    "montpellier": {"city": "Montpellier", "country": "France", "lat": 43.610769, "lon": 3.876716},
    "bordeaux": {"city": "Bordeaux", "country": "France", "lat": 44.837789, "lon": -0.57918},
    "lille": {"city": "Lille", "country": "France", "lat": 50.62925, "lon": 3.057256},
    "rennes": {"city": "Rennes", "country": "France", "lat": 48.117266, "lon": -1.677793},
    "reims": {"city": "Reims", "country": "France", "lat": 49.258329, "lon": 4.031696},
    "saint-etienne": {"city": "Saint-Étienne", "country": "France", "lat": 45.439695, "lon": 4.387178},
    "saint-étienne": {"city": "Saint-Étienne", "country": "France", "lat": 45.439695, "lon": 4.387178},
    "toulon": {"city": "Toulon", "country": "France", "lat": 43.124228, "lon": 5.928364},
    "grenoble": {"city": "Grenoble", "country": "France", "lat": 45.188529, "lon": 5.724524},
    "dijon": {"city": "Dijon", "country": "France", "lat": 47.322047, "lon": 5.04148},
    "angers": {"city": "Angers", "country": "France", "lat": 47.478419, "lon": -0.563166},
    "nimes": {"city": "Nîmes", "country": "France", "lat": 43.836699, "lon": 4.360054},
    "nîmes": {"city": "Nîmes", "country": "France", "lat": 43.836699, "lon": 4.360054},
    "clermont-ferrand": {"city": "Clermont-Ferrand", "country": "France", "lat": 45.777222, "lon": 3.087025},
    "le mans": {"city": "Le Mans", "country": "France", "lat": 48.00611, "lon": 0.199556},
    "aix-en-provence": {"city": "Aix-en-Provence", "country": "France", "lat": 43.529742, "lon": 5.447427},
    "brest": {"city": "Brest", "country": "France", "lat": 48.390394, "lon": -4.486076},
    "tours": {"city": "Tours", "country": "France", "lat": 47.394144, "lon": 0.68484},
    "amiens": {"city": "Amiens", "country": "France", "lat": 49.894067, "lon": 2.295753},
    "limoges": {"city": "Limoges", "country": "France", "lat": 45.833619, "lon": 1.261105},
    "annecy": {"city": "Annecy", "country": "France", "lat": 45.899247, "lon": 6.129384},
    "perpignan": {"city": "Perpignan", "country": "France", "lat": 42.688659, "lon": 2.894833},
    "boulogne-billancourt": {"city": "Boulogne-Billancourt", "country": "France", "lat": 48.839695, "lon": 2.239913},
    "metz": {"city": "Metz", "country": "France", "lat": 49.119308, "lon": 6.175716},
    "besancon": {"city": "Besançon", "country": "France", "lat": 47.237829, "lon": 6.024054},
    "besançon": {"city": "Besançon", "country": "France", "lat": 47.237829, "lon": 6.024054},
    "rouen": {"city": "Rouen", "country": "France", "lat": 49.443232, "lon": 1.099971},
    "caen": {"city": "Caen", "country": "France", "lat": 49.182863, "lon": -0.370679},
    "mulhouse": {"city": "Mulhouse", "country": "France", "lat": 47.750839, "lon": 7.335888},
    "nancy": {"city": "Nancy", "country": "France", "lat": 48.692054, "lon": 6.184417},

    # International hubs
    "london": {"city": "London", "country": "United Kingdom", "lat": 51.507351, "lon": -0.127758},
    "bruxelles": {"city": "Bruxelles", "country": "Belgium", "lat": 50.850346, "lon": 4.351721},
    "brussels": {"city": "Brussels", "country": "Belgium", "lat": 50.850346, "lon": 4.351721},
    "geneve": {"city": "Genève", "country": "Switzerland", "lat": 46.204391, "lon": 6.143158},
    "geneva": {"city": "Geneva", "country": "Switzerland", "lat": 46.204391, "lon": 6.143158},
    "new york": {"city": "New York", "country": "United States", "lat": 40.712776, "lon": -74.005974},
    "san francisco": {"city": "San Francisco", "country": "United States", "lat": 37.774929, "lon": -122.419416},
    "montreal": {"city": "Montréal", "country": "Canada", "lat": 45.501689, "lon": -73.567256},
    "berlin": {"city": "Berlin", "country": "Germany", "lat": 52.520007, "lon": 13.404954},
    "tokyo": {"city": "Tokyo", "country": "Japan", "lat": 35.676192, "lon": 139.650311},
    "alger": {"city": "Alger", "country": "Algeria", "lat": 36.753768, "lon": 3.058778},
    "algiers": {"city": "Algiers", "country": "Algeria", "lat": 36.753768, "lon": 3.058778},
    "casablanca": {"city": "Casablanca", "country": "Morocco", "lat": 33.57311, "lon": -7.589843},
    "tunis": {"city": "Tunis", "country": "Tunisia", "lat": 36.806495, "lon": 10.181532},
    "dubai": {"city": "Dubai", "country": "United Arab Emirates", "lat": 25.204849, "lon": 55.270783},
}

# Regex to match location phrases like "Lieu : Lyon", "à Lyon", "#Lyon", "académie de Lyon", etc.
LOCATION_PATTERNS = [
    re.compile(r"(?:lieu|location|ville|city|résidant à|habite à|situé à)\s*[:\-]?\s*([a-zA-ZÀ-ÿ\s\-]+)", re.I),
    re.compile(r"(?:à|in|at|sur|de|#)\s+([a-zA-ZÀ-ÿ\-]+)", re.I),
    re.compile(r"(?:académie de|iut|université de|lycée)\s+([a-zA-ZÀ-ÿ\-]+)", re.I),
]


def detect_location_in_text(text: str) -> Optional[dict]:
    """Scan text for explicit city names, hashtags or location patterns."""
    if not text:
        return None

    text_lower = text.lower()

    # 1. Check direct matches for known city names (with word boundaries)
    # Order by longest name first to avoid partial matches
    sorted_cities = sorted(CITY_COORDINATES.keys(), key=len, reverse=True)
    for city_key in sorted_cities:
        pattern = rf"(?:\b|#){re.escape(city_key)}(?:\b|\s)"
        if re.search(pattern, text_lower):
            info = CITY_COORDINATES[city_key]
            return {
                "city": info["city"],
                "country": info["country"],
                "location": f"{info['city']}, {info['country']}",
                "latitude": info["lat"],
                "longitude": info["lon"],
            }

    # 2. Check location regex patterns
    for pat in LOCATION_PATTERNS:
        match = pat.search(text)
        if match:
            candidate = match.group(1).strip().lower()
            # Clean punctuation
            candidate = re.sub(r"[^\w\s\-]", "", candidate).strip()
            if candidate in CITY_COORDINATES:
                info = CITY_COORDINATES[candidate]
                return {
                    "city": info["city"],
                    "country": info["country"],
                    "location": f"{info['city']}, {info['country']}",
                    "latitude": info["lat"],
                    "longitude": info["lon"],
                }

    return None
