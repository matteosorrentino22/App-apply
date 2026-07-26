# Sprint 22 — QA end-to-end

## Input
- Sprint 21 completato (ambiente di deploy funzionante); tutte le funzionalità implementate.
- Riferimenti: `01-specifiche-funzionali-v4.md` §7 (criteri di accettazione), §6 (non funzionali).

## Obiettivo
Percorrere sistematicamente la checklist dei criteri di accettazione del documento funzionale (§7) sull'ambiente deployato, verificando anche i requisiti trasversali (isolamento multi-utente, fuso orario, lingua interfaccia) e correggendo eventuali difetti emersi.

## Risultato atteso
Tutte le voci della checklist §7 delle specifiche funzionali risultano verificate sull'ambiente di test deployato, con eventuali difetti corretti e ri-verificati.

## Criteri di verifica
- Per ciascuna delle sezioni della checklist §7 (profilo/onboarding, ricerche, raccolta e fonte, notifiche, scoring, vista lista/sezioni/ricerca, stati del job, generazione CV, arricchimento, import manuale, piani/massimali/credito, requisiti trasversali), eseguire il test corrispondente (manuale o automatizzato) sull'ambiente deployato e registrarne l'esito.
- Test di isolamento multi-utente: con due utenti di test, verificare che nessuno dei due possa accedere a dati (profilo, ricerche, job, CV) dell'altro, tramite chiamate API dirette con il token dell'uno sulle risorse dell'altro.
- Test fuso orario: con un utente configurato su un fuso non-Europe/Rome, verificare che "oggi" in lista e l'orario delle notifiche seguano il fuso locale, mentre il reset dei massimali segua Europe/Rome.
- Report finale: percentuale di voci della checklist §7 verificate con esito positivo = 100%, oppure elenco esplicito delle eccezioni residue con relativa motivazione.

## Output per lo sprint successivo
Nessuno (ultimo sprint) — l'output è la validazione complessiva del MVP rispetto alle specifiche funzionali.