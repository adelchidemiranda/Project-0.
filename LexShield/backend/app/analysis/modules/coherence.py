"""
Module 1: Coherence & Contradiction Detector
Finds internal contradictions and cross-document inconsistencies.
"""
from __future__ import annotations
import re
from app.analysis.base import BaseModule, DocumentContext, FindingData
from app.services.llm import llm_complete, parse_json_response, chunk_text


class CoherenceModule(BaseModule):
    name = "coherence"

    def analyze(self, ctx: DocumentContext) -> list[FindingData]:
        findings = []
        findings.extend(self._rule_based(ctx))
        findings.extend(self._llm_based(ctx))
        if ctx.support_documents and ctx.analysis_mode == "contestazione":
            findings.extend(self._cross_doc_coherence(ctx))
        return findings

    def _rule_based(self, ctx: DocumentContext) -> list[FindingData]:
        """Fast rule-based checks for obvious contradictions."""
        findings = []
        # Rule-based checks are minimal; the LLM does the heavy lifting
        return findings

    def _llm_based(self, ctx: DocumentContext) -> list[FindingData]:
        system = """Sei un analista legale specializzato nell'individuazione di CONTRADDIZIONI INTERNE nei documenti.
Analizza il testo e trova:
1. Date contraddittorie o illogiche (es. data firma successiva a data obbligo)
2. Importi che si contraddicono tra loro
3. Definizioni usate in modo incoerente
4. Parti nominate diversamente in sezioni diverse
5. Obbligazioni formulate in modo contraddittorio
6. Riferimenti normativi incongruenti tra loro

Per ogni contraddizione, spiega:
- Il PASSAGGIO PRECISO dove emerge la contraddizione
- PERCHÉ è una contraddizione (non solo "è incoerente")
- QUALE IMPATTO ha sulla solidità dell'atto
- COME la controparte potrebbe sfruttarla
- COME correggerla

Restituisci JSON: {"findings": [{"claim": "estratto breve", "why_weak": "spiegazione dettagliata", "severity": "Low|Medium|High|Critical", "opponent_angle": "come la controparte sfrutta questa contraddizione", "strengthen_suggestion": "come correggere", "base_normativa": "principio giuridico rilevante con [DA VERIFICARE]", "impatto_potenziale": "impatto sulla causa", "section_id": "S0"}]}"""

        all_findings = []
        for chunk in chunk_text(ctx.normalized_text, 6000):
            raw = llm_complete(system, f"Tipo documento: {ctx.doc_type}\nModalità: {ctx.analysis_mode}\n\nTesto:\n{chunk}", max_tokens=4000)
            data = parse_json_response(raw)
            for f in data.get("findings", []):
                all_findings.append(FindingData(
                    severity=f.get("severity", "Medium"),
                    category="Incoerenza / Contraddizione",
                    finding_type="internal",
                    claim=f.get("claim", "")[:300],
                    why_weak=f.get("why_weak", ""),
                    opponent_angle=f.get("opponent_angle", ""),
                    strengthen_suggestion=f.get("strengthen_suggestion", ""),
                    base_normativa=f.get("base_normativa", ""),
                    impatto_potenziale=f.get("impatto_potenziale", ""),
                    section_id=f.get("section_id"),
                    confidence=0.75,
                    module_source=self.name,
                ))
        return all_findings

    def _cross_doc_coherence(self, ctx: DocumentContext) -> list[FindingData]:
        """Check coherence between main document and support documents (contestazione mode)."""
        support_summary = ctx.get_support_text_summary(max_chars=4000)
        if not support_summary:
            return []

        system = """Sei un analista legale. Confronta il documento principale con i documenti di supporto allegati.
Individua:
1. Contraddizioni tra ciò che afferma il documento principale e ciò che risulta dai documenti di supporto
2. Dati/date/importi discordanti tra i documenti
3. Fatti negati nel documento principale ma confermati in documenti allegati
4. Fatti affermati nel documento principale ma smentiti dai documenti allegati

Per ogni incongruenza cross-documentale:
- Indica il PASSAGGIO del documento principale
- Indica il PASSAGGIO del documento di supporto che lo contraddice
- Spiega l'IMPATTO della discrepanza
- Suggerisci come procedere

Restituisci JSON: {"findings": [{"claim": "passaggio del doc principale", "why_weak": "spiegazione dell'incongruenza con riferimento al doc di supporto", "severity": "Medium|High|Critical", "opponent_angle": "come la controparte usa questa discrepanza", "strengthen_suggestion": "come risolvere", "documenti_correlati_trovati": "nome del doc di supporto rilevante"}]}"""

        main_excerpt = ctx.normalized_text[:5000]
        raw = llm_complete(
            system,
            f"DOCUMENTO PRINCIPALE:\n{main_excerpt}\n\n{support_summary}",
            max_tokens=4000,
            include_cross_doc=True,
        )
        data = parse_json_response(raw)

        findings = []
        for f in data.get("findings", []):
            if f.get("claim"):
                findings.append(FindingData(
                    severity=f.get("severity", "High"),
                    category="Incoerenza / Contraddizione",
                    finding_type="cross_document",
                    claim=f.get("claim", "")[:300],
                    why_weak=f.get("why_weak", ""),
                    opponent_angle=f.get("opponent_angle", ""),
                    strengthen_suggestion=f.get("strengthen_suggestion", ""),
                    confidence=0.72,
                    module_source=self.name,
                ))
        return findings
