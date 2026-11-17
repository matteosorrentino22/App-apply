# SCREENS — mockup → route → codice → cosa cambia

> **Stato (Sprint 80): tutte le schermate sono implementate** (sprint 72–79). Le tabelle §1–7 sono la mappa di partenza (file React dello **Sprint 71**); file attuali, differenze rimaste dai mockup e stati aggiunti sono in §8.
>
> Mappa schermata per schermata. Il nome nella prima colonna è il file in `mockups/html/<nome>.html` (immagine in `mockups/png/<nome>.png`). I file React sono quelli presenti in `frontend/src/` all'**Sprint 71**. "Nuovo" = da creare. Le voci **[decisione]** rimandano a `SPEC-DELTA.md`.

## 1. Jobs (route `/list`, oggi `JobListPage.jsx` + `HomePage.jsx`)
| Mockup | Cosa mostra | Codice | Cosa cambia |
|---|---|---|---|
| `jobs-lista` | Titolo, pulsante Raccogli, ricerca testo, riepilogo (nuovi oggi / settimana), pillole Raccolti · Importati · Preferiti · Archiviati, filtri attivi, card | `JobListPage.jsx`, `JobCard.jsx` | Card ridotta (badge, titolo, azienda·località + icona recruiter, **2 gap**, data, ♥), tutta cliccabile; niente bottoni Dettagli/Archivia/Genera CV; swipe = archivia |
| `jobs-stats` | Riepilogo espanso | `HomePage.jsx` (statistiche) | Le statistiche di Home entrano in Jobs come `StatsSummary` espandibile; stessa API |
| `jobs-card-desiderio`, `jobs-filtri-desiderio-modalita` (Sprint 84, **da implementare**) | Card con etichetta Desiderio; pannello Filtri | `JobCard.jsx`, `JobFiltersSheet.jsx`, `utils/jobFilters.js` | Etichetta "Desiderio" con stellina tra le etichette della card; nei Filtri "Lavoro dei desideri" primo chip del gruppo Ricerca; nuovo gruppo **Modalità** (Remoto, Ibrido, In sede, Non indicata) |
| `jobs-filtri-contratto`, `jobs-filtri-contratto-attivi` (Sprint 82, **da implementare**) | Pannello Filtri con i due nuovi gruppi, senza e con selezione | `JobFiltersSheet.jsx`, `utils/jobFilters.js` | Nuovi gruppi **Contratto** (pillole a selezione multipla: Full-time, Part-time, Temporaneo) e **Stipendio** (segmenti Tutti / Con stipendio / Senza stipendio, come Recruiter) |
| `jobs-filtri` | Pannello filtri (stato, punteggio, ricerca, ordinamento, ecc.) + salva filtro | `JobListPage.jsx`, `MultiSelectFilter.jsx` | `Sheet` dal basso; filtri **in URL** (Sprint 68) restano; badge con numero filtri attivi |
| `save-filter` | Salva filtri attuali | `JobListPage.jsx` | `Modal` con nome; filtri salvati come pillole |
| `toast-archived` | Job archiviato · Annulla | `ToastProvider.jsx`, `SwipeToArchive.jsx` | Toast con azione |
| `jobs-importati` | Scheda Importati | `JobListPage.jsx` | Stessa card; pulsante "Aggiungi" |
| `jobs-vuoto` | Nessun job | `JobListPage.jsx` | `EmptyState` con CTA "Raccogli" (e invito Pro) |
| `add-manual` / `add-manual-cost` / `add-manual-blocked` | Aggiungi job da link o a mano; a credito; bloccato (saldo insufficiente) | `JobListPage.jsx` (dialog) | `Sheet`; 3 stati di costo (Sprint 69–70) |
| `jobs-avvisi` | Banner "Profilo incompleto" e "Nuova versione disponibile" | `ProfileCompletionBanner.jsx`, `AppUpdateBanner.jsx` | Restyling `Banner`; priorità: versione, poi profilo |
| `confirm-cost` | Conferma costo oltre il massimale | `ActionCost.jsx` + `window.confirm` in `JobListPage`/`JobDetailPage`/editor | **`CostConfirmDialog`** al posto di `window.confirm` |
| `collect-pro` / `collect-free` / `collect-running` | Raccolta: Pro con orario automatico, Free solo manuale (1/giorno) con opzione bloccata, attesa sincrona | oggi `HomePage.jsx` ("Raccogli ora") | `Sheet` da Jobs. **[decisione]** raccolta automatica Pro (backend) |

## 2. Dettaglio job (route `/jobs/:id`, `JobDetailPage.jsx`)
| Mockup | Cosa mostra | Cosa cambia |
|---|---|---|
| `detail-desiderio-modalita` (Sprint 84, **da implementare**) | Chip della modalità accanto ad azienda · località; etichetta "Lavoro dei desideri" prima delle altre etichette | Senza modalità nota il chip non compare ("Non indicata" solo nei filtri) |
| `detail-stipendio-contratto`, `detail-solo-contratto` (Sprint 82, **da implementare**) | Riga di chip sotto "azienda · località": stipendio (evidenziato, icona banconote) e tipo di contratto (neutro, icona valigetta), stesse dimensioni dei chip dei candidati; con un solo dato, solo quello; senza dati la riga non c'è | Cosa cambia: la card di lista **non** cambia |
| `detail-nuovo` | Stato, titolo, punteggio, azienda·località, recruiter, "Perché questo punteggio" (troncato, Leggi tutto), contatori "7 corrispondenze" / "1 gap" espandibili, descrizione annuncio a fisarmonica, barra con **Genera CV ▾** | Un solo punto di generazione; il chip stato è solo indicativo |
| `detail-menu` | Menu del ▾: Genera cover letter, Genera messaggio | `SplitButton` + `Menu` |
| `detail-gap` | "Colma i gap" prima di generare il CV (facoltativo) | `Sheet`; il testo libero ha `max_length` lato server (CLAUDE.md) |
| `detail-cover-letter`, `detail-message` | Genera cover letter / messaggio di networking | `Sheet` con parametri; avviso AI; "Incluso nel piano: ne restano X su Y oggi" |
| `generazione-in-corso` | Attesa sincrona (minuti) | Spinner + testo, pulsante disattivato |
| `detail-cv-generato` | Sezione Documenti (CV, cover letter, messaggio), barra "Segna candidatura fatta" | `DocumentRow` |
| `detail-docs-pages` | Avvisi multipagina e link firmati (Sprint 66–70) | Avviso `Banner` sotto la riga del CV |
| `detail-applied`, `undo-application` | Candidatura fatta; annulla con conferma | `Modal` di conferma; l'azione "Annulla candidatura" (Sprint 69–70) sta nel menu ⋯ |

## 3. Editor (routes `/jobs/:id/cv-editor`, `/jobs/:id/cover-letter-editor`)
| Mockup | Codice | Cosa cambia |
|---|---|---|
| `cv-editor`, `cv-preview` | `CvDraftEditorPage.jsx` | Sezioni a fisarmonica (Sommario, Qualifica, Aree, Esperienze…) + segmento Modifica/Anteprima; barra "Genera PDF finale" |
| `cv-assistant`, `cv-assistant-warn`, `cv-assistant-credit` | `CvDraftChatPanel.jsx`, `AiNotice.jsx`, `ActionCost.jsx` | Su mobile `Sheet` dal basso; bolle proposta con Rifiuta/Accetta; costo per messaggio e saldo in calce; credito insufficiente disattiva il campo |
| `cv-outdated` | `CvDraftEditorPage.jsx` | `Modal` "bozza superata" (Sprint 69–70) |
| `cover-editor` | `CoverLetterDraftEditorPage.jsx`, `CoverLetterChatPanel.jsx` | Stesso schema del CV, un solo campo di testo |
| `profile-exp` (anche nel profilo) | `ExperienceGroupEditor.jsx`, `RichBulletInput.jsx` | Limiti punti elenco (15 × 400) e avvisi in linea |
| `profile-act-chip`, `profile-act-modifica`, `profile-act-errore`, `profile-act-vuoto`, `profile-act-limite`, `desk-profile-act` (Sprint 82, **da implementare**) | `ExperienceGroupEditor.jsx`, `ChipInput.jsx` | Le **attività** di un ruolo come chip a angoli ridotti (raggio 10 px): tocco sul testo = modifica nel riquadro con contatore e Annulla / Fatto; ✕ da 44 px per eliminare; testo lungo troncato a 3 righe. Le tecnologie restano come sono (pillole attuali) |

## 4. Profilo, impostazioni, ricerche (routes `/profile`, `/settings`)
| Mockup | Codice | Cosa cambia |
|---|---|---|
| `profilo`, `profile-exp` | `ProfilePage.jsx` | Sezioni a fisarmonica, barra "Salva modifiche"; banner profilo incompleto; rimozione foto |
| `impostazioni` | `AccountPage.jsx` (677 righe, da spezzare) | Elenco a gruppi: Ricerche, Notifiche, Account (email, fuso, limiti, privacy), Lingua, Esci |
| `ricerca-nuova-citta-pro`, `ricerca-nuova-citta-free`, `ricerche-citta` (Sprint 84, **da implementare**) | `pages/settings/*` (Ricerche salvate) | Paese (elenco) poi città come chip (Free 1, Pro 5, raggio ~40 km); conteggio "Città attive n di 50"; modalità a segmenti (Qualsiasi / Remoto / Ibrido / In sede) solo Pro, bloccata con badge PRO per i Free; nella scheda della ricerca le città e la modalità |
| `desiderio-pro`, `desiderio-free`, `impostazioni-voci-nuove` (Sprint 84, **da implementare**) | `pages/settings/*` (nuova sottopagina Lavoro dei desideri) | Descrizione (max 1000), paese, fino a 5 città, interruttore Attivo; **nessuna keyword mostrata**; Free bloccato con "Scopri Pro". In Impostazioni: voce "Lavoro dei desideri" in Ricerca job, gruppo **Aspetto** con "Dimensione del testo" |
| `settings-dimensione-testo`, `jobs-lista-testo-grande` (Sprint 84, **da implementare**) | `pages/settings/*` (nuova sottopagina), `index.css` | Come il telefono / Normale / Grande con anteprima; con Grande tutta l'app è più grande e si ridispone |
| `ricerche`, `ricerca-nuova`, `delete-search`, `search-deactivated` | `AccountPage.jsx` (ricerche) | Sottopagina Ricerche; `Sheet` nuova ricerca; `Modal` elimina; avviso all'attivazione |
| `settings-limiti` | `UsageLimitsCard.jsx` | Sottopagina "I tuoi limiti di oggi" |
| `settings-email`, `settings-email-sent`, `confirm-email` | `EmailChangeForm.jsx`, `ConfirmEmailChangePage.jsx` | Sottopagina + schermata di esito |
| `settings-fuso` | `TimezoneSelect.jsx` | Sottopagina |
| `settings-privacy`, `settings-password`, `settings-delete` | `AccountDataActions.jsx` | Export ZIP, notifiche, cambio password, eliminazione account con `Modal` |
| `notifications-ios` | `AccountPage.jsx` (push) | Istruzioni per iPhone/iPad (Home → notifiche) |
| *(logout)* | `App.jsx` `Topbar` | **[decisione]** Logout in Impostazioni (finestra di conferma), non più nella barra |

## 5. Accesso, onboarding, legale
| Mockup | Codice | Cosa cambia |
|---|---|---|
| `login`, `login-err`, `login-not-verified` | `LoginPage.jsx` | Logo + wordmark; **nessun pulsante Google** (non configurato in produzione, **[decisione]**); "Password dimenticata?"; stato email non verificata con "Reinvia" |
| `register`, `register-err`, `register-email` | `RegisterPage.jsx`, `LegalConsents.jsx` | Codice invito, 3 consensi (privacy, termini, età ≥ 16); errori di campo; schermata "Controlla la tua email" |
| `verify-ok`, `verify-expired` | `VerifyEmailPage.jsx` | Esito + "Reinvia link" |
| `forgot`, `forgot-sent`, `reset`, `reset-invalid`, `reset-done` | `ForgotPasswordPage.jsx`, `ResetPasswordPage.jsx` | Restyling dei passi |
| `onboarding1`, `onboarding2`, `onboarding2-err`, `onboarding3` | `onboarding/OnboardingPage.jsx` | Stepper; fuso orario nel passo 1; errore di import CV con riprova |
| `legal-gate` | `LegalAcceptancePage.jsx` | Accettazione informativa e termini al primo accesso/cambio versione |
| `legal-privacy`, `legal-terms` | `LegalPage.jsx` | Sezioni a fisarmonica (12 + 11 titoli reali) |

## 6. Desktop (≥ 1024 px)
| Mockup | Cosa mostra |
|---|---|
| `desk-jobs` | Barra in alto (logo, Jobs · Profilo · Impostazioni, lingua), colonna 640 px |
| `desk-detail` | Stessa colonna; barra azione larga quanto la colonna |
| `desk-editor` | Editor a sinistra + chat AI fissa a destra (400 px), barra "Genera PDF finale" |

## 7. Logo
`logo1…5`, `logo-confronto`: proposte; **scelta la 1**. Asset in `../logo/`.

## 8. Stato di implementazione e differenze rimaste (as-is Sprint 80)
| Area | Sprint | File attuali | Differenze rimaste dai mockup (e perché) |
|---|---|---|---|
| Fondamenta | 72 | `index.css`, `components/ui/*`, `public/` (icone) | Tema scuro solo adattato (B8); scala storica dei raggi tenuta accanto a quella per ruolo |
| Navigazione | 73 | `AppShell.jsx`, `LogoutButton.jsx` | Finestra "Esci" senza mockup (modello di `delete-search`); barra di navigazione anche nell'onboarding |
| Jobs | 74, 77 | `JobListPage.jsx`, `JobCard.jsx`, `StatsSummary.jsx`, `JobFiltersSheet.jsx`, `CollectJobsSheet.jsx`, `ManualJobSheet.jsx` | Statistiche: "di cui manuali" oggi/settimana/totale; inserimento manuale anche per i Free (regola reale); `collect-pro` mostra due limiti, vale la **quota unica** di una raccolta al giorno; segnaposto della ricerca accorciato (Sprint 80: "Titolo, azienda o luogo") |
| Dettaglio | 75 | `JobDetailPage.jsx`, `components/job-detail/*` | Chip di stato senza ▾ (indicativo, B7); "Colma i gap" si apre a ogni "Genera CV"; contatori impilati a 360–390 px; messaggi generati elencati sotto la riga "Messaggio"; nessun testo "nessun link di candidatura" |
| Editor | 76 | `CvDraftEditorPage.jsx`, `CoverLetterDraftEditorPage.jsx`, `components/editor/*`, `DraftChatPanel.jsx`, `lib/useDraftChat.js` | Nelle proposte da decidere resta il "prima" barrato; "bozza superata" sopra una pagina vuota; nessuna conferma di costo (non c'era) |
| Profilo, impostazioni | 78 | `ProfilePage.jsx`, `pages/settings/*`, `components/settings/*`, `UsageLimitsCard.jsx` | Nome e cognome in "Dati di contatto"; notifiche su due livelli (preferenza e dispositivo); elenco completo dei fusi; `settings-limiti` con "Raccolta giornaliera 0/1"; nessun acquisto di piano |
| Accesso, onboarding, legale | 79 | `components/auth/AuthPage.jsx`, pagine di accesso, `onboarding/OnboardingPage.jsx`, `LegalPage.jsx`, `LegalAcceptancePage.jsx`, `legal/shared.jsx` | Pulsante Google solo se configurato (oggi mai); form del profilo sempre visibile nel passo 2; prima sezione legale aperta; termini alla versione 1.0 (testo non cambiato) |
| Desktop | 73–76 | come sopra | Nessun layout tablet (768–1023 px usa quello mobile) |

**Stati senza mockup aggiunti nello Sprint 80** (soluzioni minime, nessuna API nuova):
- **Errore di rete all'avvio** (`ProtectedRoute`): con una sessione salvata ma il server irraggiungibile, "Nessuna connessione" con "Riprova" invece del rimando al login; in tutte le pagine un errore di rete ha il testo "Connessione non riuscita: controlla la rete e riprova." al posto del messaggio generico (`api/client.js`, `ApiError` con status 0).
- **Pagine legali senza risposta da `/api/legal/`**: "Impossibile caricare la pagina" con "Riprova" (prima restavano in caricamento).
- **Pagina non trovata** (`NotFoundPage.jsx`, route `*`): prima un indirizzo sconosciuto mostrava una pagina vuota.
- **Notifiche disattivate** (B10): nel pannello di raccolta, per un Pro con l'automatica attiva e le notifiche spente, un avviso con il link a Impostazioni.

## Punti da verificare in revisione
1. I nomi dei file React sono quelli dell'Sprint 71: se nel frattempo ne cambiano, aggiornare la mappa.
2. `AccountPage.jsx` contiene oggi ricerche, notifiche, account e dati: va spezzato in sottopagine; verificare che i test e2e (`account.spec.js`) continuino a coprire gli stessi flussi.
3. Il mockup `notifications-ios` e `collect-*` dipendono dalle decisioni su notifiche e raccolta automatica (`SPEC-DELTA.md`).
