# Sprint 79 — Redesign UI: accesso, onboarding, legale

> **Periodo:** 2026-11-15 · **Branch:** `sprint-79-accesso` (da `sprint-78-profilo`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (e2e 58/58, screenshot a 360/390/1280 px); **merge e deploy non fatti** (in attesa dell'ok del committente).

## Input
Perimetro da `Docs/design/IMPLEMENTATION-PLAN.md` (sprint 79) e `SCREENS.md`. Mockup: `login`, `login-err`, `login-not-verified`, `register`, `register-err`, `register-email`, `verify-ok`, `verify-expired`, `forgot`, `forgot-sent`, `reset`, `reset-invalid`, `reset-done`, `confirm-email`, `onboarding1`, `onboarding2`, `onboarding2-err`, `onboarding3`, `legal-gate`, `legal-privacy`, `legal-terms`. Regole: comportamento di oggi con il nuovo aspetto; nessun cambio di API, backend o regole (inviti, limiti, tentativi, consensi, età); nessuna dipendenza né font esterni; it/en; nessuna pagina più larga dello schermo; PDF del CV non toccato; testo legale non modificato; pagine pubbliche accessibili come oggi.

Prima di partire: produzione su `main` (f6584e5), container invariati da `docker-compose.prod.yml`, sito 200 (unica differenza nella copia di produzione: il blocco dell'anteprima nel Caddyfile, approvato nello Sprint 77). Numero: `git log` e `ls sprints/` arrivano entrambi a 78.

## Decisioni prese
- **Google:** il pulsante resta nel codice, condizionato a `google_login_enabled` come dallo Sprint 67. In produzione e nell'anteprima non è configurato, quindi non compare (SPEC-DELTA A10). Non è stato tolto il ramo condizionale, per non cambiare il comportamento se un giorno l'amministratore lo configura.
- **Onboarding, passo 2:** il form del profilo resta **sempre visibile** sotto la scheda di caricamento ("oppure compila qui sotto"). Il mockup `onboarding2` non lo mostra finché non si sceglie: aggiungere una scelta avrebbe significato un passo in più.
- **Riprova dell'import:** dopo un errore "Carica file" resta disponibile; il campo del file viene svuotato a ogni scelta, così si può riscegliere anche **lo stesso file** (prima il browser non segnalava la seconda scelta dello stesso file). Regole dell'import (5 MB, formati, pagine, 5 al giorno) invariate.
- **Pagine legali:** sezioni a fisarmonica con `<details>` nativo (nessuna libreria), **la prima aperta** perché la pagina non parta tutta chiusa; testi, numeri e titoli invariati (12 sezioni nell'informativa, 11 nei termini). In `PrivacyContent`/`TermsContent` è cambiato solo l'attributo `defaultOpen` della prima sezione.
- **Versioni:** l'informativa è alla 1.1 (Sprint 77), i termini sono ancora alla 1.0: il testo legale non si tocca, quindi la versione dei termini non è stata alzata.
- **Password dimenticata:** dopo l'invio la conferma **prende il posto** del modulo (mockup `forgot-sent`); prima compariva sotto il modulo, che restava.
- **Registrazione:** gli errori del server sono mostrati **sotto il campo** a cui si riferiscono (prima solo il primo errore, in alto); se il server ne manda più d'uno si vedono tutti.

## Confronto funzione per funzione (prima → dopo)
| Funzione (prima) | Dopo |
|---|---|
| Login: card con titolo, email, password, "Password dimenticata?" sotto il pulsante, link alla registrazione | logo e lingua in alto, colonna unica, "Password dimenticata?" sopra "Accedi", "Non hai un account? Registrati" in fondo |
| Login: "Credenziali non valide.", troppi tentativi, errore generico | stessi messaggi in un riquadro (`role="alert"`) |
| Login: account non confermato → messaggio e "Invia di nuovo il link" | avviso e pulsante in cima al modulo, esito del reinvio sotto |
| Login Google (solo se configurato) | invariato, oggi non compare |
| Dopo il login: `/list` (o `/onboarding` dal link di verifica) | invariato |
| Registrazione: email, password, codice di invito, tre caselle mai pre-selezionate | stessi campi, suggerimento "Almeno 8 caratteri." e "Richiesto durante la fase di test" sotto i campi |
| Registrazione: primo errore del server in alto; caselle mancanti → messaggio | errori sotto email, password e codice; caselle mancanti sotto i consensi; il resto in un riquadro |
| Registrazione con verifica: "Controlla la tua email" | schermata centrata con icona e "Vai all'accesso" |
| Verifica email: in corso, riuscita, scaduta, non valida, reinvio | stesse quattro schermate, centrate con icona; reinvio con email nella stessa pagina |
| Recupera la password: modulo, risposta sempre uguale, non disponibile senza email | stesso; la conferma sostituisce il modulo; "non disponibile" in un riquadro con l'email del titolare |
| Nuova password: due campi, password diverse, errori del server, link non valido, esito | stesso; "Chiedi un nuovo link" dal link non valido, "Vai all'accesso" dall'esito |
| Conferma del cambio email: in corso, riuscita, errore | stesse schermate, centrate con icona |
| Onboarding: tre passi con titolo e pulsante in fondo alla card | indicatore a barre (Preferenze · Profilo · Ricerca), titolo del passo, pulsante nella barra in basso |
| Passo 1: nome e cognome obbligatori, obiettivo, fuso orario, template bloccato, lingua del CV, foto | stessi campi, lingua del CV a scelte grandi |
| Passo 2: upload facoltativo, messaggio d'errore, form del profilo | scheda di caricamento "Opzionale", errore in un riquadro con "Puoi anche riprovare con un altro file.", form sempre sotto |
| Passo 2: salvataggio sezione per sezione senza duplicati | invariato |
| Passo 3: tipo, keywords, città e paese; ricerca attivata subito | stessi campi, tipo come segmento Ruolo / Azienda |
| Accettazione: tre caselle, "Continua", esporta, elimina, esci | stesso ("Continua" attivo solo con tutte e tre le caselle, come prima); colonna unica, export con `useDataExport` |
| Pagine legali: sezioni sempre aperte, "← Indietro" | sezioni a fisarmonica (prima aperta), "Indietro" con icona, avviso del titolare in un riquadro |

## Implementazione
- Nuovo: `components/auth/AuthPage.jsx`.
- Riscritti nella presentazione: `LoginPage`, `RegisterPage`, `VerifyEmailPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `ConfirmEmailChangePage`, `LegalAcceptancePage`, `LegalPage`, `onboarding/OnboardingPage` (handler e regole invariati).
- Ritocchi: `LegalConsents.jsx` (stile), `legal/shared.jsx` (`Section` a fisarmonica con `defaultOpen`), `PrivacyContent`/`TermsContent` (solo `defaultOpen` sulla prima sezione).
- Rimosso: `ExportDataButton` da `AccountDataActions.jsx` (non più usato).
- Testi (it/en): `auth.emailPlaceholder`; `onboarding.optional`, `uploadingCv`, `uploadCvRetry`, `orFillBelow`, `preferencesTitle`, `profileStepTitle`; `onboarding.uploadCvTitle` senza "(opzionale)"; `legal.back` senza la freccia (l'icona è nel pulsante). Controllo automatico: tutte le 605 chiavi usate esistono in it ed en.
- Backend / API: nessun cambio.

## E2e
| Spec / test | Prima | Dopo |
|---|---|---|
| `auth-onboarding` › registrazione e onboarding; esperienze | "Profilo" nel contenuto | titolo "Il tuo profilo" e passo corrente "Profilo" (`aria-current="step"`) |
| **nuovo** › passi, fuso orario, import del CV con errore e riprova | — | 422 → riquadro d'errore; stesso file di nuovo → 200, sommario compilato, errore sparito, 2 richieste |
| **nuovo** › errori in linea e consensi | — | senza caselle: messaggio; 400 finto: errori sotto codice e password, `aria-invalid` |
| **nuovo** › "controlla la tua email" | — | risposta finta `verification_required` |
| **nuovo** › email non confermata | — | 403 finto, nessun pulsante Google, "Invia di nuovo il link" e conferma |
| **nuovo** › verifica email riuscita / scaduta / mancante | — | risposte finte |
| **nuovo** › recupero non disponibile | — | stack senza email: nessun modulo |
| **nuovo** › recupero e reset | — | `email_enabled` finto; inviato; link non valido; reset riuscito |
| **nuovo** › pagine legali | — | 12 e 11 sezioni, la prima aperta, apertura di una sezione |
| **nuovo** › accettazione | — | `/me` con `legal_acceptance_required`; "Continua" disattivato fino alle tre caselle; elimina ed esci presenti |
| altri spec | — | invariati, passano |

## Verifica
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi).
- **E2e** sullo stack usa e getta (immagini ricostruite dal branch): primo giro **55/57**. I due fallimenti erano asserzioni, non difetti: (1) il selettore del file trovava anche il riquadro con lo stesso nome; (2) il test del reset presupponeva l'invio email attivo, mentre lo stack di prova non lo ha e la pagina mostra correttamente "non disponibile" (aggiunto un test per questo caso, simulato `email_enabled` nell'altro). Nel rilancio due etichette da precisare ("Nuova password" esatta, "Ripeti la nuova password"). Poi **suite completa 58/58**.
- **Screenshot** (360/390/1280 px, più login, registrazione e informativa in inglese a 360): login, errore, email non confermata, registrazione, errori in linea, consensi mancanti, controlla la tua email, verifica riuscita / scaduta / non valida, recupero, inviato, non disponibile, nuova password, password diverse, link non valido, password aggiornata, conferma del cambio email riuscita ed errore, onboarding passi 1–3 ed errore dell'import, accettazione, informativa, termini. Gli stati legati alle email con risposte finte dell'API.
- Nessuna pagina sborda (84 misure); nessun errore JavaScript. Dal controllo visivo: accorciato il testo di riprova dell'import, che ripeteva "compila".
- Backend non toccato: test backend non necessari. Stack di prova abbattuto.

## Cosa manca / note
- Nell'onboarding resta la barra di navigazione (Jobs, Profilo, Impostazioni), come prima: il mockup non la mostra, ma toglierla cambierebbe il comportamento dell'`AppShell` per un utente già collegato.
- Il campo "Foto profilo" usa ancora il selettore di file nativo del browser (testo nella lingua del browser).
- Il collegamento dell'onboarding con un "Indietro" tra i passi non esiste (non c'era prima).
- Rifinitura generale (en, contrasto, iPhone da Home): sprint 80.
