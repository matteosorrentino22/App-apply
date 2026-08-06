# Sprint 32 — Fix layout CV e campi Nome/Cognome

## Input
Test manuali del committente dopo il primo CV generato con successo
(Sprint 30/31). Cinque difetti segnalati, tutti puramente visivi/di
contenuto tranne il primo.

## Esito (2026-08-06)

### 1 — Nome e Cognome mancanti
Nessun campo per inserirli: il titolo in alto al CV mostrava l'email
(`_build_full_name` in `generation.py` cade sull'email quando
`first_name`/`last_name` sono vuoti — logica già corretta, mancavano solo i
campi in UI e nel serializer per popolarli).
- `UserOnboardingSerializer`: aggiunti `first_name`/`last_name` (campi
  nativi di `AbstractUser`, nessuna migrazione necessaria).
- `OnboardingPage.jsx` (step preferenze) e `ProfilePage.jsx`: nuovi campi
  "Nome"/"Cognome" obbligatori, salvati tramite `updateMe` (sono su `User`,
  non su `Profile`).

### 2 — Areas of Expertise senza punto elenco
La lista usava `list-style: none` (necessario per il layout a due colonne
via CSS grid, dove i marker nativi non si posizionano bene) ma senza
sostituirlo con nulla. Aggiunto un marker manuale (`::before { content:
"•" }`), più prevedibile anche per il parsing di un ATS rispetto al marker
nativo del browser.

### 3 — Titolo "PROFILE" superfluo
Rimosso `<h2>{{ labels.summary }}</h2>`; resta solo il paragrafo. Lo spazio
verticale tra sezioni è preservato automaticamente (già definito su
`section`), nessuna linea separatrice aggiunta al suo posto (confermato col
committente).

### 4 — Lingue centrate → allineate a sinistra
`.languages-row`: `justify-content`/`text-align` da `center` a
`flex-start`/`left`. Resta la disposizione in riga orizzontale (confermato
col committente), solo l'allineamento cambia.

### 5 — "Certified in"/"Skilled in" sotto Education → sotto Areas of Expertise
Riordinato il template: il blocco `skills-certifications` si è spostato
subito dopo la sezione Areas of Expertise, prima di Esperienza. Nuovo
ordine delle sezioni: Sommario → Areas of Expertise → Certified in/Skilled
in → Esperienza → Istruzione → Lingue.

### Verifica eseguita
- `python manage.py test`: 167/167 passati (166 pre-esistenti + 1 nuovo su
  `first_name`/`last_name` editabili ed esposti); `makemigrations --check`
  pulito (nessuna migrazione: campi nativi di Django).
- Frontend: `npm run build` e `oxlint` sui file toccati — puliti.
- Verifica visiva end-to-end: generato un CV reale con l'intera pipeline
  (solo `generate_cv_content` mockato) e confermate tutte le 5 modifiche sul
  PDF prodotto.

### Cosa manca
Nessun nuovo punto aperto. Resta valido quanto già segnalato negli sprint
precedenti (calibrazione parametri, qualità reale dei contenuti con una
vera `ANTHROPIC_API_KEY`, suite e2e da ambiente dedicato).
