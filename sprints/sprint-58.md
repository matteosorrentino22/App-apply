# Sprint 58 — Grassetto automatico sulle keyword rilevanti nei bullet

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `3259f91`

## Input
Prima di passare al chatbot: le keyword rilevanti per il job devono
comparire in grassetto dentro i bullet delle esperienze, restituite
direttamente da Claude con il resto del CV, e la cosa va gestita anche in
"Modifica CV".

## Decisioni prese
- Proposte due rappresentazioni: (A) marcatori nel testo `**parola**`;
  (B) lista separata di frasi da evidenziare per bullet, modificabile come
  chip (consigliata inizialmente). Il committente ha scartato la lista
  separata ("non è bella") e chiesto un comportamento "alla Word":
  selezionare il testo nel campo del bullet e premere un pulsante.
- Scelta finale: marcatori `**...**` nel testo del bullet come unico
  formato, sia per il grassetto prodotto dall'AI sia per quello manuale;
  nell'editor un campo ricco con pulsante grassetto e Ctrl/Cmd+B.
- Ambito: solo i bullet delle esperienze (non sommario, aree, skills).
- Limite nel prompt: massimo 1–2 brevi parole/espressioni per bullet,
  testo letterale del bullet stesso (nessun contenuto aggiunto).
- Nessuna modifica a selezione/taglio/overflow: il testo del bullet resta
  una stringa.

## Implementazione

### Backend
- `ai_content.py`, `CONTENT_SYSTEM_PROMPT`: nuovo paragrafo "GRASSETTO NEI
  BULLET" (marcatore `**parola**` senza spazi interni, 1–2 evidenziazioni
  per bullet, solo le più rilevanti per l'offerta — tool/tecnologia
  richiesta, competenza chiave, risultato numerico —, mai intere frasi,
  non forzato). Schema JSON invariato.
- Nuovo `apps/cv/templatetags/cv_extras.py`: filtro `bold_markup`
  (regex non greedy `\*\*(.+?)\*\*`), che fa l'escape HTML di tutto il
  testo e produce solo `<strong>` attorno alle porzioni marcate; marcatori
  non bilanciati restano testo letterale.
- `cv_template.html`: `{% load cv_extras %}` e
  `<li>{{ bullet|bold_markup }}</li>` nei bullet delle esperienze. Vale
  per il PDF generato, per l'anteprima e per il PDF finale dell'editor.

### Frontend
- Nuovo componente `RichBulletInput.jsx`: `contentEditable` con pulsante
  "B" (icona `Bold`) e scorciatoia Ctrl/Cmd+B (toggle: se la selezione è
  dentro un `<strong>` lo rimuove), Invio disabilitato, incolla solo testo
  semplice. Converte marcatori ↔ `<strong>` (`markersToHtml` /
  `nodeToMarkers`): il valore salvato resta la stringa con `**...**`.
- `CvDraftEditorPage.jsx`: il testo dei bullet usa `RichBulletInput` al
  posto della `Textarea`.

## Verifica
- Suite `apps.cv` 49/49; build frontend ok.
- CV reale rigenerato in produzione: Claude produce correttamente i
  marcatori; rendering PDF→PNG con 1–2 evidenziazioni per bullet.
- Segnalazione del committente subito dopo il rilascio: in un CV i
  grassetti apparivano come `**parola**` letterali e mancava il pulsante.
  Diagnosi: i dati erano corretti (`content_json` con marcatori); la tab
  dell'editor era stata aperta prima del deploy e usava ancora il bundle
  precedente (Textarea semplice). Risolto con ricarica forzata, nessuna
  modifica di codice.

## Note / cosa manca
- Nessun test automatico per `bold_markup` né per `RichBulletInput`.
- I marcatori sono interpretati solo nei bullet delle esperienze: se
  comparissero in altri campi (es. sommario modificato a mano o da chat)
  verrebbero stampati come asterischi letterali.
- Proposto e non deciso: ricaricamento automatico della PWA dopo un
  deploy (problema delle tab rimaste aperte su una versione precedente).
