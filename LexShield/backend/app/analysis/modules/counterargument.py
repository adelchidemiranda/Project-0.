"""
Module 4: Counterargument Generator
Generates attack lines from opponent's perspective with deep legal analysis.
In contestazione mode, uses support documents for richer context.
"""
from __future__ import annotations
from app.analysis.base import BaseModule, DocumentContext, FindingData
from app.services.llm import llm_complete, parse_json_response, chunk_text


class CounterargumentModule(BaseModule):
    name = "counterargument"

    def analyze(self, ctx: DocumentContext) -> list[FindingData]:
        has_support = len(ctx.support_documents) > 0
        support_context = ""
        if has_support:
            support_context = f"""

DOCUMENTI DI SUPPORTO/CONTESTO:
{ctx.get_support_text_summary(max_chars=3000)}

Usa questi documenti per:
- Individuare punti del documento principale che i documenti di supporto contraddicono o indeboliscono
- Trovare elementi nei documenti di supporto che possono essere usati come argomentazioni contrarie
- Verificare se le affermazioni del documento principale sono coerenti con i documenti allegati"""

        perspective = "dell'attore/ricorrente" if ctx.doc_role == "mine" else "della controparte"
        target = "della controparte" if ctx.doc_role == "mine" else "del cliente"

        system = f"""Sei uno stratega legale avversario esperto in diritto italiano. Il tuo compito: analizzare questo documento {perspective} e generare le ARGOMENTAZIONI PIÙ FORTI che {target} potrebbe utilizzare.

Genera 4-7 linee di attacco concrete sui punti più deboli del documento.

Per ogni controargomentazione fornisci:
- Il PASSAGGIO SPECIFICO del testo che viene attaccato (estratto esatto)
- La BASE GIURIDICA dell'attacco (principio o norma pertinente, con [DA VERIFICARE] se non certo)
- L'ARGOMENTAZIONE COMPLETA come verrebbe formulata in un atto processuale
- La GRAVITÀ dell'attacco (quanto è dannoso per la posizione avversaria)
- COME DIFENDERSI da questo attacco (se il doc è del cliente)
- L'IMPATTO POTENZIALE sull'esito della causa
- ELEMENTI DA VERIFICARE per il professionista{support_context}

Restituisci JSON: {{"findings": [{{
  "claim": "estratto esatto del passaggio attaccato",
  "why_weak": "perchè questo punto è vulnerabile — spiegazione concreta e specifica",
  "attack_suggestion": "linea di attacco formulata in linguaggio giuridico processuale",
  "opponent_angle": "controargomentazione completa e sviluppata",
  "base_normativa": "principio o norma pertinente [DA VERIFICARE]",
  "impatto_potenziale": "impatto sull'esito della causa",
  "come_rafforzare": "come difendersi da questo attacco o come prevenirlo",
  "elementi_da_verificare": "cosa verificare",
  "severity": "Low|Medium|High|Critical"
}}]}}"""

        all_findings = []
        text_sample = ctx.normalized_text[:8000]
        raw = llm_complete(
            system,
            f"Tipo documento: {ctx.doc_type}\nLingua: {ctx.language}\nModalità: {ctx.analysis_mode}\n\nTesto completo:\n{text_sample}",
            max_tokens=4000,
            include_cross_doc=has_support,
        )
        data = parse_json_response(raw)

        for f in data.get("findings", []):
            if f.get("claim"):
                all_findings.append(FindingData(
                    severity=f.get("severity", "High"),
                    category="Opportunità di Attacco" if ctx.doc_role == "opponent" else "Eccezioni Prevedibili",
                    finding_type="attack" if ctx.doc_role == "opponent" else "internal",
                    claim=f.get("claim", "")[:300],
                    why_weak=f.get("why_weak", ""),
                    opponent_angle=f.get("opponent_angle", ""),
                    attack_suggestion=f.get("attack_suggestion", ""),
                    strengthen_suggestion="" if ctx.doc_role == "opponent" else f.get("come_rafforzare", ""),
                    base_normativa=f.get("base_normativa", ""),
                    impatto_potenziale=f.get("impatto_potenziale", ""),
                    come_attacca_controparte=f.get("opponent_angle", ""),
                    come_rafforzare=f.get("come_rafforzare", ""),
                    elementi_da_verificare=f.get("elementi_da_verificare", ""),
                    confidence=0.75,
                    module_source=self.name,
                ))

        return all_findings
