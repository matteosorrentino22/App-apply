FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Librerie di sistema richieste da WeasyPrint (Pango/Cairo/GObject) per il
# rendering PDF del CV: senza queste, `import weasyprint` fallisce a runtime
# anche se il pacchetto pip è installato correttamente. postgresql-client
# fornisce `pg_dump`/`pg_restore`, usati dal backup giornaliero e dal
# ripristino di prova (Sprint 21) — psycopg2-binary non include i binari CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libffi-dev \
    shared-mime-info \
    postgresql-client \
    && (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 \
        || apt-get install -y --no-install-recommends libgdk-pixbuf2.0-0) \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
