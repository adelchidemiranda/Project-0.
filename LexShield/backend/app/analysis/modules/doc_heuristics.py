"""
Module 6: Document-Type Heuristics
Rule-based checks tailored to specific document types.
"""
from __future__ import annotations
import re
from app.analysis.base import BaseModule, DocumentContext, FindingData


# Required clauses/elements by document type
REQUIRED_ELEMENTS = {
    "contratto": {
        "it": [
            ("parti", r"(?:le\s+parti\s+sono|tra\s+i\s+sottoscritti|tra\s+le\s+parti)", "Identificazione delle parti"),
            ("oggetto", r"(?:oggetto\s+del\s+contratto|ha\s+per\s+oggetto)", "Oggetto del contratto"),
            ("durata", r"(?:durata|validità|periodo|scadenza|termine\s+del\s+contratto)", "Durata/scadenza"),
            ("corrispettivo", r"(?:corrispettivo|prezzo|compenso|importo|€|EUR)", "Corrispettivo/prezzo"),
            ("recesso", r"(?:recesso|rescissione|risoluzione|disdetta)", "Clausola di recesso"),
            ("foro", r"(?:foro\s+competente|giurisdizione|tribunale\s+di)", "Foro competente"),
            ("legge", r"(?:legge\s+applicabile|diritto\s+applicabile|legge\s+italiana|governed\s+by)", "Legge applicabile"),
        ]
    },
    "diffida": {
        "it": [
            ("destinatario", r"(?:spett\.?le|alla\s+soc\.|al\s+sig\.|gentile)", "Destinatario identificato"),
            ("termine", r"(?:entro\s+\d+|termine\s+di|giorni\s+dalla|entro\s+e\s+non\s+oltre)", "Termine perentorio"),
            ("richiesta", r"(?:si\s+diffida|si\s+intima|si\s+richiede\s+formalmente)", "Intimazione formale"),
            ("riserva", r"(?:riserva\s+di\s+agire|ogni\s+azione|tutela|giudiziale)", "Riserva di azioni legali"),
        ]
    },
    "atto": {
        "it": [
            ("petitum", r"(?:voglia\s+il\s+tribunale|si\s+chiede\s+che|si\s+domanda\s+che|condannare|accertare)", "Petitum"),
            ("causa_petendi", r"(?:causa\s+petendi|in\s+fatto|in\s+diritto|premesso\s+che)", "Causa petendi"),
            ("prove", r"(?:si\s+producono|produzione\s+documenti|mezzi\s+di\s+prova|si\s+offrono)", "Mezzi di prova"),
            ("valore", r"(?:valore\s+della\s+causa|si\s+dichiara\s+il\s+valore)", "Valore della causa"),
        ]
    },
}


class DocHeuristicsModule(BaseModule):
    name = "doc_heuristics"

    def analyze(self, ctx: DocumentContext) -> list[FindingData]:
        findings = []

        doc_type_key = ctx.doc_type.lower()
        lang = ctx.language.lower()

        required = REQUIRED_ELEMENTS.get(doc_type_key, {}).get(lang, [])

        for key, pattern, label in required:
            if not re.search(pattern, ctx.normalized_text, re.IGNORECASE):
                findings.append(FindingData(
                    severity="High",
                    category="Elemento Obbligatorio Mancante",
                    finding_type="internal",
                    claim=f"[Elemento non trovato nel documento]",
                    why_weak=f'Il documento di tipo "{ctx.doc_type}" non contiene "{label}". Si tratta di un elemento essenziale per questo tipo di atto.',
                    opponent_angle=f'La controparte potrà eccepire la nullità o l\'incompletezza del documento per assenza di "{label}".',
                    strengthen_suggestion=f'Aggiungere esplicitamente una sezione dedicata a "{label}" con dati precisi e circostanziati.',
                    confidence=0.88,
                    module_source=self.name,
                ))

        # Additional cross-cutting checks
        findings.extend(self._check_absolute_language(ctx))
        findings.extend(self._check_undefined_references(ctx))

        return findings

    def _check_absolute_language(self, ctx: DocumentContext) -> list[FindingData]:
        """Flag overly absolute language that is hard to defend."""
        findings = []
        absolute_patterns = [
            r"\bnunca\b", r"\bjamás\b",  # Spanish false friends sometimes creep in
            r"\bmai\s+(?:e\s+poi\s+mai|in\s+nessun\s+caso)\b",
            r"\bassolutamente\s+(?:sempre|mai|niente|tutto)\b",
            r"\bin\s+ogni\s+caso\s+e\s+senza\s+eccezione", 
            r"\balways\b.*\bwithout\s+exception\b",
            r"\bnever\s+under\s+any\s+circumstances?\b",
        ]
        for pat in absolute_patterns:
            for m in re.finditer(pat, ctx.normalized_text, re.IGNORECASE):
                start = max(0, m.start() - 80)
                end = min(len(ctx.normalized_text), m.end() + 100)
                findings.append(FindingData(
                    severity="Medium",
                    category="Linguaggio Eccessivamente Assoluto",
                    claim=ctx.normalized_text[start:end].strip()[:250],
                    why_weak="Linguaggio assoluto ('mai', 'sempre', 'in ogni caso senza eccezione') è difficile da mantenere e offre facile presa alla controparte.",
                    opponent_angle="La controparte dimostrerà anche un solo caso contrario per smontare l'intera affermazione.",
                    strengthen_suggestion="Riformulare con qualificazioni: 'nella generalità dei casi', 'salvo forza maggiore', 'nei limiti del ragionevole'.",
                    char_start=m.start(),
                    char_end=m.end(),
                    confidence=0.80,
                    module_source=self.name,
                ))
        return findings

    def _check_undefined_references(self, ctx: DocumentContext) -> list[FindingData]:
        """Find references to undefined docs/exhibits."""
        findings = []
        ref_pattern = r"(?:all(?:egat)?[oi]?\.?\s*[A-Z\d]+|doc\.\s*\d+|exhibit\s+[A-Z\d]+)"
        refs = re.findall(ref_pattern, ctx.normalized_text, re.IGNORECASE)
        if refs and len(refs) > 0:
            # Check if there's an allegati/attachments section
            has_allegati = bool(re.search(r"(?:elenco\s+allegati|allegati\s*:|list\s+of\s+exhibits)", ctx.normalized_text, re.IGNORECASE))
            if not has_allegati and len(refs) > 1:
                findings.append(FindingData(
                    severity="Medium",
                    category="Riferimenti Non Verificabili",
                    claim=f"Trovati {len(refs)} riferimenti ad allegati/documenti ({', '.join(set(refs)[:5])})",
                    why_weak="Il documento fa riferimento ad allegati/documenti ma non contiene un elenco degli stessi. In caso di contestazione, l'elenco completo degli allegati è essenziale.",
                    opponent_angle="La controparte potrà contestare che taluni allegati non esistano o siano diversi da quanto indicato.",
                    strengthen_suggestion="Aggiungere in calce al documento 'Elenco Allegati' con numerazione progressiva, titolo e numero di pagine di ciascuno.",
                    confidence=0.78,
                    module_source=self.name,
                ))
        return findings
