import html
import re

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

# Actor Apify per la raccolta LinkedIn (02-specifiche-tecniche-v3.md §5.3).
# Non è un segreto: il token di autenticazione, quello sì, viene letto da
# variabile d'ambiente (settings.APIFY_API_TOKEN), mai cablato nell'URL.
APIFY_ACTOR = "cheap_scraper~linkedin-job-scraper"
APIFY_RUN_SYNC_URL = (
    f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"
)

# Endpoint pubblico non autenticato usato solo per l'import manuale di un
# singolo job (Sprint 24): evita di passare da Apify — con i suoi tempi
# variabili (§5.2) e il consumo di credito — per recuperare i dettagli di
# un link già noto. Verificato senza rate-limiting apprezzabile su richieste
# ripetute; nessuna chiave richiesta.
LINKEDIN_GUEST_JOB_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"
LINKEDIN_GUEST_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
LINKEDIN_GUEST_TIMEOUT_SECONDS = 15

# Il tempo di risposta della chiamata sincrona a questo actor è molto
# variabile sotto carico (osservato tra ~10s e oltre 60s per lo stesso
# identico payload): un timeout di 60s con zero retry falliva l'intero ciclo
# notturno in modo intermittente. Timeout più ampio + un retry riducono il
# fallimento a un evento raro senza introdurre una libreria di retry esterna.
REQUEST_TIMEOUT_SECONDS = 180
MAX_ATTEMPTS = 2


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
            response = self._post_with_retry(payload)
            items.extend(response.json())
        return [self._normalize_item(item) for item in items]

    def fetch_by_url(self, url):
        """Recupera i dettagli di una singola offerta a partire dal suo link
        (import manuale, Sprint 14) con una richiesta diretta a LinkedIn,
        senza passare da Apify (Sprint 24 — vedi nota sull'endpoint guest
        sopra). Ritorna `None` se il job non esiste più o il link non è
        riconoscibile."""
        job_id = self._extract_job_id(url)
        if job_id is None:
            return None

        try:
            response = requests.get(
                LINKEDIN_GUEST_JOB_URL.format(id=job_id),
                headers={"User-Agent": LINKEDIN_GUEST_USER_AGENT},
                timeout=LINKEDIN_GUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None

        return self._parse_guest_posting(response.text, url, job_id)

    def _extract_job_id(self, url):
        match = re.search(r"/jobs/view/(?:[\w-]*-)?(?P<id>\d+)", url or "")
        return match.group("id") if match else None

    def _parse_guest_posting(self, page_html, url, job_id):
        title = self._extract_tag_text(
            page_html, r'class="[^"]*topcard__title[^"]*">(.*?)</h2>'
        )
        company = self._extract_tag_text(
            page_html, r'topcard__org-name-link[^>]*>(.*?)</a>'
        )
        location = self._extract_tag_text(
            page_html, r'class="topcard__flavor topcard__flavor--bullet">(.*?)</span>'
        )
        description = self._extract_description(page_html)

        if not title or not description:
            return None

        return {
            "external_id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "apply_url": url,
            "published_at": None,
            "salary": "",
            "matched_search": "",
        }

    def _extract_tag_text(self, page_html, pattern):
        match = re.search(pattern, page_html, re.S)
        if not match:
            return ""
        return html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()

    def _extract_description(self, page_html):
        match = re.search(
            r'show-more-less-html__markup[^"]*">(.*?)</div>', page_html, re.S
        )
        if not match:
            return ""
        text = match.group(1)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</li>", "\n", text)
        text = re.sub(r"<li[^>]*>", "- ", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _post_with_retry(self, payload):
        last_error = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = requests.post(
                    APIFY_RUN_SYNC_URL,
                    headers={"Authorization": f"Bearer {settings.APIFY_API_TOKEN}"},
                    json=payload,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
        raise last_error

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
            "published_at": self._parse_published_at(
                item.get("publishedAt") or item.get("postedAt")
            ),
            "salary": item.get("salary") or "",
            "matched_search": item.get("searchString") or "",
        }

    def _parse_published_at(self, raw_value):
        """Converte la data restituita da Apify in un `datetime` prima che
        arrivi a `Job.objects.create()`: assegnata in memoria (senza refresh
        dal DB), una stringa grezza farebbe fallire con AttributeError il
        confronto per data più recente nel tie-break del cap di intake
        (`apps.jobs.intake.apply_intake_cap`), perdendo l'intera raccolta
        della notte per l'utente colpito — bug osservato in produzione."""
        if not isinstance(raw_value, str):
            return None
        return parse_datetime(raw_value)
