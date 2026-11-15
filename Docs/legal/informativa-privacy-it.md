<!-- Testo di riferimento versionato (Sprint 67). La versione mostrata agli utenti è in frontend/src/legal/; i segnaposto sono sostituiti con i valori di GET /api/legal/ (versioni e date nel backend, dati del titolare da variabili d'ambiente). -->

# Informativa sul trattamento dei dati personali

**Versione {{PRIVACY_VERSION}} — in vigore dal {{PRIVACY_DATE}}**

Questa informativa è resa ai sensi degli artt. 13 e 14 del Regolamento (UE) 2016/679 ("GDPR") a chi si registra e usa App-apply (di seguito "l'app"), un servizio che raccoglie offerte di lavoro, ne valuta l'affinità con il profilo dell'utente e lo aiuta a preparare CV, lettere di presentazione e messaggi.

## 1. Titolare del trattamento
{{CONTROLLER_NAME}}{{CONTROLLER_ADDRESS}} — email: {{CONTROLLER_EMAIL}}.
Per qualunque richiesta relativa ai tuoi dati puoi scrivere a questo indirizzo. Non è stato nominato un Responsabile della protezione dei dati (DPO), non essendo obbligatorio.

## 2. Quali dati trattiamo
- **Dati dell'account:** email di accesso, password (conservata solo in forma cifrata non reversibile), lingua dell'interfaccia, fuso orario, piano, saldo del credito, data di registrazione, stato di verifica dell'email, preferenza sulle notifiche, attivazione e orario della raccolta automatica (piano Pro), registrazione delle accettazioni di questa informativa e dei termini (versione e data).
- **Dati del profilo professionale**, che inserisci tu o che l'app estrae dal CV che carichi in onboarding: nome, cognome, telefono, email di contatto, città e paese, profilo LinkedIn, foto (facoltativa), sommario, esperienze lavorative, istruzione, competenze, certificazioni, lingue, obiettivo professionale. Il file del CV caricato viene letto per compilare il profilo e **non viene conservato**.
- **Dati di utilizzo del servizio:** ricerche salvate, offerte raccolte o importate con i relativi punteggi e motivazioni, documenti generati (CV, cover letter, messaggi), bozze, cronologia delle chat con l'assistente AI, istruzioni che fornisci, preferiti, filtri salvati, stato delle candidature.
- **Dati di terzi che inserisci o che compaiono nelle offerte:** nome e profilo pubblico del recruiter indicati nell'annuncio; nome e profilo LinkedIn del destinatario di un messaggio di networking che scrivi tu. Ti chiediamo di inserirli solo se hai un motivo legittimo per contattare quella persona.
- **Dati tecnici:** token di accesso (conservati solo in forma cifrata non reversibile), dati della sottoscrizione alle notifiche push del tuo browser, indirizzo IP e dati della richiesta nei log di sicurezza del server, registri tecnici delle elaborazioni.

**Ti chiediamo di non inserire nel profilo dati particolari** (art. 9 GDPR: salute, opinioni politiche, convinzioni religiose, appartenenza sindacale, ecc.) né dati giudiziari: non servono al servizio. Se scegli di inserirli, li tratteremo solo per generare i documenti che richiedi.

## 3. Finalità e basi giuridiche
| Finalità | Base giuridica |
|---|---|
| Creare e gestire il tuo account; fornire il servizio (raccolta e valutazione delle offerte, generazione e modifica dei documenti, chat, notifiche sui nuovi job a fine raccolta automatica e promemoria in caso di inattività) | Esecuzione del contratto (art. 6.1.b) |
| Invio di email di servizio (verifica dell'indirizzo, recupero password, conferma di cancellazione) | Esecuzione del contratto (art. 6.1.b) |
| Notifiche push sul dispositivo | Consenso, espresso tramite il permesso del browser e revocabile in ogni momento dall'app o dalle impostazioni del browser (art. 6.1.a) |
| Sicurezza del servizio, prevenzione di abusi e frodi, limiti di frequenza, log tecnici | Legittimo interesse del titolare a proteggere il servizio e i dati degli utenti (art. 6.1.f) |
| Adempimenti di legge e difesa di diritti in sede giudiziaria | Obbligo legale (art. 6.1.c) e legittimo interesse (art. 6.1.f) |

Non usiamo i tuoi dati per pubblicità, non li vendiamo e non li cediamo a terzi per loro finalità.

## 4. Uso dell'intelligenza artificiale
L'app usa modelli di intelligenza artificiale (Claude, tramite il servizio Amazon Bedrock) per: estrarre il profilo dal CV caricato, valutare l'affinità delle offerte con il tuo profilo (punteggio, punti di forza e lacune), generare CV, lettere di presentazione e messaggi, e rispondere nella chat degli editor.
- I contenuti generati sono **proposte**: verificali sempre prima di usarli. Sei responsabile della veridicità dei documenti che invii.
- La valutazione delle offerte è un'elaborazione automatizzata a **tuo esclusivo uso**: serve a ordinare le offerte per te e **non produce decisioni che abbiano effetti giuridici** su di te ai sensi dell'art. 22 GDPR. Non viene comunicata a datori di lavoro o a terzi.
- Le elaborazioni AI avvengono **nell'Unione Europea**: le richieste sono inviate alla regione AWS di Francoforte e, tramite i profili di inferenza «EU» di Amazon Bedrock, possono essere elaborate solo in regioni AWS situate nell'UE. Il fornitore del servizio non usa i dati inviati per addestrare i modelli.

## 5. Destinatari e responsabili del trattamento
I dati sono trattati dal titolare e, per suo conto, da fornitori che agiscono come responsabili del trattamento (art. 28 GDPR) o come titolari autonomi per i servizi indicati:
- **Hosting del server:** Hostinger International Ltd — server situato in Germania (UE).
- **Elaborazione AI:** Amazon Web Services (Amazon Bedrock), regione UE (Francoforte), con elaborazione limitata alle regioni AWS dell'UE.
- **Invio delle email di servizio:** Google (Gmail) — l'indirizzo email e il contenuto del messaggio transitano sui server di Google; una copia delle email inviate resta nella casella del titolare presso Google e viene cancellata periodicamente.
- **Notifiche push:** il servizio push del tuo browser (es. Google, Mozilla, Apple, Microsoft) riceve solo l'identificativo tecnico della sottoscrizione e il testo della notifica, che non contiene dati del tuo profilo.
- **Raccolta delle offerte:** Apify (raccolta automatica degli annunci) e LinkedIn (pagine pubbliche degli annunci): ricevono solo le parole chiave e le località delle tue ricerche, **non** i dati del tuo profilo.
- **Ricerca delle località:** OpenStreetMap (Nominatim), interrogato dal nostro server con il solo testo della città digitata.
- **Accesso con Google** (quando sarà disponibile): Google riceve la richiesta di autenticazione e ci comunica il tuo indirizzo email.

## 6. Trasferimenti fuori dall'Unione Europea
I dati del profilo e i documenti sono conservati ed elaborati nell'UE. Alcuni fornitori (Google per le email e le notifiche, altri servizi push, Apify) possono trattare i dati indicati sopra anche negli Stati Uniti: in tal caso il trasferimento si basa sulla decisione di adeguatezza UE–USA (EU-US Data Privacy Framework) per i fornitori certificati o sulle Clausole contrattuali standard della Commissione europea.

## 7. Per quanto tempo conserviamo i dati
- **Account, profilo, offerte, documenti, bozze e chat:** finché mantieni l'account. Se lo cancelli, li eliminiamo subito, insieme ai file (PDF e foto).
- **Copie di backup:** sono conservate per 7 giorni e poi cancellate automaticamente; i dati cancellati scompaiono anche dai backup entro questo termine.
- **Log di sicurezza del server (con indirizzi IP):** 14 giorni.
- **Dati temporanei per i limiti di frequenza:** al massimo 24 ore.
- **Token di accesso:** scadono dopo 30 giorni di inattività o al logout.
- **Registri tecnici delle elaborazioni** (esito di raccolte, generazioni e chat): per la durata dell'account; se lo cancelli restano solo in forma anonima, senza alcun riferimento a te.
- **Registrazione delle accettazioni** di informativa e termini: per la durata dell'account.

## 8. I tuoi diritti
Hai diritto di chiedere l'accesso ai tuoi dati, la rettifica, la cancellazione, la limitazione del trattamento, la portabilità e di opporti ai trattamenti basati sul legittimo interesse; puoi revocare in ogni momento il consenso alle notifiche, senza effetti sui trattamenti precedenti.
- Dall'app puoi in autonomia: **modificare** il profilo, **scaricare** tutti i tuoi dati in formato leggibile (Impostazioni → Esporta i miei dati), **cancellare** l'account e tutti i dati (Impostazioni → Elimina account), disattivare le notifiche.
- Per tutto il resto scrivi a {{CONTROLLER_EMAIL}}: rispondiamo entro un mese.
- Hai anche diritto di proporre reclamo al **Garante per la protezione dei dati personali** (www.garanteprivacy.it) o all'autorità del Paese UE in cui vivi o lavori.

## 9. Età minima
L'app è riservata a chi ha compiuto **16 anni**. Registrandoti dichiari di avere almeno 16 anni.

## 10. Cookie e archiviazione sul dispositivo
L'app **non usa cookie di profilazione né strumenti di analisi o pubblicità**. Sul tuo dispositivo salva solo ciò che serve a farla funzionare: il token di accesso e la lingua scelta (memoria locale del browser) e i file dell'app installabile (service worker), necessari anche per le notifiche. Per questi strumenti tecnici non è richiesto il consenso. L'area di amministrazione, usata solo dal titolare, usa cookie tecnici di sessione.

## 11. Sicurezza
Usiamo misure tecniche e organizzative adeguate: connessione cifrata (HTTPS), password e token conservati in forma cifrata, accesso ai documenti consentito solo al proprietario tramite link temporanei, limiti ai tentativi di accesso, aggiornamenti di sicurezza del server, backup.

## 12. Modifiche
Se modifichiamo questa informativa in modo sostanziale te lo segnaleremo nell'app e, dove necessario, ti chiederemo di prenderne visione di nuovo. La versione in vigore è sempre disponibile in questa pagina.
