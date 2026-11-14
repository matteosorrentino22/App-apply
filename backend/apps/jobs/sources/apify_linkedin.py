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

# 150 è il minimo consentito dall'actor quando si usa la fatturazione
# pay-per-result (sotto quella soglia il campo verrebbe comunque forzato a
# 150 dall'actor stesso): è quindi anche il valore più economico possibile,
# usato su ogni chiamata per limitare la spesa (sprint-39).
MAX_ITEMS_PER_CALL = 150

# Per le ricerche di tipo Company, `keyword` resta un termine neutro fisso
# invece dei nomi azienda: verificato con chiamate reali (2026-08-15) che
# metterci anche i nomi azienda fa scattare la ricerca semantica di LinkedIn,
# che aggira `companyInclude` e torna aziende non pertinenti (solo ~25% dei
# risultati erano dell'azienda cercata — lo stesso identico problema di
# sprint-23 "Bug 2"). Con keyword neutro, `companyInclude` filtra al 100%.
# Due termini invece di uno solo per un recall leggermente migliore (testato:
# "jobs" da solo 37 risultati, "jobs"+"hiring" uniti 38, entrambi al 100% di
# pertinenza) — l'actor unisce i risultati dei singoli termini deduplicando.
COMPANY_SEARCH_KEYWORDS = ["jobs", "hiring"]


class ApifyLinkedInSource:
    """Fonte offerte LinkedIn via Apify.

    Implementa l'interfaccia attesa da `apps.jobs.collection`: `fetch(searches,
    window_hours, limit)` → lista di dict normalizzati (`external_id`, `title`,
    `company`, `location`, `description`, `apply_url`, `published_at`, `salary`,
    `applicants_count`, `applicants_bucket`, `recruiter_name`,
    `recruiter_profile_url`).
    """

    def fetch(self, searches, window_hours, limit):
        """Tutte le offerte di tutti i gruppi; solleva l'errore del primo
        gruppo fallito. La raccolta usa `fetch_groups`, che invece isola gli
        errori per gruppo."""
        offers = []
        for group in self.fetch_groups(searches, window_hours):
            if group["error"] is not None:
                raise group["error"]
            offers.extend(group["offers"])
        return offers

    def fetch_groups(self, searches, window_hours):
        """Una chiamata per gruppo (tipo × città × paese). Un errore su un
        gruppo non fa perdere gli altri (Sprint 68): ogni elemento del
        risultato è `{"label", "offers", "error"}`, con `error` = eccezione
        del gruppo fallito (dopo i retry) e `offers` vuota in quel caso.
        Ogni offerta porta `saved_search_id`, la ricerca del gruppo che l'ha
        prodotta quando è individuabile (None altrimenti)."""
        results = []
        for group in self._group_by_type_and_location(searches):
            label = f"{group['search_type']} · {group['city']}, {group['country']}"
            try:
                offers = self._fetch_group(group, window_hours)
            except Exception as exc:
                results.append({"label": label, "offers": [], "error": exc})
                continue
            results.append({"label": label, "offers": offers, "error": None})
        return results

    def _fetch_group(self, group, window_hours):
        company_names = [search.keywords for search in group["searches"]]
        is_company = group["search_type"] == "company"
        payload = {
            "keyword": COMPANY_SEARCH_KEYWORDS if is_company else company_names,
            "location": f"{group['city']}, {group['country']}",
            "publishedAt": self._published_at_filter(window_hours),
            "maxItems": MAX_ITEMS_PER_CALL,
            "saveOnlyUniqueItems": True,
        }
        if is_company:
            payload["companyInclude"] = company_names
        response = self._post_with_retry(payload)
        raw_items = response.json()
        if is_company:
            # `searchString` varrebbe qui "jobs"/"hiring" (il keyword
            # neutro), non il nome azienda: sovrascritto con l'azienda
            # reale del job (già garantita da `companyInclude`) prima
            # della normalizzazione, così `matched_search` resta utile.
            for item in raw_items:
                item["searchString"] = item.get("companyName") or item.get("company") or ""
        offers = []
        for item in raw_items:
            offer = self._normalize_item(item)
            offer["saved_search_id"] = self._attribute_to_search(group, offer["matched_search"])
            offers.append(offer)
        return offers

    def _attribute_to_search(self, group, matched_search):
        """Ricerca del gruppo che ha prodotto l'offerta: confronto con
        l'etichetta restituita dall'actor (Company: nome azienda; Job role:
        "<keywords> - <città>, <paese>"), senza distinzione di maiuscole; con
        una sola ricerca nel gruppo è per forza quella."""
        searches = group["searches"]
        label = (matched_search or "").casefold()
        for search in searches:
            if group["search_type"] == "company":
                expected = search.keywords
            else:
                expected = f"{search.keywords} - {search.city}, {search.country}"
            if expected.casefold() == label:
                return search.pk
        if len(searches) == 1:
            return searches[0].pk
        return None

    def _group_by_type_and_location(self, searches):
        """Raggruppa le ricerche per (tipo, città, paese): una chiamata per
        gruppo invece di una per ricerca, per risparmiare sul costo Apify
        (sprint-39). Le ricerche con città/paese diversi restano in gruppi
        (quindi chiamate) separati anche se dello stesso tipo."""
        groups = {}
        for search in searches:
            key = (search.search_type, search.city, search.country)
            if key not in groups:
                groups[key] = {
                    "search_type": search.search_type,
                    "city": search.city,
                    "country": search.country,
                    "searches": [],
                }
            groups[key]["searches"].append(search)
        return list(groups.values())

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
            # La pagina guest pubblica di LinkedIn non mostra né il numero di
            # candidati né chi ha pubblicato l'annuncio (info riservate agli
            # utenti loggati): dato semplicemente non disponibile per import
            # da link, a differenza della raccolta via actor Apify.
            "applicants_count": None,
            "applicants_bucket": "",
            "recruiter_name": "",
            "recruiter_profile_url": "",
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
        applicants_count, applicants_bucket = self._parse_applicants_count(
            item.get("applicationsCount")
        )
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
            "applicants_count": applicants_count,
            "applicants_bucket": applicants_bucket,
            "recruiter_name": item.get("posterFullName") or "",
            "recruiter_profile_url": item.get("posterProfileUrl") or "",
        }

    def _parse_applicants_count(self, raw_value):
        """`applicationsCount` da Apify è una stringa: un intero puro quando
        LinkedIn mostra il numero esatto, altrimenti una delle due fasce
        testuali fisse osservate ("Be among the first 25 applicants" /
        "Over 200 applicants") quando non lo mostra. Ritorna
        (applicants_count, applicants_bucket): sempre uno dei due None/vuoto,
        entrambi None/vuoti se il formato non è nessuno dei tre casi noti."""
        if not isinstance(raw_value, str):
            return None, ""
        raw_value = raw_value.strip()
        if raw_value.isdigit():
            return int(raw_value), ""
        if "first 25" in raw_value:
            return None, "under_25"
        if "Over 200" in raw_value:
            return None, "over_200"
        return None, ""

    def _parse_published_at(self, raw_value):
        """Converte la data restituita da Apify in un `datetime` prima che
        arrivi a `Job.objects.create()` (campo `DateTimeField`, non accetta
        una stringa grezza)."""
        if not isinstance(raw_value, str):
            return None
        return parse_datetime(raw_value)
