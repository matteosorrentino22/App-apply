import jsonschema
from anthropic import AnthropicBedrock
from django.conf import settings

# Nome fisso del tool forzato usato per ottenere JSON strutturato: Bedrock
# non supporta il parametro nativo `output_config.format` (json_schema)
# dell'API Anthropic diretta — 400 "output_config.format: Extra inputs are
# not permitted", verificato in produzione — quindi lo strutturiamo con la
# tecnica classica del tool-use forzato, supportata in modo identico.
_OUTPUT_TOOL_NAME = "output"

# A differenza dell'output strutturato nativo, il tool-use forzato non
# garantisce la conformità allo schema (osservato in produzione: il modello
# ha incapsulato l'oggetto in una chiave spuria come "jsonPayload", o
# aggiunto campi fantasma). Si valida quindi esplicitamente la risposta e si
# ritenta un numero limitato di volte prima di arrendersi.
_MAX_ATTEMPTS = 3


class StructuredOutputError(Exception):
    """Il modello non ha rispettato lo schema richiesto nemmeno dopo i retry."""


def call_claude_structured(model, system, user_content, schema, max_tokens, effort=None):
    """Chiama Claude via Bedrock e restituisce l'output validato contro
    `schema` (dict), forzando la chiamata al tool `_OUTPUT_TOOL_NAME` invece
    di usare l'output strutturato nativo (vedi sopra)."""
    client = AnthropicBedrock(aws_region=settings.AWS_BEDROCK_REGION)
    extra = {"output_config": {"effort": effort}} if effort else {}
    last_error = None

    for _ in range(_MAX_ATTEMPTS):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "disabled"},
            system=system,
            messages=[{"role": "user", "content": user_content}],
            **extra,
            tools=[
                {
                    "name": _OUTPUT_TOOL_NAME,
                    "description": (
                        "Restituisci il risultato chiamando questo tool una sola "
                        "volta, con i campi richiesti impostati direttamente come "
                        "argomenti di primo livello dell'input del tool — senza "
                        "nessuna chiave contenitore aggiuntiva (es. niente "
                        "'jsonPayload' o simili) e senza campi non richiesti."
                    ),
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": _OUTPUT_TOOL_NAME},
        )
        block = next(b for b in response.content if b.type == "tool_use")
        try:
            jsonschema.validate(block.input, schema)
            return block.input
        except jsonschema.ValidationError as exc:
            last_error = exc

    raise StructuredOutputError(
        f"Output non conforme allo schema dopo {_MAX_ATTEMPTS} tentativi: {last_error}"
    )
