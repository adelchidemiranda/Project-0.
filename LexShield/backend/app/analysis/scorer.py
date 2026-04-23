"""
Score Calculator
Weighted average of sub-scores based on findings severity and categories.
"""
from __future__ import annotations
from app.analysis.base import FindingData

# Weights for each sub-score dimension
SUBSCORE_WEIGHTS = {
    "logical_strength": 0.20,
    "evidence_support": 0.20,
    "clarity_precision": 0.15,
    "risk_exposure": 0.15,
    "completeness": 0.15,
    "attack_surface": 0.15,
}

# Severity → penalty points
SEVERITY_PENALTY = {
    "Critical": 25,
    "High": 15,
    "Medium": 8,
    "Low": 3,
}

# Category → which sub-dimension it affects most
CATEGORY_DIMENSION_MAP = {
    "Incoerenza / Contraddizione": "logical_strength",
    "Affermazione Non Supportata": "evidence_support",
    "Onere della Prova / Affermazione Non Supportata": "evidence_support",
    "Ambiguità / Vaghezza Terminologica": "clarity_precision",
    "Ambiguità Strutturale": "clarity_precision",
    "Opportunità di Attacco": "attack_surface",
    "Eccezioni Prevedibili": "attack_surface",
    "Suggerimento di Rafforzamento": "completeness",
    "Elemento Obbligatorio Mancante": "completeness",
    "Linguaggio Eccessivamente Assoluto": "clarity_precision",
    "Riferimenti Non Verificabili": "evidence_support",
    "Rischio Procedurale": "risk_exposure",
    "Rischio Contrattuale": "risk_exposure",
}


def calculate_scores(findings: list[FindingData]) -> tuple[float, dict, dict]:
    """
    Returns (total_score, subscores, score_breakdown).
    total_score: 0–100 (100 = perfect)
    subscores: {dimension: 0–100}
    score_breakdown: explanation dict
    """
    # Start all dimensions at 100
    raw_scores = {dim: 100.0 for dim in SUBSCORE_WEIGHTS}
    dimension_hits = {dim: [] for dim in SUBSCORE_WEIGHTS}

    for finding in findings:
        penalty = SEVERITY_PENALTY.get(finding.severity, 5) * finding.confidence
        dim = CATEGORY_DIMENSION_MAP.get(finding.category, "logical_strength")
        raw_scores[dim] = max(0, raw_scores[dim] - penalty)
        dimension_hits[dim].append({
            "finding_id": finding.id,
            "severity": finding.severity,
            "claim": finding.claim[:80],
        })

    # Normalize to 0-100
    subscores = {dim: round(max(0.0, min(100.0, score)), 1) for dim, score in raw_scores.items()}

    # Weighted total
    total = sum(
        subscores[dim] * weight
        for dim, weight in SUBSCORE_WEIGHTS.items()
    )
    total = round(total, 1)

    # Breakdown: top contributors to score loss
    breakdown = {
        "total_score": total,
        "total_findings": len(findings),
        "critical_count": sum(1 for f in findings if f.severity == "Critical"),
        "high_count": sum(1 for f in findings if f.severity == "High"),
        "medium_count": sum(1 for f in findings if f.severity == "Medium"),
        "low_count": sum(1 for f in findings if f.severity == "Low"),
        "dimension_hits": {k: len(v) for k, v in dimension_hits.items()},
        "score_label": _score_label(total),
    }

    return total, subscores, breakdown


def _score_label(score: float) -> str:
    if score >= 85:
        return "Forte"
    elif score >= 70:
        return "Accettabile"
    elif score >= 50:
        return "Vulnerabile"
    elif score >= 30:
        return "Debole"
    else:
        return "Critico"
