"""
LLM Service — abstract provider interface.
Supports: openai | anthropic | ollama
Prompt safety enforced: never invent laws/precedents.
Extended with deep legal analysis and normative referencing guidelines.
"""
from __future__ import annotations
import json
import re
from app.config import get_settings

settings = get_settings()

SAFETY_PREAMBLE = """
REGOLE FONDAMENTALI:
1. NON inventare mai numeri precisi di articoli di legge, nomi di sentenze o decisioni giurisprudenziali specifiche.
2. Se vuoi suggerire un riferimento normativo, indica la tipologia e l'ambito (es. "verificare artt. del Codice Civile in materia di responsabilità contrattuale") — NON citare numeri specifici a meno che tu sia ASSOLUTAMENTE certo.
3. Ogni riferimento normativo deve essere marcato con [DA VERIFICARE] se non sei certo al 100%.
4. Sii preciso e concreto. Riferisciti a passaggi reali del testo.
5. Restituisci SOLO JSON valido come specificato.

LINEE GUIDA PER RIFERIMENTI NORMATIVI:
- Cita norme solo quando sono davvero rilevanti e pertinenti al punto analizzato
- Spiega PERCHÉ la norma si applica al caso concreto
- Collega sempre la norma al passaggio specifico del testo
- Se non c'è una base normativa chiara, dichiaralo esplicitamente
- Distingui tra principi generali (es. buona fede, diligenza) e norme specifiche
- Indica sempre se il riferimento è un principio generale o una norma specifica

LINEE GUIDA PER ANALISI APPROFONDITA:
- Non dire solo "punto debole": spiega PERCHÉ è debole, QUALE passaggio lo rende vulnerabile
- Indica QUALE eccezione o contestazione potrebbe essere sollevata
- Descrivi COME la controparte potrebbe impugnare il punto
- Suggerisci COME andrebbe riscritto o integrato per renderlo più forte
- Indica QUALI elementi fattuali, probatori o giuridici andrebbero aggiunti
"""

CROSS_DOC_INSTRUCTION = """
ISTRUZIONI PER VERIFICA CROSS-DOCUMENTALE:
Ti vengono forniti anche documenti di supporto (atto controparte, sentenze, allegati, ecc.).
PRIMA di segnalare che un'affermazione non è fondata o una richiesta non è supportata:
1. Verifica se il fondamento esiste nei documenti di supporto forniti
2. Se il supporto ESISTE in un altro documento, NON classificarlo come "non fondato" ma come:
   - "supportato esternamente ma non esplicitato nel testo principale"
   - "il richiamo è implicito ma andrebbe reso espresso"
   - "il supporto è parziale" (specificando cosa manca)
3. Se il supporto NON esiste neppure nei documenti allegati, allora classificalo come "non fondato"
4. Indica sempre QUALI documenti di supporto hai consultato per questa verifica
"""


def get_llm_client():
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=settings.openai_api_key)
    elif provider == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return None


def llm_complete(system_prompt: str, user_prompt: str, max_tokens: int = 4000, include_cross_doc: bool = False) -> str:
    """Send prompt to configured LLM, return text response."""
    provider = settings.llm_provider.lower()
    full_system = SAFETY_PREAMBLE
    if include_cross_doc:
        full_system += "\n" + CROSS_DOC_INSTRUCTION
    full_system += "\n\n" + system_prompt

    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content

        elif provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                system=full_system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text

        else:
            # Fallback: rule-based mock (when no LLM key provided)
            return json.dumps({"findings": [], "note": "No LLM provider configured"})

    except Exception as e:
        return json.dumps({"findings": [], "error": str(e)})


def parse_json_response(raw: str) -> dict:
    """Safely parse LLM JSON output, handle markdown code fences."""
    if "```" in raw:
        raw = re.sub(r"```(?:json)?\n?", "", raw).strip("`").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"findings": [], "raw": raw}


def chunk_text(text: str, max_chars: int = 8000) -> list[str]:
    """Split long documents into overlapping chunks for LLM processing."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    overlap = 500
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Try to break at paragraph boundary
        last_nl = text.rfind("\n\n", start, end)
        if last_nl > start + max_chars // 2:
            end = last_nl
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
