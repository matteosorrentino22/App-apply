#!/bin/sh
# Gestione dell'istanza di anteprima (vedi DEPLOY.md, "Istanza di anteprima").
# Modello: copiarlo con gli altri file di docker/preview/ in una cartella
# fuori da git sul VPS (DEPLOY.md §10) ed eseguirlo da lì.
# Codice dalla copia di lavoro separata; mai dalla cartella di produzione.
set -eu
cd "$(dirname "$0")"
DEV=/root/App-apply-dev
PROD_ENV=/root/App-apply/.env
P="docker compose -p appapply-preview -f docker-compose.preview.yml"

rand() { head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }

# Tempo di risposta della produzione (solo codice HTTP e secondi).
probe() {
  host=$(grep -E '^DOMAIN=' "$PROD_ENV" | cut -d= -f2- | tr -d "\"'")
  curl -s -o /dev/null --max-time 10 -w "produzione: %{http_code} in %{time_total}s\n" "https://$host/" || echo "produzione: nessuna risposta"
}

# Controllo della produzione ogni 15 s mentre gira un comando pesante.
with_probe() {
  ( while true; do probe; sleep 15; done ) & watcher=$!
  rc=0
  "$@" || rc=$?
  kill "$watcher" 2>/dev/null || true
  return $rc
}

case "${1:-}" in
  init)
    # Segreti e credenziali generati a caso, solo in questa cartella (700) e
    # nei file 600; mai stampati. Il dominio si legge dal .env di produzione
    # (solo la variabile DOMAIN).
    [ -f .env.preview ] && { echo ".env.preview esiste già"; exit 1; }
    umask 077
    host="anteprima.$(grep -E '^DOMAIN=' "$PROD_ENV" | cut -d= -f2- | tr -d "\"'")"
    basic_user="anteprima"; basic_pw=$(rand 24)
    app_email="prova@example.com"; app_pw=$(rand 20)
    db_pw=$(rand 32)
    hash=$(printf '%s\n%s\n' "$basic_pw" "$basic_pw" | docker run --rm -i caddy:2-alpine caddy hash-password 2>/dev/null | tail -1)
    cat > .env.preview <<ENV
DJANGO_SECRET_KEY=$(rand 50)
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=$host
DJANGO_CSRF_TRUSTED_ORIGINS=https://$host
DJANGO_ADMIN_PATH=$(rand 16)/
PUBLIC_BASE_URL=https://$host
REGISTRATION_INVITE_CODE=$(rand 32)
POSTGRES_HOST=preview-db
POSTGRES_PORT=5432
POSTGRES_DB=app_apply_preview
POSTGRES_USER=app_apply_preview
POSTGRES_PASSWORD=$db_pw
REDIS_CACHE_URL=redis://preview-redis:6379/2
CELERY_BROKER_URL=redis://preview-redis:6379/0
CELERY_RESULT_BACKEND=redis://preview-redis:6379/1
LEGAL_CONTROLLER_NAME=Istanza di anteprima (dati di prova)
LEGAL_CONTROLLER_EMAIL=anteprima@example.com
PREVIEW_APP_EMAIL=$app_email
PREVIEW_APP_PASSWORD=$app_pw
ENV
    # Hash bcrypt in un file a parte importato dal Caddyfile (niente
    # interpolazione dei "$" come in un env_file).
    printf '%s %s\n' "$basic_user" "$hash" > auth.caddy
    case "$hash" in '$2'*) ;; *) echo "hash della password non generato"; rm -f .env.preview auth.caddy; exit 1 ;; esac
    cat > CREDENZIALI.txt <<CRED
Anteprima: https://$host
1) Password del sito (finestra del browser): utente $basic_user  password $basic_pw
2) Login dell'app: email $app_email  password $app_pw
Dati finti, nessuna chiave reale, registrazione chiusa.
CRED
    chmod 600 .env.preview CREDENZIALI.txt auth.caddy
    echo "creati .env.preview, auth.caddy e CREDENZIALI.txt (600)"
    ;;
  build)
    # Backend: immagine dalla copia di lavoro (strati delle dipendenze in
    # cache). Frontend: build in un container con CPU e memoria limitate e
    # priorità bassa, dentro l'immagine con le dipendenze npm già installate.
    probe
    with_probe nice -n 19 ionice -c3 docker build -q -t appapply-preview-web "$DEV/backend"
    docker volume create appapply-preview_frontend >/dev/null
    with_probe nice -n 19 ionice -c3 docker run --rm --cpus 0.5 --cpu-shares 128 --memory 900m --memory-swap 900m \
      -e VITE_BACKEND_URL= -v "$DEV/frontend/src:/mnt/src:ro" -v "$DEV/frontend/index.html:/mnt/index.html:ro" \
      -v appapply-preview_frontend:/dist --entrypoint sh appapply-e2e-frontend-build \
      -c "rm -rf /app/src && cp -r /mnt/src /app/src && cp /mnt/index.html /app/index.html && nice -n 19 npm run build >/tmp/build.log 2>&1 && rm -rf /dist/* && cp -r dist/. /dist/ && echo 'frontend: build ok' || (tail -20 /tmp/build.log; exit 1)"
    probe
    ;;
  up) $P up -d; probe ;;
  seed) $P exec -T preview-web python manage.py shell < seed_preview.py ;;
  update)
    # Dopo aver cambiato branch nella copia di lavoro: ricostruisce e riavvia
    # (dati conservati; per ripartire dai dati di prova: ./preview.sh seed).
    "$0" build
    $P up -d --force-recreate preview-web preview-caddy
    probe
    ;;
  status) $P ps; docker stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}' | grep preview || true; probe ;;
  down) $P down ;;
  destroy)
    # Spegne e cancella anche i dati (volumi) e l'immagine del backend.
    $P down -v
    docker volume rm appapply-preview_frontend 2>/dev/null || true
    docker image rm appapply-preview-web 2>/dev/null || true
    ;;
  *) echo "uso: $0 init|build|up|seed|update|status|down|destroy"; exit 1 ;;
esac
