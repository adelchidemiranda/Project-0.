from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.db.database import get_db
from app.models import Project, Document, User
from app.auth import get_anonymous_user

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    client_name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client_name: Optional[str]
    description: Optional[str]
    document_count: int = 0

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    out = []
    for p in projects:
        doc_result = await db.execute(
            select(Document).where(Document.project_id == p.id)
        )
        docs = doc_result.scalars().all()
        out.append(ProjectResponse(
            id=p.id,
            name=p.name,
            client_name=p.client_name,
            description=p.description,
            document_count=len(docs),
        ))
    return out


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    req: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    project = Project(user_id=current_user.id, **req.model_dump())
    db.add(project)
    await db.flush()
    return ProjectResponse(id=project.id, name=project.name, client_name=project.client_name, description=project.description)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_anonymous_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(id=project.id, name=project.name, client_name=project.client_name, description=project.description)
