"""
Module 2: Unsupported Claims Detector
Identifies assertive statements lacking evidence, with cross-document verification.
"""
from __future__ import annotations
import re
from app.analysis.base import BaseModule, DocumentContext, FindingData
from app.services.llm import llm_complete, parse_json_response, chunk_text

# Assertive phrases common in Italian legal docs without evidence follow-up
ASSERTIVE_PATTERNS_IT = [
    r"è\s+(?:pacifico|notorio|evidente|certo|indubbio|comprovato)\s+che",
    r"è\s+(?:stato|stata)\s+(?:accertato|dimostrato|provato)\s+che",
    r"come\s+(?:è\s+)?(?:noto|dimostrato|accertato)",
    r"risulta\s+(?:che|pacifico|evidente)",
    r"nel\s+caso\s+di\s+specie",
    r"senza\s+(?:dubbio|ombra\s+di\s+dubbio)",
]

ASSERTIVE_PATTERNS_EN = [
    r"it\s+is\s+(?:clear|evident|undeniable|established|well-known)\s+that",
    r"as\s+(?:demonstrated|proven|established|shown)",
    r"it\s+is\s+(?:a\s+fact|beyond\s+dispute|undisputed)\s+that",
    r"clearly\s+(?:demonstrates?|shows?|proves?)",
]


class UnsupportedClaimsModule(BaseModule):
    name = "unsupported_claims"

    def analyze(self, ctx: DocumentContext) -> list[FindingData]:
        findings = []
        findings.extend(self._rule_based(ctx))
        findings.extend(self._llm_based(ctx))
        return findings

    def _rule_based(self, ctx: DocumentContext) -> list[FindingData]:
        findings = []
        patterns = ASSERTIVE_PATTERNS_IT if ctx.language == "it" else ASSERTIVE_PATTERNS_EN
        text = ctx.normalized_text

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 200)
                snippet = text[start:end].strip()

                # Check if evidence reference follows (e.g., "doc. X", "all. Y", "(v. Tab. X)")
                evidence_check = text[match.end():match.end() + 300]
                has_evidence = bool(re.search(
                    r"(?:doc\.|all\.|allegat|exhibit|annex|cfr\.|v\.\s*tab|[Vv]ed\.|par\. \d+)",
                    evidence_check
                ))

                if not has_evidence:
                    # Check support documents before flagging
                    support_found = False
                    doc_refs = []
                    if ctx.support_documents:
                        matches_in_support = ctx.search_in_support_docs(snippet[:120])
                        if matches_in_support:
                            support_found = True
                            doc_refs = [
                                {
                                    "document_id": m["document_id"],
                                    "filename": m["filename"],
                                    "role": m["role"],
                                    "relevance": "Supporto trovato",
                                }
                                for m in matches_in_support
                            ]

                    if support_found:
                        # Supported externally — lower severity
                        doc_names = ", ".join(r["filename"] for r in doc_refs)
                        findings.append(FindingData(
                            severity="Low",
                            category="Affermazione Non Supportata",
                            finding_type="cross_document",
                            claim=snippet[:250],
                            why_weak=(
                                f"Affermazione assertiva senza riferimento esplicito nel testo principale, "
                                f"ma supportata nei documenti allegati ({doc_names}). "
                                f"Il richiamo documentale andrebbe reso espresso nel testo."
                            ),
                            opponent_angle=(
                                "La controparte potrà sostenere che il richiamo implicito non è sufficiente. "
                                "È buona prassi rendere esplicito ogni riferimento documentale."
                            ),
                            strengthen_suggestion=(
                                f"Aggiungere riferimento esplicito al documento di supporto: "
                                f"'come documentato in {doc_names}' oppure 'cfr. doc. allegato'."
                            ),
                            come_rafforzare=(
                                f"Integrare nel testo un rinvio esplicito: "
                                f"'(cfr. {doc_names})' subito dopo l'affermazione."
                            ),
                            cosa_manca="Manca il collegamento esplicito tra affermazione e prova documentale.",
                            documenti_correlati=doc_refs,
                            char_start=match.start(),
                            char_end=match.end() + 200,
                            confidence=0.60,
                            module_source=self.name,
                        ))
                    else:
                        findings.append(FindingData(
                            severity="High",
                            category="Affermazione Non Supportata",
                            finding_type="internal",
                            claim=snippet[:250],
                            why_weak=(
                                "Affermazione assertiva senza riferimento a prove, allegati o documenti a supporto. "
                                "Il passaggio presenta l'affermazione come pacifica senza esplicitare su quali elementi si fonda."
                            ),
                            opponent_angle=(
                                "La controparte potrà contestare l'affermazione come apodittica e priva di fondamento probatorio. "
                                "In fase processuale, l'onere della prova grava su chi afferma: senza documentazione "
                                "di supporto, il punto è esposto a eccezione di genericità."
                            ),
                            strengthen_suggestion=(
                                "Aggiungere riferimento specifico: allegato, documento, perizia, testimonianza, o precisare la fonte. "
                                "Formulare il passaggio in modo che il nesso tra affermazione e prova sia evidente."
                            ),
                            cosa_manca=(
                                "Mancano: (1) il riferimento documentale o probatorio; "
                                "(2) l'indicazione della fonte dell'affermazione; "
                                "(3) il collegamento tra fatto affermato e mezzo di prova."
                            ),
                            base_normativa=(
                                "Principio dell'onere della prova: chi vuol far valere un diritto in giudizio deve "
                                "provare i fatti che ne costituiscono il fondamento [DA VERIFICARE: artt. Codice Civile "
                                "in materia di onere probatorio]. L'affermazione apodittica non soddisfa questo requisito."
                            ),
                            impatto_potenziale=(
                                "Medio-alto: un'eccezione di genericità su questo punto potrebbe indebolire "
                                "l'intera linea argomentativa in cui si inserisce."
                            ),
                            elementi_da_verificare=(
                                "Verificare se esistono documenti/prove che supportano l'affermazione e che non sono stati "
                                "allegati. Se esistono, allegarli e inserire il riferimento nel testo."
                            ),
                            char_start=match.start(),
                            char_end=match.end() + 200,
                            confidence=0.80,
                            module_source=self.name,
                        ))
        return findings

    def _llm_based(self, ctx: DocumentContext) -> list[FindingData]:
        has_support = len(ctx.support_documents) > 0
        support_context = ""
        if has_support:
            support_context = f"""

DOCUMENTI DI SUPPORTO DISPONIBILI:
{ctx.get_support_text_summary(max_chars=3000)}

ATTENZIONE: Prima di classificare un'affermazione come "non supportata", verifica se il supporto esiste nei documenti allegati sopra. Se il supporto ESISTE, segnala che "il fondamento esiste nel documento [nome] ma non è richiamato espressamente nel testo principale"."""

        system = f"""Sei un analista legale esperto. Trova affermazioni nel documento che fanno dichiarazioni assertive SENZA fornire prove a supporto.

Concentrati su:
- Affermazioni fattuali presentate come fatti ma prive di supporto probatorio
- Affermazioni sull'intento o conoscenza della controparte senza prova
- Richieste di danni senza quantificazione/documentazione
- Conclusioni giuridiche enunciate senza ragionamento giuridico
- Riferimenti normativi generici senza specificare quali norme si applicano

Per ogni rilievo, fornisci un'analisi APPROFONDITA, non generica.{support_context}

Restituisci JSON: {{"findings": [{{
  "claim": "estratto breve dal testo",
  "why_weak": "spiegazione dettagliata del perchè il punto è vulnerabile, con riferimento al passaggio specifico",
  "severity": "Medium|High|Critical",
  "cosa_manca": "cosa manca specificamente: quali prove, quali riferimenti, quali elementi fattuali",
  "base_normativa": "principio giuridico o norma pertinente (con [DA VERIFICARE] se non certo)",
  "come_attacca_controparte": "come la controparte potrebbe contestare questo punto specifico",
  "come_rafforzare": "come riformulare o integrare il passaggio per renderlo più solido",
  "impatto_potenziale": "quale impatto ha questa debolezza sulla solidità complessiva dell'atto",
  "elementi_da_verificare": "cosa il professionista deve verificare manualmente",
  "documenti_correlati_trovati": "nomi dei documenti di supporto che contengono riferimenti rilevanti (se trovati)"
}}]}}"""

        all_findings = []
        for chunk in chunk_text(ctx.normalized_text, 5000):
            raw = llm_complete(
                system,
                f"Lingua: {ctx.language}\nTipo documento: {ctx.doc_type}\nModalità analisi: {ctx.analysis_mode}\n\nTesto:\n{chunk}",
                max_tokens=4000,
                include_cross_doc=has_support,
            )
            data = parse_json_response(raw)
            for f in data.get("findings", []):
                has_external_support = bool(f.get("documenti_correlati_trovati"))
                all_findings.append(FindingData(
                    severity=f.get("severity", "High") if not has_external_support else "Low",
                    category="Onere della Prova / Affermazione Non Supportata",
                    finding_type="cross_document" if has_external_support else "internal",
                    claim=f.get("claim", "")[:300],
                    why_weak=f.get("why_weak", ""),
                    opponent_angle=f.get("come_attacca_controparte", ""),
                    strengthen_suggestion=f.get("come_rafforzare", ""),
                    cosa_manca=f.get("cosa_manca", ""),
                    base_normativa=f.get("base_normativa", ""),
                    come_attacca_controparte=f.get("come_attacca_controparte", ""),
                    come_rafforzare=f.get("come_rafforzare", ""),
                    impatto_potenziale=f.get("impatto_potenziale", ""),
                    elementi_da_verificare=f.get("elementi_da_verificare", ""),
                    confidence=0.55 if has_external_support else 0.70,
                    module_source=self.name,
                ))
        return all_findings
