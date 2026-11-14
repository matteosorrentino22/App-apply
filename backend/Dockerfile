FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Librerie di sistema richieste da WeasyPrint (Pango/Cairo/GObject) per il
# rendering PDF del CV: senza queste, `import weasyprint` fallisce a runtime
# anche se il pacchetto pip è installato correttamente. postgresql-client
# fornisce `pg_dump`/`pg_restore`, usati dal backup giornaliero e dal
# ripristino di prova (Sprint 21) — psycopg2-binary non include i binari CLI.
# fonts-crosextra-caladea (Sprint 52): l'immagine di base non ha né Calibri
# né Cambria (solo DejaVu) — Pango ricadeva silenziosamente su DejaVu Sans
# per qualunque font-family richiesta nel template, mai realmente "Calibri".
# Caladea è il font open source metricamente compatibile con Cambria.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libffi-dev \
    shared-mime-info \
    postgresql-client \
    fonts-crosextra-caladea \
    && (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 \
        || apt-get install -y --no-install-recommends libgdk-pixbuf2.0-0) \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Utente non privilegiato (Sprint 66) per web/worker/beat: una falla in un
# parser (pdfminer, Pillow, lxml, WeasyPrint) non dà root nel container, e
# il codice (di root) resta in sola lettura: scrivibili solo staticfiles e
# mediafiles. uid fisso 1000: i volumi media_data/static_data esistenti vanno passati a
# questo uid una volta prima del primo avvio (DEPLOY.md §4.5); i volumi nuovi
# ereditano il proprietario dalle cartelle create qui sotto (compresa
# /app/backups, volume `local_backups` dei backup locali, Sprint 67).
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/staticfiles /app/mediafiles /app/backups \
    && chown app:app /app/staticfiles /app/mediafiles \
    && chown app:app /app/backups && chmod 700 /app/backups

COPY . .

USER app

EXPOSE 8000
