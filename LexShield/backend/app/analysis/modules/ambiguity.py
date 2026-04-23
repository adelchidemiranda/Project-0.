"""
Module 3: Ambiguity & Vagueness Scanner
Detects undefined vague terms and structural ambiguities.
Extended with deeper legal analysis and normative references.
"""
from __future__ import annotations
import re
from app.analysis.base import BaseModule, DocumentContext, FindingData
from app.services.llm import llm_complete, parse_json_response, chunk_text

VAGUE_TERMS_IT = [
    "ragionevole", "ragionevolmente", "congruo", "adeguato", "adeguatamente",
    "tempestivo", "tempestivamente", "idoneo", "idoneamente", "sufficiente",
    "significativo", "rilevante", "proporzionale", "opportuno", "necessario",
    "appropriato", "sostanziale", "normale", "ordinario", "usuale",
    "entro breve termine", "nel più breve tempo", "sollecitamente",
    "a prima richiesta", "senza indugio", "prontamente",
]

VAGUE_TERMS_EN = [
    "reasonable", "reasonably", "appropriate", "appropriately", "adequate",
    "timely", "promptly", "sufficient", "sufficiently", "material",
    "substantial", "significant", "proportionate", "necessary", "suitable",
    "without undue delay", "as soon as practicable", "best efforts",
    "commercially reasonable", "satisfactory",
]


class AmbiguityModule(BaseModule):
    name = "ambiguity"

    def analyze(self, ctx: DocumentContext) -> list[FindingData]:
        findings = []
        findings.extend(self._scan_vague_terms(ctx))
        findings.extend(self._llm_ambiguity(ctx))
        return findings

    def _scan_vague_terms(self, ctx: DocumentContext) -> list[FindingData]:
        findings = []
        terms = VAGUE_TERMS_IT if ctx.language == "it" else VAGUE_TERMS_EN
        text = ctx.normalized_text

        seen_terms = set()

        for term in terms:
            pattern = r"\b" + re.escape(term) + r"\b"
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            if not matches or term in seen_terms:
                continue

            # Check if there's a definition nearby
            term_defined = bool(re.search(
                r'(?:ai\s+sensi\s+del\s+presente|per\s+"' + re.escape(term) + r'"|"' + re.escape(term) + r'"\s+significa)',
                text, re.IGNORECASE
            ))

            if not term_defined and len(matches) >= 1:
                seen_terms.add(term)
                m = matches[0]
                start = max(0, m.start() - 60)
                end = min(len(text), m.end() + 150)
                snippet = text[start:end].strip()

                findings.append(FindingData(
                    severity="Medium" if len(matches) > 2 else "Low",
                    category="Ambiguità / Vaghezza Terminologica",
                    finding_type="internal",
                    claim=snippet[:250],
                    why_weak=(
                        f'Il termine "{term}" è usato {len(matches)} volta/e senza essere definito nel documento. '
                        f'In caso di controversia, le parti potrebbero avere interpretazioni divergenti, '
                        f'lasciando al giudice un ampio margine discrezionale nell\'interpretazione.'
                    ),
                    opponent_angle=(
                        f'La controparte potrà sostenere che "{term}" debba interpretarsi a proprio favore. '
                        f'Senza definizione contrattuale, l\'interpretazione diventa questione di fatto '
                        f'rimessa alla valutazione del giudice.'
                    ),
                    strengthen_suggestion=(
                        f'Aggiungere una definizione precisa: "Ai fini del presente atto, per «{term}» '
                        f'si intende: [DEFINIZIONE SPECIFICA]." Oppure sostituire con parametro '
                        f'misurabile (es. "entro 30 giorni", "per un importo non inferiore a €X").'
                    ),
                    cosa_manca=f'Manca la definizione del termine "{term}" nel contesto del documento.',
                    base_normativa=(
                        "Principio di determinatezza/determinabilità dell'oggetto contrattuale "
                        "[DA VERIFICARE: artt. Codice Civile su oggetto del contratto]. "
                        "I termini vaghi possono rendere contestabile l'adempimento."
                    ),
                    come_rafforzare=(
                        f'Opzione 1: Aggiungere nelle definizioni: «"{term}" significa [definizione precisa]». '
                        f'Opzione 2: Sostituire con termine quantificabile. '
                        f'Opzione 3: Aggiungere criteri oggettivi di valutazione.'
                    ),
                    impatto_potenziale=(
                        "L'ambiguità terminologica è spesso fonte di contenzioso interpretativo. "
                        "L'impatto dipende dalla centralità del termine nel contesto dell'atto."
                    ),
                    char_start=m.start(),
                    char_end=m.end(),
                    confidence=0.85,
                    module_source=self.name,
                ))
        return findings

    def _llm_ambiguity(self, ctx: DocumentContext) -> list[FindingData]:
        system = """Sei un analista legale esperto. Identifica AMBIGUITÀ STRUTTURALI nel documento, andando oltre i semplici termini vaghi:

1. Clausole interpretabili in modi diversi — indica entrambe le interpretazioni possibili
2. Condizioni poco chiare — quando si verifica la condizione? Chi lo determina?
3. Ambiguità di ambito — cosa è incluso ed escluso?
4. Ambiguità di riferimento — a quale documento/parte/data si riferisce?
5. Obbligazioni la cui portata non è determinata

Per ogni ambiguità:
- Cita il PASSAGGIO PRECISO
- Spiega LE DUE O PIÙ INTERPRETAZIONI POSSIBILI
- Indica CHI NE TRAE VANTAGGIO e chi ne è svantaggiato
- Suggerisci una RISCRITTURA PRECISA che elimini l'ambiguità
- Se c'è una norma rilevante sull'interpretazione, indicala con [DA VERIFICARE]

Restituisci JSON: {"findings": [{"claim": "estratto breve", "why_weak": "spiegazione con le interpretazioni possibili", "severity": "Low|Medium|High", "strengthen_suggestion": "riscrittura che elimina l'ambiguità", "opponent_angle": "come la controparte sfrutta l'ambiguità", "base_normativa": "norma interpretativa rilevante [DA VERIFICARE]", "impatto_potenziale": "impatto dell'ambiguità"}]}"""

        all_findings = []
        for chunk in chunk_text(ctx.normalized_text, 5000):
            raw = llm_complete(system, f"Lingua: {ctx.language}\nTipo: {ctx.doc_type}\n\nTesto:\n{chunk}", max_tokens=3000)
            data = parse_json_response(raw)
            for f in data.get("findings", []):
                if f.get("claim"):
                    all_findings.append(FindingData(
                        severity=f.get("severity", "Medium"),
                        category="Ambiguità Strutturale",
                        finding_type="internal",
                        claim=f.get("claim", "")[:300],
                        why_weak=f.get("why_weak", ""),
                        opponent_angle=f.get("opponent_angle", ""),
                        strengthen_suggestion=f.get("strengthen_suggestion", ""),
                        base_normativa=f.get("base_normativa", ""),
                        impatto_potenziale=f.get("impatto_potenziale", ""),
                        confidence=0.72,
                        module_source=self.name,
                    ))
        return all_findings
