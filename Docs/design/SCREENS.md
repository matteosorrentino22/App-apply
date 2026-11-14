# SCREENS — mockup → route → codice → cosa cambia

> Mappa schermata per schermata. Il nome nella prima colonna è il file in `mockups/html/<nome>.html` (immagine in `mockups/png/<nome>.png`). I file React sono quelli presenti in `frontend/src/` all'**Sprint 71**. "Nuovo" = da creare. Le voci **[decisione]** rimandano a `SPEC-DELTA.md`.

## 1. Jobs (route `/list`, oggi `JobListPage.jsx` + `HomePage.jsx`)
| Mockup | Cosa mostra | Codice | Cosa cambia |
|---|---|---|---|
| `jobs-lista` | Titolo, pulsante Raccogli, ricerca testo, riepilogo (nuovi oggi / settimana), pillole Raccolti · Importati · Preferiti · Archiviati, filtri attivi, card | `JobListPage.jsx`, `JobCard.jsx` | Card ridotta (badge, titolo, azienda·località + icona recruiter, **2 gap**, data, ♥), tutta cliccabile; niente bottoni Dettagli/Archivia/Genera CV; swipe = archivia |
| `jobs-stats` | Riepilogo espanso | `HomePage.jsx` (statistiche) | Le statistiche di Home entrano in Jobs come `StatsSummary` espandibile; stessa API |
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

## 4. Profilo, impostazioni, ricerche (routes `/profile`, `/settings`)
| Mockup | Codice | Cosa cambia |
|---|---|---|
| `profilo`, `profile-exp` | `ProfilePage.jsx` | Sezioni a fisarmonica, barra "Salva modifiche"; banner profilo incompleto; rimozione foto |
| `impostazioni` | `AccountPage.jsx` (677 righe, da spezzare) | Elenco a gruppi: Ricerche, Notifiche, Account (email, fuso, limiti, privacy), Lingua, Esci |
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

## Punti da verificare in revisione
1. I nomi dei file React sono quelli dell'Sprint 71: se nel frattempo ne cambiano, aggiornare la mappa.
2. `AccountPage.jsx` contiene oggi ricerche, notifiche, account e dati: va spezzato in sottopagine; verificare che i test e2e (`account.spec.js`) continuino a coprire gli stessi flussi.
3. Il mockup `notifications-ios` e `collect-*` dipendono dalle decisioni su notifiche e raccolta automatica (`SPEC-DELTA.md`).
