"""
Base interface that all analysis modules must implement.
Extended with multi-document context and enriched finding fields.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class SupportDocData:
    """Parsed data from a support document attached to the analysis session."""
    document_id: str
    filename: str
    role: str               # SupportDocumentRole value
    normalized_text: str
    sections: list


@dataclass
class FindingData:
    # Classification
    severity: str          # Low | Medium | High | Critical
    category: str
    finding_type: str = "internal"   # internal | cross_document | strengthening | attack | normative_gap

    # Core content
    claim: str = ""                  # Short excerpt from main document text
    why_weak: str = ""

    # Original suggestion fields (kept for backward compat)
    opponent_angle: str = ""
    strengthen_suggestion: str = ""
    attack_suggestion: str = ""

    # NEW: Deep analysis fields
    sezione_documento: str = ""             # section title in main document
    estratto_testo: str = ""                # exact excerpt from main doc
    cosa_manca: str = ""                    # detailed: what is missing
    cosa_contraddetto: str = ""             # what can be contradicted
    base_normativa: str = ""                # normative/legal basis (with [DA VERIFICARE])
    come_attacca_controparte: str = ""      # how counterparty could attack this point
    come_rafforzare: str = ""               # how to strengthen this point
    adattamento_contesto: str = ""          # adaptation to specific context
    impatto_potenziale: str = ""            # potential impact description
    elementi_da_verificare: str = ""        # checklist for human lawyer
    documenti_correlati: list = field(default_factory=list)  # [{doc_id, filename, role, relevance}]

    # Position in text
    section_id: Optional[str] = None
    paragraph_id: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    # Metadata
    confidence: float = 0.7
    module_source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class DocumentContext:
    document_id: str
    normalized_text: str
    sections: list         # list of Section objects
    doc_type: str
    doc_role: str          # mine | opponent
    language: str

    # NEW: Multi-document context
    analysis_mode: str = "atto_iniziale"    # atto_iniziale | contestazione
    support_documents: list[SupportDocData] = field(default_factory=list)
    all_documents_text: str = ""            # concatenated text of all support docs for search

    def get_support_docs_by_role(self, role: str) -> list[SupportDocData]:
        """Get all support documents with a specific role."""
        return [d for d in self.support_documents if d.role == role]

    def get_support_text_summary(self, max_chars: int = 4000) -> str:
        """Build a summary of all support documents for LLM context."""
        if not self.support_documents:
            return ""
        parts = []
        chars_used = 0
        for doc in self.support_documents:
            header = f"\n--- DOCUMENTO DI SUPPORTO: {doc.filename} (Ruolo: {doc.role}) ---\n"
            available = max_chars - chars_used - len(header)
            if available <= 200:
                break
            text_excerpt = doc.normalized_text[:available]
            parts.append(header + text_excerpt)
            chars_used += len(header) + len(text_excerpt)
        return "\n".join(parts)

    def search_in_support_docs(self, query: str) -> list[dict]:
        """Search for a text fragment across all support documents. Returns matches."""
        import re
        query_clean = re.sub(r"\s+", " ", query.strip().lower())
        if len(query_clean) < 10:
            return []
        results = []
        for doc in self.support_documents:
            doc_text_lower = re.sub(r"\s+", " ", doc.normalized_text.lower())
            # Try exact match first
            idx = doc_text_lower.find(query_clean[:80])
            if idx != -1:
                start = max(0, idx - 100)
                end = min(len(doc.normalized_text), idx + len(query_clean) + 200)
                results.append({
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "role": doc.role,
                    "match_excerpt": doc.normalized_text[start:end],
                    "match_type": "exact",
                })
            else:
                # Try key phrases (first 5 meaningful words)
                words = [w for w in query_clean.split() if len(w) > 3][:5]
                if words:
                    phrase = " ".join(words[:3])
                    idx2 = doc_text_lower.find(phrase)
                    if idx2 != -1:
                        start = max(0, idx2 - 100)
                        end = min(len(doc.normalized_text), idx2 + 300)
                        results.append({
                            "document_id": doc.document_id,
                            "filename": doc.filename,
                            "role": doc.role,
                            "match_excerpt": doc.normalized_text[start:end],
                            "match_type": "partial",
                        })
        return results


class BaseModule:
    """Interface for all analysis plugin modules."""
    name: str = "base"

    def analyze(self, context: DocumentContext) -> list[FindingData]:
        raise NotImplementedError
