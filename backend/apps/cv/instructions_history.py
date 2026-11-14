# Storico delle indicazioni riusabili di cover letter e messaggi (Sprint 69).
# La PWA concatena le voci riusate e il testo nuovo separandoli con una riga
# vuota, e quel testo combinato è quello salvato in `instructions_used`
# (serve così com'è al modello). Per lo storico ogni testo salvato si
# riscompone nei blocchi separati da righe vuote: una combinazione di voci
# già note non diventa una voce nuova, e di una combinazione con testo
# nuovo compare solo la parte nuova. Le voci si deduplicano ignorando
# spazi e maiuscole. Effetto collaterale accettato: un'indicazione scritta
# su più paragrafi compare come più voci (riselezionandole tutte si
# ricompone lo stesso testo).
import re

_BLOCK_SEPARATOR = re.compile(r"\n\s*\n")


def _normalize(text):
    return " ".join(text.split()).casefold()


def recent_instruction_entries(texts, limit=20):
    """`texts`: testi `instructions_used` dal più recente."""
    seen = set()
    entries = []
    for text in texts:
        for block in _BLOCK_SEPARATOR.split(text or ""):
            block = block.strip()
            key = _normalize(block)
            if not key or key in seen:
                continue
            seen.add(key)
            entries.append(block)
            if len(entries) >= limit:
                return entries
    return entries
