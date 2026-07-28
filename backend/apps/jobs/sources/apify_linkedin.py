import requests
from django.conf import settings

# Actor Apify per la raccolta LinkedIn (02-specifiche-tecniche-v3.md §5.3).
# Non è un segreto: il token di autenticazione, quello sì, viene letto da
# variabile d'ambiente (settings.APIFY_API_TOKEN), mai cablato nell'URL.
APIFY_ACTOR = "cheap_scraper~linkedin-job-scraper"
APIFY_RUN_SYNC_URL = (
    f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"
)


class ApifyLinkedInSource:
    """Fonte offerte LinkedIn via Apify.

    Implementa l'interfaccia attesa da `apps.jobs.collection`: `fetch(searches,
    window_hours, limit)` → lista di dict normalizzati (`external_id`, `title`,
    `company`, `location`, `description`, `apply_url`, `published_at`, `salary`).
    """

    def fetch(self, searches, window_hours, limit):
        items = []
        for search in searches:
            payload = {
                "keyword": [search.keywords],
                "location": f"{search.city}, {search.country}",
                "publishedAt": self._published_at_filter(window_hours),
            }
            response = requests.post(
                APIFY_RUN_SYNC_URL,
                headers={"Authorization": f"Bearer {settings.APIFY_API_TOKEN}"},
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            items.extend(response.json())
        return [self._normalize_item(item) for item in items]

    def fetch_by_url(self, url):
        """Recupera i dettagli di una singola offerta a partire dal suo link
        (import manuale, Sprint 14). Ritorna `None` se non viene restituito
        alcun risultato."""
        response = requests.post(
            APIFY_RUN_SYNC_URL,
            headers={"Authorization": f"Bearer {settings.APIFY_API_TOKEN}"},
            json={"startUrls": [{"url": url}]},
            timeout=60,
        )
        response.raise_for_status()
        items = response.json()
        return self._normalize_item(items[0]) if items else None

    def _published_at_filter(self, window_hours):
        """Mappa la finestra oraria richiesta sull'enum `publishedAt`
        dell'actor (solo 24h/7g/30g disponibili — 02-specifiche-tecniche-v3.md
        §5.3 richiede una finestra di 24h, coperta da "r86400")."""
        if window_hours <= 24:
            return "r86400"
        if window_hours <= 24 * 7:
            return "r604800"
        return "r2592000"

    def _normalize_item(self, item):
        return {
            "external_id": str(item.get("id") or item.get("jobId") or ""),
            "title": item.get("title") or item.get("jobTitle") or "",
            "company": item.get("company") or item.get("companyName") or "",
            "location": item.get("location") or "",
            "description": item.get("description") or item.get("jobDescription") or "",
            "apply_url": item.get("applyUrl") or item.get("jobUrl") or item.get("link") or "",
            "published_at": item.get("publishedAt") or item.get("postedAt"),
            "salary": item.get("salary") or "",
            "matched_search": item.get("searchString") or "",
        }
