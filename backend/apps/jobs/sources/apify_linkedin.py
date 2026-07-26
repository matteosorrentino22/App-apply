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
                "keywords": search.keywords,
                "location": search.location,
                "hours_old": window_hours,
                "rows": limit,
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
            json={"startUrls": [{"url": url}], "rows": 1},
            timeout=60,
        )
        response.raise_for_status()
        items = response.json()
        return self._normalize_item(items[0]) if items else None

    def _normalize_item(self, item):
        return {
            "external_id": str(item.get("id") or item.get("jobId") or ""),
            "title": item.get("title") or "",
            "company": item.get("company") or item.get("companyName") or "",
            "location": item.get("location") or "",
            "description": item.get("description") or "",
            "apply_url": item.get("applyUrl") or item.get("jobUrl") or item.get("link") or "",
            "published_at": item.get("publishedAt") or item.get("postedAt"),
            "salary": item.get("salary") or "",
        }
