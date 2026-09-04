import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.project import Project
from app.models.dataset import Dataset
from app.schemas.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all projects with dataset counts."""
    count_result = await db.execute(
        select(func.count()).select_from(Project).where(Project.status == "active")
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Project)
        .where(Project.status == "active")
        .options(selectinload(Project.datasets))
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    projects = result.scalars().all()

    project_responses = []
    for p in projects:
        pr = ProjectResponse.model_validate(p)
        pr.dataset_count = len([d for d in p.datasets if d.status == "active"])
        project_responses.append(pr)

    return ProjectListResponse(total=total, projects=project_responses)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        name=payload.name,
        description=payload.description,
        location_name=payload.location_name,
        crs=payload.crs or "EPSG:4326",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    pr = ProjectResponse.model_validate(project)
    pr.dataset_count = 0
    return pr


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single project by ID."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.status == "active")
        .options(selectinload(Project.datasets))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    pr = ProjectResponse.model_validate(project)
    pr.dataset_count = len([d for d in project.datasets if d.status == "active"])
    return pr


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update project fields."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.status == "active")
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    pr = ProjectResponse.model_validate(project)
    pr.dataset_count = 0
    return pr


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.status == "active")
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    project.status = "deleted"
    await db.commit()
