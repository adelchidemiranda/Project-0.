import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Integer, Float, DateTime, Boolean,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    lawyer = "lawyer"
    reviewer = "reviewer"


class DocumentRole(str, enum.Enum):
    mine = "mine"
    opponent = "opponent"


class DocumentType(str, enum.Enum):
    atto = "atto"
    contratto = "contratto"
    lettera = "lettera"
    parere = "parere"
    memoria = "memoria"
    diffida = "diffida"
    ricorso = "ricorso"
    citazione = "citazione"
    comparsa = "comparsa"
    clausola = "clausola"
    altro = "altro"


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"


class FindingSeverity(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


# ── NEW ENUMS ──────────────────────────────────────────────────────

class AnalysisMode(str, enum.Enum):
    atto_iniziale = "atto_iniziale"       # Standalone document analysis
    contestazione = "contestazione"        # Rebuttal/response to another act


class SupportDocumentRole(str, enum.Enum):
    atto_controparte = "atto_controparte"
    sentenza = "sentenza"
    provvedimento = "provvedimento"
    contratto = "contratto"
    allegato = "allegato"
    comunicazione = "comunicazione"
    memoria = "memoria"
    documento_probatorio = "documento_probatorio"
    altro = "altro"


class FindingType(str, enum.Enum):
    internal = "internal"                  # Weakness within main doc
    cross_document = "cross_document"      # Issue from comparing documents
    strengthening = "strengthening"        # Point to reinforce
    attack = "attack"                      # Point to attack
    normative_gap = "normative_gap"        # Missing legal basis


# ── EXISTING MODELS ────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    firm_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.lawyer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    analysis_sessions: Mapped[list["AnalysisSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | docx | txt
    doc_type: Mapped[str] = mapped_column(String(50), default=DocumentType.altro)
    doc_role: Mapped[str] = mapped_column(String(20), default=DocumentRole.mine)
    language: Mapped[str] = mapped_column(String(10), default="it")
    jurisdiction: Mapped[str] = mapped_column(String(50), default="IT")
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    normalized_text: Mapped[Optional[str]] = mapped_column(Text)
    sections: Mapped[Optional[dict]] = mapped_column(JSON)  # structured sections
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default=AnalysisStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped[Optional["Project"]] = relationship(back_populates="documents")
    analysis: Mapped[Optional["Analysis"]] = relationship(back_populates="document", uselist=False, cascade="all, delete-orphan")


# ── NEW: Analysis Session ──────────────────────────────────────────

class AnalysisSession(Base):
    """Groups a main document + support documents into a single analysis unit."""
    __tablename__ = "analysis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False, default=AnalysisMode.atto_iniziale)
    main_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AnalysisStatus.pending)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="analysis_sessions")
    main_document: Mapped["Document"] = relationship(foreign_keys=[main_document_id])
    support_documents: Mapped[list["SessionDocument"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    analysis: Mapped[Optional["Analysis"]] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")


class SessionDocument(Base):
    """A support document attached to an analysis session with a specific role."""
    __tablename__ = "session_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=SupportDocumentRole.altro)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["AnalysisSession"] = relationship(back_populates="support_documents")
    document: Mapped["Document"] = relationship()


# ── EXISTING: Analysis (extended) ──────────────────────────────────

class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), unique=True, nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("analysis_sessions.id"))
    total_score: Mapped[Optional[float]] = mapped_column(Float)
    subscores: Mapped[Optional[dict]] = mapped_column(JSON)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)
    top_findings_summary: Mapped[Optional[dict]] = mapped_column(JSON)
    documents_considered: Mapped[Optional[dict]] = mapped_column(JSON)  # list of all docs used
    status: Mapped[str] = mapped_column(String(20), default=AnalysisStatus.pending)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    document: Mapped["Document"] = relationship(back_populates="analysis")
    session: Mapped[Optional["AnalysisSession"]] = relationship(back_populates="analysis")
    findings: Mapped[list["Finding"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


# ── EXISTING: Finding (extended with new fields) ───────────────────

class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id"), nullable=False)

    # Classification
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(30), default=FindingType.internal)

    # Location in main document
    section_id: Mapped[Optional[str]] = mapped_column(String(100))
    paragraph_id: Mapped[Optional[str]] = mapped_column(String(100))
    char_start: Mapped[Optional[int]] = mapped_column(Integer)
    char_end: Mapped[Optional[int]] = mapped_column(Integer)
    sezione_documento: Mapped[Optional[str]] = mapped_column(Text)          # section title/description
    estratto_testo: Mapped[Optional[str]] = mapped_column(Text)             # exact excerpt from main doc

    # Core analysis (original fields)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    why_weak: Mapped[str] = mapped_column(Text, nullable=False)
    opponent_angle: Mapped[Optional[str]] = mapped_column(Text)
    strengthen_suggestion: Mapped[Optional[str]] = mapped_column(Text)
    attack_suggestion: Mapped[Optional[str]] = mapped_column(Text)

    # NEW: Deep analysis fields
    cosa_manca: Mapped[Optional[str]] = mapped_column(Text)                 # what's missing
    cosa_contraddetto: Mapped[Optional[str]] = mapped_column(Text)          # what can be contradicted
    base_normativa: Mapped[Optional[str]] = mapped_column(Text)             # normative/legal basis
    come_attacca_controparte: Mapped[Optional[str]] = mapped_column(Text)   # how counterparty attacks
    come_rafforzare: Mapped[Optional[str]] = mapped_column(Text)            # how to strengthen
    adattamento_contesto: Mapped[Optional[str]] = mapped_column(Text)       # context adaptation
    impatto_potenziale: Mapped[Optional[str]] = mapped_column(Text)         # potential impact
    elementi_da_verificare: Mapped[Optional[str]] = mapped_column(Text)     # items for human to verify
    documenti_correlati: Mapped[Optional[dict]] = mapped_column(JSON)       # support docs consulted

    # Metadata
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    module_source: Mapped[Optional[str]] = mapped_column(String(100))
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    analysis: Mapped["Analysis"] = relationship(back_populates="findings")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String(36))
    log_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="audit_logs")
