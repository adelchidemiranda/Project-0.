from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.db.database import get_db
from app.models import Document, Analysis, Finding, User, AnalysisSession, SessionDocument
from app.auth import get_current_user
from app.services.report import generate_pdf_report
import io

router = APIRouter(prefix="/analysis", tags=["analysis"])


class FindingResponse(BaseModel):
    id: str
    severity: str
    category: str
    finding_type: str = "internal"
    section_id: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    sezione_documento: Optional[str] = None
    estratto_testo: Optional[str] = None
    claim: str
    why_weak: str
    opponent_angle: Optional[str] = None
    strengthen_suggestion: Optional[str] = None
    attack_suggestion: Optional[str] = None
    # Deep analysis fields
    cosa_manca: Optional[str] = None
    cosa_contraddetto: Optional[str] = None
    base_normativa: Optional[str] = None
    come_attacca_controparte: Optional[str] = None
    come_rafforzare: Optional[str] = None
    adattamento_contesto: Optional[str] = None
    impatto_potenziale: Optional[str] = None
    elementi_da_verificare: Optional[str] = None
    documenti_correlati: Optional[dict] = None
    confidence: float = 0.7
    module_source: Optional[str] = None

    class Config:
        from_attributes = True


class SessionDocInfo(BaseModel):
    document_id: str
    filename: str
    role: str

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: str
    document_id: str
    session_id: Optional[str] = None
    status: str
    total_score: Optional[float] = None
    subscores: Optional[dict] = None
    score_breakdown: Optional[dict] = None
    documents_considered: Optional[dict] = None
    findings: list[FindingResponse] = []
    # Session info
    analysis_mode: Optional[str] = None
    support_documents: list[SessionDocInfo] = []

    class Config:
        from_attributes = True


@router.get("/{document_id}", response_model=AnalysisResponse)
async def get_analysis(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify ownership
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    analysis_result = await db.execute(
        select(Analysis).where(Analysis.document_id == document_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found yet")

    findings_result = await db.execute(
        select(Finding).where(Finding.analysis_id == analysis.id).order_by(Finding.char_start)
    )
    findings = findings_result.scalars().all()

    # Get session info if exists
    analysis_mode = None
    support_docs_info = []
    if analysis.session_id:
        session_result = await db.execute(
            select(AnalysisSession).where(AnalysisSession.id == analysis.session_id)
        )
        session = session_result.scalar_one_or_none()
        if session:
            analysis_mode = session.mode
            # Get support docs
            sd_result = await db.execute(
                select(SessionDocument).where(SessionDocument.session_id == session.id)
            )
            session_docs = sd_result.scalars().all()
            for sd in session_docs:
                sup_doc_result = await db.execute(
                    select(Document).where(Document.id == sd.document_id)
                )
                sup_doc = sup_doc_result.scalar_one_or_none()
                if sup_doc:
                    support_docs_info.append(SessionDocInfo(
                        document_id=sup_doc.id,
                        filename=sup_doc.filename,
                        role=sd.role,
                    ))

    return AnalysisResponse(
        id=analysis.id,
        document_id=document_id,
        session_id=analysis.session_id,
        status=analysis.status,
        total_score=analysis.total_score,
        subscores=analysis.subscores,
        score_breakdown=analysis.score_breakdown,
        documents_considered=analysis.documents_considered,
        findings=[FindingResponse.model_validate(f) for f in findings],
        analysis_mode=analysis_mode,
        support_documents=support_docs_info,
    )


@router.get("/session/{session_id}", response_model=AnalysisResponse)
async def get_session_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analysis results for a complete session (main + support docs)."""
    session_result = await db.execute(
        select(AnalysisSession).where(
            AnalysisSession.id == session_id,
            AnalysisSession.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get analysis for the main document in this session
    analysis_result = await db.execute(
        select(Analysis).where(Analysis.session_id == session_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found yet")

    findings_result = await db.execute(
        select(Finding).where(Finding.analysis_id == analysis.id).order_by(Finding.char_start)
    )
    findings = findings_result.scalars().all()

    # Get support docs info
    sd_result = await db.execute(
        select(SessionDocument).where(SessionDocument.session_id == session.id)
    )
    session_docs = sd_result.scalars().all()
    support_docs_info = []
    for sd in session_docs:
        sup_doc_result = await db.execute(
            select(Document).where(Document.id == sd.document_id)
        )
        sup_doc = sup_doc_result.scalar_one_or_none()
        if sup_doc:
            support_docs_info.append(SessionDocInfo(
                document_id=sup_doc.id,
                filename=sup_doc.filename,
                role=sd.role,
            ))

    return AnalysisResponse(
        id=analysis.id,
        document_id=session.main_document_id,
        session_id=session_id,
        status=analysis.status,
        total_score=analysis.total_score,
        subscores=analysis.subscores,
        score_breakdown=analysis.score_breakdown,
        documents_considered=analysis.documents_considered,
        findings=[FindingResponse.model_validate(f) for f in findings],
        analysis_mode=session.mode,
        support_documents=support_docs_info,
    )


@router.get("/{document_id}/report")
async def export_report(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    analysis_result = await db.execute(
        select(Analysis).where(Analysis.document_id == document_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis or analysis.status != "done":
        raise HTTPException(status_code=400, detail="Analysis not complete")

    findings_result = await db.execute(
        select(Finding).where(Finding.analysis_id == analysis.id)
    )
    findings = findings_result.scalars().all()

    pdf_bytes = generate_pdf_report(doc, analysis, findings)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lexshield_report_{document_id[:8]}.pdf"'},
    )


@router.post("/{document_id}/findings/{finding_id}/flag")
async def flag_finding(
    document_id: str,
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding_result = await db.execute(
        select(Finding).where(Finding.id == finding_id)
    )
    finding = finding_result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.is_flagged = not finding.is_flagged
    return {"flagged": finding.is_flagged}
