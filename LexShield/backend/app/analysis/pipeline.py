"""
Analysis Pipeline Orchestrator
Runs all module plugins, deduplicates, performs cross-document verification,
and calculates scores.
"""
from __future__ import annotations
import re
from app.analysis.base import DocumentContext, FindingData
from app.analysis.modules.coherence import CoherenceModule
from app.analysis.modules.unsupported_claims import UnsupportedClaimsModule
from app.analysis.modules.ambiguity import AmbiguityModule
from app.analysis.modules.counterargument import CounterargumentModule
from app.analysis.modules.strengthening import StrengtheningModule
from app.analysis.modules.doc_heuristics import DocHeuristicsModule
from app.analysis.scorer import calculate_scores
from app.services.parser import ParsedDocument

MODULES = [
    DocHeuristicsModule(),      # Fast rule-based first
    AmbiguityModule(),          # Fast regex + LLM
    UnsupportedClaimsModule(),  # Regex + LLM
    CoherenceModule(),          # LLM heavy
    CounterargumentModule(),    # LLM adversarial
    StrengtheningModule(),      # LLM, own docs only
]

# Categories that should be cross-checked against support documents
CROSS_DOC_CATEGORIES = {
    "Affermazione Non Supportata",
    "Onere della Prova / Affermazione Non Supportata",
    "Riferimenti Non Verificabili",
    "Incoerenza / Contraddizione",
}


def run_pipeline(
    document_id: str,
    parsed: ParsedDocument,
    doc_type: str,
    doc_role: str,
    language: str,
    analysis_mode: str = "atto_iniziale",
    support_documents: list = None,
) -> tuple[list[FindingData], float, dict, dict]:
    """
    Execute the full analysis pipeline.
    Returns (findings, total_score, subscores, breakdown)
    """
    ctx = DocumentContext(
        document_id=document_id,
        normalized_text=parsed.normalized_text,
        sections=parsed.sections,
        doc_type=doc_type,
        doc_role=doc_role,
        language=language,
        analysis_mode=analysis_mode,
        support_documents=support_documents or [],
        all_documents_text=_build_all_docs_text(support_documents or []),
    )

    all_findings: list[FindingData] = []

    # STEP 1-2: Run all analysis modules
    for module in MODULES:
        try:
            findings = module.analyze(ctx)
            all_findings.extend(findings)
        except Exception as e:
            # Module failure is non-blocking — log and continue
            print(f"[WARN] Module {module.name} failed: {e}")

    # Deduplication: remove near-duplicate claims (same first 80 chars)
    seen_claims = set()
    unique_findings = []
    for f in all_findings:
        key = f.claim[:80].lower().strip()
        if key and key not in seen_claims:
            seen_claims.add(key)
            unique_findings.append(f)

    # STEP 3: Cross-document verification
    if ctx.support_documents:
        unique_findings = _cross_document_verify(unique_findings, ctx)

    # Enrich findings with char positions from text
    _enrich_positions(unique_findings, parsed.normalized_text)

    # Calculate scores
    total_score, subscores, breakdown = calculate_scores(unique_findings)

    return unique_findings, total_score, subscores, breakdown


def _build_all_docs_text(support_documents: list) -> str:
    """Concatenate all support doc texts for search."""
    parts = []
    for doc in support_documents:
        parts.append(f"[{doc.role}: {doc.filename}] {doc.normalized_text}")
    return "\n\n".join(parts)


def _cross_document_verify(findings: list[FindingData], ctx: DocumentContext) -> list[FindingData]:
    """
    STEP 3: Cross-document verification.
    For each finding that claims something is 'unsupported' or 'unfounded',
    check if the support documents contain evidence that contradicts this classification.
    """
    verified = []
    for finding in findings:
        # Only cross-check relevant categories
        if finding.category in CROSS_DOC_CATEGORIES and finding.claim:
            matches = ctx.search_in_support_docs(finding.claim)
            if matches:
                # Evidence found in support docs — reclassify the finding
                doc_refs = [
                    {
                        "document_id": m["document_id"],
                        "filename": m["filename"],
                        "role": m["role"],
                        "relevance": "Supporto trovato nel documento allegato",
                    }
                    for m in matches
                ]
                finding.documenti_correlati = doc_refs

                # Downgrade: don't say "unsupported", say "supported externally"
                match_descriptions = "; ".join(
                    f"{m['filename']} ({m['role']})" for m in matches
                )
                finding.severity = _downgrade_severity(finding.severity)
                finding.finding_type = "cross_document"

                original_why = finding.why_weak
                finding.why_weak = (
                    f"Il punto risulta supportato nei documenti allegati ({match_descriptions}), "
                    f"ma il richiamo non è esplicitato nel testo principale. "
                    f"Analisi originale: {original_why}"
                )
                finding.cosa_manca = (
                    "Il supporto documentale esiste ma non è integrato nel testo dell'atto. "
                    "Si consiglia di rendere esplicito il riferimento al documento di supporto."
                )
                finding.come_rafforzare = (
                    f"Inserire un richiamo esplicito ai documenti: {match_descriptions}. "
                    f"Rendere il collegamento tra affermazione e prova documentale più diretto."
                )
                finding.elementi_da_verificare = (
                    f"Verificare che il contenuto di {match_descriptions} "
                    f"supporti effettivamente il punto in questione e che il richiamo sia sufficientemente specifico."
                )
            else:
                # No support found — check if there are support docs at all
                if ctx.support_documents:
                    doc_names = ", ".join(d.filename for d in ctx.support_documents)
                    finding.documenti_correlati = [
                        {
                            "document_id": d.document_id,
                            "filename": d.filename,
                            "role": d.role,
                            "relevance": "Consultato — nessun supporto trovato",
                        }
                        for d in ctx.support_documents
                    ]
                    finding.elementi_da_verificare = (
                        f"Nessun supporto trovato nei documenti allegati ({doc_names}). "
                        f"Verificare se esistono ulteriori documenti non caricati che possano supportare questo punto."
                    )
        verified.append(finding)
    return verified


def _downgrade_severity(severity: str) -> str:
    """Downgrade severity when external support is found."""
    downgrades = {
        "Critical": "Medium",
        "High": "Medium",
        "Medium": "Low",
        "Low": "Low",
    }
    return downgrades.get(severity, severity)


def _enrich_positions(findings: list[FindingData], text: str) -> None:
    """Try to locate findings in the full text by searching the claim excerpt."""
    for finding in findings:
        if finding.char_start is not None:
            continue
        # Search for claim in text
        claim_clean = finding.claim.strip()
        if len(claim_clean) < 10:
            continue
        # Try exact match first, then partial
        search_text = claim_clean[:100].strip()
        idx = text.find(search_text)
        if idx == -1:
            # Try with normalized whitespace
            search_normalized = re.sub(r"\s+", " ", search_text[:60])
            for m in re.finditer(re.escape(search_normalized), re.sub(r"\s+", " ", text), re.IGNORECASE):
                idx = m.start()
                break
        if idx != -1:
            finding.char_start = idx
            finding.char_end = idx + len(search_text)
            # Also populate estratto_testo if empty
            if not finding.estratto_testo:
                start = max(0, idx - 50)
                end = min(len(text), idx + len(search_text) + 50)
                finding.estratto_testo = text[start:end].strip()
