import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.db.database import get_db
from app.models import (
    Document, Analysis, Finding, AnalysisStatus, User,
    AnalysisSession, SessionDocument, AnalysisMode, SupportDocumentRole
)
from app.auth import get_anonymous_user
from app.config import get_settings
from app.worker import run_analysis_task, run_session_analysis_task

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    doc_type: str
    doc_role: str
    language: str
    status: str
    normalized_text: Optional[str] = None
    sections: Optional[dict] = None

    class Config:
        from_attributes = True


class SessionDocumentInfo(BaseModel):
    document_id: str
    filename: str
    role: str

    class Config:
        from_attributes = True


class AnalysisSessionResponse(BaseModel):
    session_id: str
    mode: str
    status: str
    main_document_id: str
    main_document_filename: str
    support_documents: list[SessionDocumentInfo] = []

    class Config:
        from_attributes = True


# ── Legacy single-doc upload (kept for backward compat) ────────────

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: Optional[UploadFile] = File(None),
    pasted_text: Optional[str] = Form(None),
    doc_type: str = Form("altro"),
    doc_role: str = Form("mine"),
    language: str = Form("it"),
    jurisdiction: str = Form("IT"),
    project_id: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    if not file and not pasted_text:
        raise HTTPException(status_code=400, detail="Provide either a file or pasted text")

    doc = await _save_uploaded_file(file, pasted_text, doc_type, doc_role, language, jurisdiction, project_id, current_user, db)
    await db.commit()
    background_tasks.add_task(run_analysis_task, doc.id)

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        doc_type=doc.doc_type,
        doc_role=doc.doc_role,
        language=doc.language,
        status=doc.status,
    )


# ── NEW: Session-based multi-document upload ───────────────────────

@router.post("/analyze-session", response_model=AnalysisSessionResponse, status_code=201)
async def create_analysis_session(
    mode: str = Form("atto_iniziale"),
    main_file: Optional[UploadFile] = File(None),
    main_pasted_text: Optional[str] = Form(None),
    main_doc_type: str = Form("atto"),
    language: str = Form("it"),
    jurisdiction: str = Form("IT"),
    # Support files are sent as arrays
    support_files: list[UploadFile] = File(default=[]),
    support_roles: str = Form(default=""),  # comma-separated roles
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    """
    Create a new analysis session with a main document and optional support documents.
    Triggers background analysis of the complete document set.
    """
    if not main_file and not main_pasted_text:
        raise HTTPException(status_code=400, detail="Provide a main file or pasted text")

    # Validate mode
    if mode not in [m.value for m in AnalysisMode]:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Use 'atto_iniziale' or 'contestazione'")

    # Save main document
    doc_role = "mine"  # Main document is always 'mine'
    main_doc = await _save_uploaded_file(
        main_file, main_pasted_text, main_doc_type, doc_role,
        language, jurisdiction, None, current_user, db
    )
    await db.flush()

    # Create analysis session
    session = AnalysisSession(
        user_id=current_user.id,
        mode=mode,
        main_document_id=main_doc.id,
        status=AnalysisStatus.pending,
    )
    db.add(session)
    await db.flush()

    # Parse support roles
    roles_list = [r.strip() for r in support_roles.split(",") if r.strip()] if support_roles else []
    valid_roles = [r.value for r in SupportDocumentRole]

    # Save support documents
    support_doc_infos = []
    for idx, sup_file in enumerate(support_files):
        role = roles_list[idx] if idx < len(roles_list) else "altro"
        if role not in valid_roles:
            role = "altro"

        sup_doc = await _save_uploaded_file(
            sup_file, None, "altro", "opponent",
            language, jurisdiction, None, current_user, db
        )
        await db.flush()

        session_doc = SessionDocument(
            session_id=session.id,
            document_id=sup_doc.id,
            role=role,
        )
        db.add(session_doc)
        support_doc_infos.append(SessionDocumentInfo(
            document_id=sup_doc.id,
            filename=sup_doc.filename,
            role=role,
        ))

    await db.commit()

    # Trigger background analysis
    background_tasks.add_task(run_session_analysis_task, session.id)

    return AnalysisSessionResponse(
        session_id=session.id,
        mode=session.mode,
        status=session.status,
        main_document_id=main_doc.id,
        main_document_filename=main_doc.filename,
        support_documents=support_doc_infos,
    )


# ── Existing endpoints ─────────────────────────────────────────────

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/status")
async def get_status(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": doc_id, "status": doc.status}


@router.get("/session/{session_id}/status")
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    result = await db.execute(
        select(AnalysisSession).where(
            AnalysisSession.id == session_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "status": session.status,
        "main_document_id": session.main_document_id,
    }


# ── Helper ─────────────────────────────────────────────────────────

async def _save_uploaded_file(
    file: Optional[UploadFile],
    pasted_text: Optional[str],
    doc_type: str,
    doc_role: str,
    language: str,
    jurisdiction: str,
    project_id: Optional[str],
    current_user: User,
    db: AsyncSession,
) -> Document:
    """Save an uploaded file or pasted text to disk and create a Document record."""
    os.makedirs(settings.upload_dir, exist_ok=True)

    if file:
        ext = Path(file.filename).suffix.lower().lstrip(".")
        if ext not in ("pdf", "docx", "txt"):
            raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT allowed")
        file_id = str(uuid.uuid4())
        file_path = os.path.join(settings.upload_dir, f"{file_id}.{ext}")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        filename = file.filename
        file_type = ext
    else:
        ext = "txt"
        file_id = str(uuid.uuid4())
        file_path = os.path.join(settings.upload_dir, f"{file_id}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pasted_text)
        filename = "pasted_text.txt"
        file_type = "txt"

    doc = Document(
        user_id=current_user.id,
        project_id=project_id,
        filename=filename,
        file_type=file_type,
        doc_type=doc_type,
        doc_role=doc_role,
        language=language,
        jurisdiction=jurisdiction,
        file_path=file_path,
        status=AnalysisStatus.pending,
    )
    db.add(doc)
    await db.flush()
    return doc
