"""
Module 5: Strengthening Suggestions
Proposes concrete improvements with deep legal analysis and normative references.
"""
from __future__ import annotations
from app.analysis.base import BaseModule, DocumentContext, FindingData
from app.services.llm import llm_complete, parse_json_response, chunk_text


class StrengtheningModule(BaseModule):
    name = "strengthening"

    def analyze(self, ctx: DocumentContext) -> list[FindingData]:
        if ctx.doc_role == "opponent":
            return []  # Strengthening is only for own documents

        has_support = len(ctx.support_documents) > 0
        support_context = ""
        if has_support:
            support_context = f"""

DOCUMENTI DI SUPPORTO DISPONIBILI:
{ctx.get_support_text_summary(max_chars=3000)}

Quando suggerisci rafforzamenti, verifica prima se il supporto necessario esiste già in uno dei documenti allegati.
Se sì, suggerisci di integrare il riferimento nel testo principale.
Se no, indica quali documenti/prove andrebbero acquisiti."""

        system = f"""Sei un editor legale senior esperto in diritto italiano. Rivedi questo documento e fornisci MIGLIORAMENTI CONCRETI e OPERATIVI.

Per ogni suggerimento:
- Indica il PASSAGGIO SPECIFICO debole (estratto esatto dal testo)
- Spiega PERCHÉ è debole dal punto di vista difensivo con ragionamento giuridico
- Fornisci una RISCRITTURA SPECIFICA o una lista di elementi da aggiungere
- Indica la BASE NORMATIVA pertinente se rilevante (con [DA VERIFICARE] se non certo)
- Valuta la PRIORITÀ dell'intervento e l'IMPATTO sulla solidità dell'atto

Concentrati su:
- Prove/allegati mancanti che dovrebbero essere richiamati
- Catene di ragionamento giuridico incomplete
- Clausole protettive mancanti
- Termini vaghi che dovrebbero essere specifici
- Definizioni mancanti dei termini chiave
- Petitum formulato in modo debole o incompleto
- Riferimenti normativi mancanti o insufficienti
- Nessi logici interrotti tra fatto, diritto e conclusione{support_context}

Restituisci JSON: {{"findings": [{{
  "claim": "estratto esatto del passaggio da rafforzare",
  "why_weak": "perchè è debole — analisi specifica, non generica",
  "strengthen_suggestion": "riscrittura concreta o lista di interventi",
  "base_normativa": "norma o principio pertinente [DA VERIFICARE]",
  "cosa_manca": "cosa manca specificamente nel passaggio",
  "come_rafforzare": "come riformulare il passaggio per renderlo più solido",
  "impatto_potenziale": "impatto del rafforzamento sulla solidità complessiva",
  "elementi_da_verificare": "cosa verificare prima dell'intervento",
  "severity": "Low|Medium|High|Critical"
}}]}}"""

        all_findings = []
        for chunk in chunk_text(ctx.normalized_text, 6000):
            raw = llm_complete(
                system,
                f"Tipo atto: {ctx.doc_type}, Lingua: {ctx.language}, Modalità: {ctx.analysis_mode}\n\n{chunk}",
                max_tokens=4000,
                include_cross_doc=has_support,
            )
            data = parse_json_response(raw)
            for f in data.get("findings", []):
                if f.get("claim"):
                    all_findings.append(FindingData(
                        severity=f.get("severity", "Medium"),
                        category="Suggerimento di Rafforzamento",
                        finding_type="strengthening",
                        claim=f.get("claim", "")[:300],
                        why_weak=f.get("why_weak", ""),
                        strengthen_suggestion=f.get("strengthen_suggestion", ""),
                        base_normativa=f.get("base_normativa", ""),
                        cosa_manca=f.get("cosa_manca", ""),
                        come_rafforzare=f.get("come_rafforzare", ""),
                        impatto_potenziale=f.get("impatto_potenziale", ""),
                        elementi_da_verificare=f.get("elementi_da_verificare", ""),
                        opponent_angle="",
                        confidence=0.70,
                        module_source=self.name,
                    ))
        return all_findings
