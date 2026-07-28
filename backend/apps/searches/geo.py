import requests
from django.core.cache import cache

# Nominatim (OpenStreetMap): servizio di geocoding gratuito senza chiave API
# (Sprint 23 — autocomplete città/paese sulle ricerche salvate). La policy di
# uso richiede uno User-Agent identificativo e un limite di 1 richiesta/
# secondo per IP: qui non c'è throttling esplicito perché il proxy è chiamato
# solo da un autocomplete con debounce lato frontend, e la cache assorbe le
# query ripetute (stesso termine digitato più volte da utenti diversi).
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "AppApply/1.0 (assistente di ricerca lavoro)"
CACHE_TTL_SECONDS = 60 * 60


def search_cities(query):
    """Suggerimenti città per l'autocomplete delle ricerche salvate.

    Ritorna una lista di dict `{"city": ..., "country": ...}`, deduplicata
    per coppia città/paese (Nominatim può restituire più risultati per lo
    stesso nome a livelli amministrativi diversi — city/state/county)."""
    query = (query or "").strip()
    if len(query) < 2:
        return []

    cache_key = f"geo:cities:{query.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    response = requests.get(
        NOMINATIM_SEARCH_URL,
        params={
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 8,
            "accept-language": "en",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()

    results = []
    seen = set()
    for item in response.json():
        address = item.get("address", {})
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
        )
        country = address.get("country")
        if not city or not country:
            continue
        key = (city, country)
        if key in seen:
            continue
        seen.add(key)
        results.append({"city": city, "country": country})

    cache.set(cache_key, results, CACHE_TTL_SECONDS)
    return results
