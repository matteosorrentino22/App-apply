# RELEASE — rilascio del redesign (sprint 72→81) su `main` e in produzione

> **Stato:** procedura scritta nello Sprint 80 (2026-11-15), **non eseguita**. Si esegue solo con l'ok esplicito del committente, in una finestra concordata. Comandi generici: nessun dominio, nessun segreto (il repository è pubblico); `<dominio>` è il dominio reale, `<caddy>` il container Caddy della produzione.
> **Riferimenti:** `DEPLOY.md` (§3 variabili, §4.1 rilascio, §4.3 coerenza dello stack, §4.10 Sprint 77, §6 backup, §10 anteprima), `CLAUDE.md` (mai mescolare `docker-compose.yml` e `docker-compose.prod.yml`).

## 0. Situazione di partenza (verificata il 2026-11-15)
- Produzione: cartella del repository sul VPS (`/root/App-apply`), branch `main` al commit `f6584e5` (Sprint 71); tutti i container da `docker-compose.prod.yml`. Unica modifica locale non committata: `docker/caddy/Caddyfile.prod` con il blocco `anteprima.{$DOMAIN}`, **identico** alla versione committata nei branch del redesign (commit `4c78973`).
- Branch del redesign, **lineari** (ognuno contiene il precedente): `sprint-72-fondamenta` → `sprint-73-appshell` → `sprint-74-lista` → `sprint-75-dettaglio` → `sprint-76-editor` → (commit anteprima) → `sprint-77-raccolta` → `sprint-78-profilo` → `sprint-79-accesso` → `sprint-80-rifinitura` → `sprint-81-correzioni`. `main` è antenato di `sprint-81-correzioni`: il merge è un **fast-forward**, senza conflitti.
- Copia di lavoro separata (`/root/App-apply-dev`) e anteprima (`/root/app-apply-preview`, stack `appapply-preview`): non sono la produzione.

## 1. Ordine di merge su `main`
Il merge di `sprint-81-correzioni` (l'ultimo) porta su `main` tutti gli sprint 72–81 nell'ordine giusto (sono commit successivi della stessa linea). Dalla copia di lavoro, non dalla cartella di produzione:

```
cd /root/App-apply-dev
git fetch origin
git status                                   # pulito, nessun file non committato
git tag pre-redesign origin/main             # punto di ritorno (= f6584e5)
git checkout -B main origin/main
git merge --ff-only sprint-81-correzioni     # deve dire "Fast-forward"; se no, fermarsi
git log --oneline origin/main..main          # elenco atteso: commit da 9e10413 (Docs/design) a Sprint 81
git push origin main pre-redesign
```

Chi preferisce passare da GitHub: una pull request `sprint-81-correzioni` → `main` con "Rebase and merge" o "Create a merge commit" dà lo stesso codice; il tag `pre-redesign` va creato comunque su `f6584e5`. I branch `sprint-7x-*` si possono cancellare dopo il rilascio riuscito (non prima: sono il riferimento per sprint).

## 2. Prima del deploy (stesso giorno)
### 2.1 Variabili d'ambiente da controllare (`.env` di produzione)
Nessuna variabile **nuova** negli sprint 72–81. Da controllare (mostrare solo "impostato / non impostato", mai i valori):

| Variabile | Stato al 2026-11-15 | Cosa fare |
|---|---|---|
| `LEGAL_CONTROLLER_NAME`, `LEGAL_CONTROLLER_EMAIL` (`LEGAL_CONTROLLER_ADDRESS` facoltativo) | **non impostate** | Da compilare **prima** del rilascio: senza, `/privacy` e `/terms` mostrano "Dati del titolare da completare" e l'informativa 1.1 che tutti devono riaccettare (§3) non ha il titolare |
| `REGISTRATION_INVITE_CODE` | impostato | Lasciarlo se la registrazione resta su invito |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | impostate | Verifica email, recupero password e cambio email sono attivi; `DEFAULT_FROM_EMAIL` e `PUBLIC_BASE_URL` vuote = mittente `EMAIL_HOST_USER` e link `https://$DOMAIN` |
| `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` | non impostate | Lasciarle vuote: il pulsante Google resta nascosto (A10) |
| `DJANGO_ADMIN_PATH` | non impostata (`admin/`) | Facoltativo: un percorso non standard (DEPLOY §3) |
| `BACKUP_S3_*` | non impostate | Facoltativo: backup fuori dal VPS (DEPLOY §6) |

Dopo una modifica al `.env`: `docker compose -f docker-compose.prod.yml up -d --force-recreate web worker beat` (DEPLOY §4.2, §7.6) — si può fare nella stessa finestra del deploy, che ricrea comunque i container.

### 2.2 Orario
- **Dopo le 02:00 e dopo la fine del ciclo notturno** di quella notte (Django Admin → *Run logs*: ultime righe `collection`/`scoring` della notte concluse; oppure `docker compose -f docker-compose.prod.yml logs --since 6h worker | tail`). Motivo: con il rilascio sparisce il ciclo notturno; rilasciando dopo che ha girato, quella giornata ha ancora le offerte raccolte di notte. Dal giorno dopo nessuno ha raccolte automatiche finché non le attiva (Sprint 81: i Pro la accendono da sé, §3).
- Meglio anche **dopo il backup delle 03:30** e in un momento di basso uso (es. mattina presto). Rilasciando prima delle 10:00 quel giorno non parte la notifica mattutina (tolta dallo Sprint 77).

### 2.3 Backup (obbligatorio, prima di toccare qualcosa)
Nella cartella di produzione:

```
cd /root/App-apply
# coerenza dello stack (tutti i container devono riportare .../docker-compose.prod.yml)
for c in $(docker ps -q); do docker inspect $c --format '{{.Name}} {{index .Config.Labels "com.docker.compose.project.config_files"}}'; done

# 1) database: dump completo fuori dalla rotazione dei 7 giorni
mkdir -p backups
docker compose -f docker-compose.prod.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > backups/pre-redesign_$(date +%Y%m%d_%H%M).dump
ls -la backups/                                                     # dimensione > 0
docker compose -f docker-compose.prod.yml exec -T db pg_restore -l < backups/pre-redesign_*.dump | head   # elenco leggibile

# 2) database + media con il task standard (volume local_backups)
docker compose -f docker-compose.prod.yml exec worker python manage.py shell -c "from apps.common.tasks import backup_database; backup_database()"

# 3) immagini attuali (ritorno rapido)
for s in web worker beat frontend-build; do docker tag app-apply-$s:latest app-apply-$s:pre-redesign; done

# 4) PWA attualmente servita (volume frontend_dist)
docker run --rm -v app-apply_frontend_dist:/d:ro -v /root:/out alpine tar czf /out/frontend_dist-pre-redesign.tgz -C /d .

# 5) Caddyfile in uso
cp docker/caddy/Caddyfile.prod /root/Caddyfile.prod.pre-redesign
```

I file in `backups/` e in `/root` stanno fuori dalla rotazione: **cancellarli entro 7 giorni** (conservazione dichiarata nell'informativa) quando il rilascio è confermato.

## 3. Migrazioni e cosa fanno sui dati reali
Solo lo Sprint 77 ha migrazioni; gli sprint 72–76 e 78–80 sono solo frontend. Le migrazioni partono da sole all'avvio di `web`.

| Migrazione | Effetto sui dati di produzione | Reversibile |
|---|---|---|
| `accounts/0011_auto_collection` | Aggiunge a ogni utente `auto_collection_enabled` (falso), `auto_collection_time` (07:00), `auto_collection_last_local_date` (vuota) | sì (toglie le colonne) |
| `accounts/0012_enable_auto_collection_for_pro` | **Nessun effetto** (Sprint 81, su richiesta del committente: niente raccolta automatica preimpostata). Tutti, Pro compresi, partono con l'automatica **spenta**; ogni Pro la attiva e sceglie l'orario dal pannello "Raccogli" o da Impostazioni. Fino ad allora i Pro hanno solo la raccolta manuale (una al giorno) | il ritorno non fa nulla |
| `jobs/0021_auto_collection` | Aggiunge `collection_done_at` (vuoto) alle quote giornaliere | sì |
| `jobs/0022_replace_nightly_cycle_schedule` | **Cancella il PeriodicTask "Ciclo notturno" delle 02:00** e crea "Raccolte automatiche Pro (ogni 15 minuti)" | sì (ricrea il ciclo delle 02:00) |
| `notifications/0003_remove_morning_notification` | **Cancella la notifica mattutina delle 10:00**; resta il promemoria di inattività | sì (ricrea la notifica) |

Altri effetti del rilascio:
- **Informativa 1.0 → 1.1** (`apps/accounts/legal.py`, Sprint 77; termini invariati alla 1.0): **tutti gli utenti**, Free e Pro, al primo accesso vedono la schermata "Informativa privacy e termini di servizio" e devono riaccettare (tre caselle); fino ad allora l'app non risponde (gate anche lato server). Conviene avvisare i tester prima.
- **Una raccolta al giorno per utente** (manuale o automatica) da subito. Il giorno del rilascio la quota di oggi risulta libera (la notte non la segna): ognuno può fare **una** raccolta manuale in più rispetto alla notturna → possibili chiamate Apify in più quel giorno.
- **PWA installate**: alla riapertura compare "Nuova versione disponibile" (Sprint 70); un tocco ricarica la nuova interfaccia.
- Nessun dato degli utenti viene cancellato o riscritto oltre a quanto sopra.

## 4. Deploy (solo `docker-compose.prod.yml`)
```
cd /root/App-apply
git status                                    # solo docker/caddy/Caddyfile.prod modificato
git fetch origin
git diff origin/main -- docker/caddy/Caddyfile.prod   # deve essere VUOTO (stesso contenuto); se no, fermarsi
git checkout -- docker/caddy/Caddyfile.prod   # la versione locale coincide con quella di main
git merge --ff-only origin/main               # "Fast-forward" fino al commit dello Sprint 80
git log -1 --oneline

nice docker compose -f docker-compose.prod.yml build web worker beat frontend-build
docker compose -f docker-compose.prod.yml up -d          # ricrea web/worker/beat, ricompila la PWA nel volume; migrazioni con web
docker compose -f docker-compose.prod.yml up -d --force-recreate caddy   # vedi nota
```

**Nota sul Caddyfile:** il file è montato come file singolo; `git checkout`/`merge` lo riscrivono con un nuovo inode, mentre il container continua a vedere il vecchio (stesso contenuto). Ricreare `caddy` (qualche secondo di interruzione) riallinea il montaggio, così le modifiche future al file arrivano al container. In alternativa lasciarlo e ricordarsene alla prossima modifica.

Mai `docker compose up` con `docker-compose.yml` (dev) sul VPS.

## 5. Controlli dopo il deploy
1. **Coerenza dello stack** (comando di §2.3): tutti i container `app-apply-*` da `.../docker-compose.prod.yml`; `docker compose -f docker-compose.prod.yml ps` tutti `Up`, `db` e `redis` `healthy`.
2. **Migrazioni:** `docker compose -f docker-compose.prod.yml exec web python manage.py showmigrations accounts jobs notifications | tail -12` → `[X]` su `accounts 0011, 0012`, `jobs 0021, 0022`, `notifications 0003`. `... exec web python manage.py check --deploy` senza problemi.
3. **Log:** `docker compose -f docker-compose.prod.yml logs --since 10m web worker beat caddy | grep -iE "error|traceback"` → niente di nuovo.
4. **Sito:** `https://<dominio>/` risponde 200; `https://<dominio>/api/legal/` riporta l'informativa alla versione `1.1` e i dati del titolare compilati (`complete: true`).
5. **Django Admin → Periodic tasks:** presenti "Raccolte automatiche Pro (ogni 15 minuti)", "Promemoria di inattività", backup 03:30; **assenti** "Ciclo notturno…" e "Notifica mattutina…". **Users:** "auto collection enabled" spento per tutti (nessuna attivazione preimpostata).
6. **Dal telefono** (PWA dalla Home, e da browser):
   - accesso → schermata di riaccettazione (tre caselle, "Continua" attivo solo con tutte e tre) → lista Jobs;
   - barra di tab con 3 voci; nell'app installata nessun contenuto sotto la status bar o sotto l'indicatore Home;
   - lista: card, filtri, pillole, swipe per archiviare con "Annulla", pannello "Raccogli" (Free: opzione automatica bloccata; Pro: interruttore e orario);
   - dettaglio di un job: punteggio, contatori, "Genera CV ▾" (aprire il pannello e chiudere senza generare, se non si vuole spendere), menu ⋯;
   - editor di un CV esistente: fisarmoniche, "Assistente" (pannello), "Genera PDF finale" solo se si vuole;
   - Profilo: fisarmoniche, "Salva modifiche"; Impostazioni: sottopagine, pannelli, notifiche (stato del dispositivo), "Esci" con conferma;
   - `/privacy` e `/terms` senza login, sezioni a fisarmonica; un indirizzo inesistente mostra "Pagina non trovata".
7. **Email** (una prova): "Password dimenticata?" con un proprio indirizzo → email ricevuta, link funzionante.
8. **Dopo che un Pro ha attivato l'automatica:** il giorno successivo all'orario scelto Admin → *Run logs* `collection` di quel Pro `SUCCESS` (o `SKIPPED` se aveva raccolto a mano); notifica push se c'erano job nuovi; nessun ciclo alle 02:00.
9. Annotare l'esito in `DEPLOY.md §9` (storico verifiche) in forma generica.

## 6. Ritorno indietro se qualcosa va storto
Scegliere il livello più basso che risolve il problema. **Il codice vecchio non funziona con il database migrato** (le colonne nuove sono obbligatorie e il codice vecchio non le valorizza: le registrazioni fallirebbero), quindi per tornare al backend vecchio si tolgono prima le migrazioni (6.2) o si ripristina il database (6.3).

### 6.1 Solo la PWA (problema grafico grave, backend sano)
Temporaneo: ripristina l'interfaccia di prima nel volume servito da Caddy (le API vecchie usate da quella interfaccia esistono ancora).
```
docker run --rm -v app-apply_frontend_dist:/d -v /root:/in:ro alpine sh -c "rm -rf /d/* && tar xzf /in/frontend_dist-pre-redesign.tgz -C /d"
```
Le PWA installate vanno riaperte. Al deploy successivo `frontend-build` riscrive il volume.

### 6.2 Tutto il codice, conservando i dati inseriti dopo il rilascio
```
cd /root/App-apply
# 1) con le immagini NUOVE ancora in esecuzione: togliere le migrazioni dello Sprint 77
docker compose -f docker-compose.prod.yml exec web python manage.py migrate notifications 0002
docker compose -f docker-compose.prod.yml exec web python manage.py migrate jobs 0020
docker compose -f docker-compose.prod.yml exec web python manage.py migrate accounts 0010
#    (ricreano ciclo delle 02:00 e notifica delle 10:00; tolgono le colonne della raccolta automatica)
# 2) codice e immagini di prima
git checkout pre-redesign                     # stato staccato su f6584e5
for s in web worker beat frontend-build; do docker tag app-apply-$s:pre-redesign app-apply-$s:latest; done
docker compose -f docker-compose.prod.yml up -d --no-build --force-recreate web worker beat frontend-build
# 3) PWA di prima (se frontend-build non l'ha già riscritta)
docker run --rm -v app-apply_frontend_dist:/d -v /root:/in:ro alpine sh -c "rm -rf /d/* && tar xzf /in/frontend_dist-pre-redesign.tgz -C /d"
```
Effetti: la versione corrente dell'informativa torna 1.0; chi l'aveva già accettata prima del rilascio non rivede la schermata (le accettazioni restano registrate), chi si è registrato dopo il rilascio (solo 1.1) la rivede; le impostazioni della raccolta automatica dei Pro si perdono. Il `frontend-build` con l'immagine di prima ricompila già la PWA vecchia: il punto 3 serve solo se il volume non risulta aggiornato. Poi controlli di §5 (punti 1–5, con i task di prima). `main` su GitHub va riportato indietro solo con un commit di revert concordato, non con un push forzato.

### 6.3 Database (ultima risorsa, con ok esplicito)
Se 6.2 non riesce: ripristino del dump di §2.3 **sul database di produzione**, che **perde tutto ciò che è stato scritto dopo il dump**. Prima fermare chi scrive (`docker compose -f docker-compose.prod.yml stop web worker beat`), poi `pg_restore --clean --if-exists` dentro il container `db` dal file `backups/pre-redesign_*.dump`, poi codice e immagini come in 6.2 (punto 2). Provare prima il ripristino in un ambiente separato se c'è tempo (DEPLOY §6).

### 6.4 Caddyfile
```
cat /root/Caddyfile.prod.pre-redesign > docker/caddy/Caddyfile.prod      # stesso inode
docker exec <caddy> caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec <caddy> caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```
Se il container era stato ricreato dopo il cambio di inode (§4), dopo il ripristino basta il `reload`; altrimenti `up -d --force-recreate caddy`. Sito 200 prima e dopo.

## 7. Spegnere e cancellare l'anteprima (quando non serve più)
1. `cd /root/app-apply-preview && ./preview.sh destroy` — spegne lo stack `appapply-preview` e cancella container, volumi (dati finti) e l'immagine del backend dell'anteprima.
2. **Blocco Caddy `anteprima.{$DOMAIN}`:** è nel file committato (`docker/caddy/Caddyfile.prod`). Con l'anteprima spenta il sottodominio risponde 502: si può lasciare per usi futuri. Per toglierlo davvero: commit che rimuove il blocco (su un branch, poi `main` con l'ok), `git merge --ff-only origin/main` in produzione e `up -d --force-recreate caddy` (oppure riscrittura nello stesso inode + `validate` + `reload`, DEPLOY §10); sito 200 prima e dopo, copia del file precedente.
3. Cancellare la cartella dell'istanza (contiene le credenziali dell'anteprima): `rm -rf /root/app-apply-preview`.
4. Facoltativo: immagini di prova `docker image rm appapply-e2e-web appapply-e2e-frontend-build` e la copia di lavoro `/root/App-apply-dev` (dopo aver verificato che `git status` sia pulito e tutto sia su GitHub). Nessun record DNS da togliere: il sottodominio è coperto dal record jolly del dominio.

## 8. Cosa serve dal committente prima del rilascio
- Ok al merge e alla finestra (§2.2).
- Valori di `LEGAL_CONTROLLER_NAME` ed `LEGAL_CONTROLLER_EMAIL` inseriti nel `.env` (da lui o su sua indicazione, mai nel repository).
- Prova dal telefono sull'anteprima (sprint 72–81) e, dopo il rilascio, sull'app vera da iPhone con la PWA dalla Home (area sicura, tastiera nella chat, notifiche): non verificabili nello stack di prova.
- Decisioni ancora aperte o da confermare (`SPEC-DELTA.md`): B8 (tema scuro, tablet), B10 (proposta minima implementata), B11 (testo del 429). Nessuna blocca il rilascio.
- Avviso ai tester: riaccettazione dell'informativa al primo accesso; non c'è più la raccolta notturna e **nessuna raccolta automatica è attiva**: i Pro che la vogliono la accendono dal pannello "Raccogli" (o da Impostazioni) e scelgono l'orario; una raccolta al giorno per tutti.
