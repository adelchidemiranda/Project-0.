"""
Background Worker (Local Execution)
Handles async document analysis jobs using FastAPI BackgroundTasks.
Supports both single-document and session-based multi-document analysis.
"""
from app.config import get_settings

settings = get_settings()


def run_analysis_task(document_id: str):
    """
    Legacy task: run the full analysis pipeline for a single document.
    Kept for backward compatibility.
    """
    import asyncio
    from datetime import datetime
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine, select
    from app.models import Document, Analysis, Finding, AnalysisStatus
    from app.services.parser import parse_document
    from app.analysis.pipeline import run_pipeline

    sync_url = settings.database_url.replace("+aiosqlite", "")
    engine = create_engine(sync_url, connect_args={"check_same_thread": False})

    with Session(engine) as session:
        doc = session.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if not doc:
            print(f"Error: Document {document_id} not found")
            return

        doc.status = AnalysisStatus.processing
        session.commit()

        analysis = session.execute(
            select(Analysis).where(Analysis.document_id == document_id)
        ).scalar_one_or_none()

        if not analysis:
            analysis = Analysis(document_id=document_id, status=AnalysisStatus.processing)
            session.add(analysis)
            session.flush()
        else:
            analysis.status = AnalysisStatus.processing
        session.commit()

        try:
            parsed = parse_document(doc.file_path)
            doc.normalized_text = parsed.normalized_text
            doc.raw_text = parsed.raw_text
            doc.sections = parsed.sections_dict
            session.commit()

            findings, total_score, subscores, breakdown = run_pipeline(
                document_id=document_id,
                parsed=parsed,
                doc_type=doc.doc_type,
                doc_role=doc.doc_role,
                language=doc.language,
            )

            _save_findings(session, analysis, findings, total_score, subscores, breakdown)
            doc.status = AnalysisStatus.done
            session.commit()
            print(f"Analysis complete for {document_id}. Score: {total_score}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            analysis.status = AnalysisStatus.error
            analysis.error_message = str(e)
            doc.status = AnalysisStatus.error
            session.commit()


def run_session_analysis_task(session_id: str):
    """
    NEW: Run analysis for an entire AnalysisSession (main doc + support docs).
    This is the primary analysis path for the multi-document feature.
    """
    import traceback
    from datetime import datetime
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine, select
    from app.models import (
        Document, Analysis, Finding, AnalysisSession,
        SessionDocument, AnalysisStatus
    )
    from app.services.parser import parse_document
    from app.analysis.pipeline import run_pipeline
    from app.analysis.base import SupportDocData

    sync_url = settings.database_url.replace("+aiosqlite", "")
    engine = create_engine(sync_url, connect_args={"check_same_thread": False})

    with Session(engine) as session:
        # Load analysis session
        analysis_session = session.execute(
            select(AnalysisSession).where(AnalysisSession.id == session_id)
        ).scalar_one_or_none()

        if not analysis_session:
            print(f"Error: AnalysisSession {session_id} not found")
            return

        analysis_session.status = AnalysisStatus.processing
        session.commit()

        try:
            # STEP 1: Load and parse main document
            main_doc = session.execute(
                select(Document).where(Document.id == analysis_session.main_document_id)
            ).scalar_one_or_none()

            if not main_doc:
                raise ValueError(f"Main document {analysis_session.main_document_id} not found")

            main_doc.status = AnalysisStatus.processing
            session.commit()

            parsed_main = parse_document(main_doc.file_path)
            main_doc.normalized_text = parsed_main.normalized_text
            main_doc.raw_text = parsed_main.raw_text
            main_doc.sections = parsed_main.sections_dict
            session.commit()

            # STEP 2: Load and parse all support documents
            session_docs = session.execute(
                select(SessionDocument).where(SessionDocument.session_id == session_id)
            ).scalars().all()

            support_docs_data: list[SupportDocData] = []
            docs_considered = [{
                "document_id": main_doc.id,
                "filename": main_doc.filename,
                "role": "documento_principale",
                "doc_type": main_doc.doc_type,
            }]

            for sd in session_docs:
                support_doc = session.execute(
                    select(Document).where(Document.id == sd.document_id)
                ).scalar_one_or_none()

                if not support_doc:
                    continue

                # Parse the support document
                try:
                    parsed_support = parse_document(support_doc.file_path)
                    support_doc.normalized_text = parsed_support.normalized_text
                    support_doc.raw_text = parsed_support.raw_text
                    support_doc.sections = parsed_support.sections_dict
                    session.commit()

                    support_docs_data.append(SupportDocData(
                        document_id=support_doc.id,
                        filename=support_doc.filename,
                        role=sd.role,
                        normalized_text=parsed_support.normalized_text,
                        sections=parsed_support.sections,
                    ))

                    docs_considered.append({
                        "document_id": support_doc.id,
                        "filename": support_doc.filename,
                        "role": sd.role,
                        "doc_type": support_doc.doc_type,
                    })
                except Exception as e:
                    print(f"[WARN] Failed to parse support doc {support_doc.filename}: {e}")

            print(f"Session {session_id}: Main doc '{main_doc.filename}' + {len(support_docs_data)} support docs")

            # STEP 3: Create or get Analysis record
            analysis = session.execute(
                select(Analysis).where(Analysis.document_id == main_doc.id)
            ).scalar_one_or_none()

            if not analysis:
                analysis = Analysis(
                    document_id=main_doc.id,
                    session_id=session_id,
                    status=AnalysisStatus.processing,
                )
                session.add(analysis)
                session.flush()
            else:
                analysis.status = AnalysisStatus.processing
                analysis.session_id = session_id
                # Clear old findings
                for old_f in session.execute(
                    select(Finding).where(Finding.analysis_id == analysis.id)
                ).scalars().all():
                    session.delete(old_f)
            session.commit()

            # STEP 4: Run the analysis pipeline with full document context
            findings, total_score, subscores, breakdown = run_pipeline(
                document_id=main_doc.id,
                parsed=parsed_main,
                doc_type=main_doc.doc_type,
                doc_role=main_doc.doc_role,
                language=main_doc.language,
                analysis_mode=analysis_session.mode,
                support_documents=support_docs_data,
            )

            # STEP 5: Save results
            analysis.documents_considered = docs_considered
            _save_findings(session, analysis, findings, total_score, subscores, breakdown)

            main_doc.status = AnalysisStatus.done
            analysis_session.status = AnalysisStatus.done
            analysis_session.completed_at = datetime.utcnow()
            session.commit()

            print(f"Session analysis complete for {session_id}. Score: {total_score}")

        except Exception as e:
            traceback.print_exc()
            analysis_session.status = AnalysisStatus.error
            analysis_session.error_message = str(e)
            session.commit()


def _save_findings(session, analysis, findings, total_score, subscores, breakdown):
    """Save findings and scores to the analysis record."""
    from datetime import datetime
    from app.models import Finding, AnalysisStatus

    for f in findings:
        finding = Finding(
            analysis_id=analysis.id,
            severity=f.severity,
            category=f.category,
            finding_type=f.finding_type,
            section_id=f.section_id,
            paragraph_id=f.paragraph_id,
            char_start=f.char_start,
            char_end=f.char_end,
            sezione_documento=f.sezione_documento or None,
            estratto_testo=f.estratto_testo or None,
            claim=f.claim,
            why_weak=f.why_weak,
            opponent_angle=f.opponent_angle or None,
            strengthen_suggestion=f.strengthen_suggestion or None,
            attack_suggestion=f.attack_suggestion or None,
            cosa_manca=f.cosa_manca or None,
            cosa_contraddetto=f.cosa_contraddetto or None,
            base_normativa=f.base_normativa or None,
            come_attacca_controparte=f.come_attacca_controparte or None,
            come_rafforzare=f.come_rafforzare or None,
            adattamento_contesto=f.adattamento_contesto or None,
            impatto_potenziale=f.impatto_potenziale or None,
            elementi_da_verificare=f.elementi_da_verificare or None,
            documenti_correlati=f.documenti_correlati if f.documenti_correlati else None,
            confidence=f.confidence,
            module_source=f.module_source,
        )
        session.add(finding)

    analysis.total_score = total_score
    analysis.subscores = subscores
    analysis.score_breakdown = breakdown
    analysis.status = AnalysisStatus.done
    analysis.completed_at = datetime.utcnow()
    session.commit()
