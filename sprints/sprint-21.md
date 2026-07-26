# Sprint 21 — Deploy produzione

## Input
- Sprint 01 (Docker Compose base) e tutti gli sprint precedenti (applicazione completa).
- Riferimenti: `02-specifiche-tecniche-v3.md` §8, §8.5.

## Obiettivo
Configurazione Docker Compose di produzione con Caddy come reverse proxy e HTTPS automatico, segreti in variabili d'ambiente (Apify, Anthropic, Google OAuth, Web Push), backup automatico giornaliero del database su storage esterno al VPS, aggiornamenti di sicurezza automatici del sistema operativo.

## Risultato atteso
L'applicazione è raggiungibile in HTTPS su un dominio di test tramite Caddy; un backup del database viene prodotto ed esportato fuori dal VPS secondo pianificazione; nessun segreto è presente nel repository.

## Criteri di verifica
- `docker compose -f docker-compose.prod.yml up -d` avvia tutti i servizi in produzione senza errori.
- Richiesta HTTPS al dominio/IP di test restituisce certificato valido emesso da Let's Encrypt (`curl -v https://...` o strumento equivalente).
- Verifica statica: nessuna chiave/token/password in chiaro nei file versionati; tutte le chiavi sono lette da variabili d'ambiente.
- Eseguendo manualmente lo script/job di backup, viene prodotto un dump del database presente sullo storage esterno configurato.
- Eseguendo un ripristino di prova dal dump più recente su un ambiente separato, il database risultante contiene i dati attesi (test di restore, non solo di backup).

## Output per lo sprint successivo
Ambiente di produzione funzionante e verificato, base per la validazione finale end-to-end (Sprint 22).