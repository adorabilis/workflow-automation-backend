from typing import Any, Sequence

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.database_service import DatabaseService
from db.models import (
    Task,
    TaskCreate,
    TaskResponse,
    Workflow,
    WorkflowCreate,
    WorkflowResponse,
)
from db.session import get_db_session

# Create router for workflow endpoints
router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse)
def create_workflow(
    workflow: WorkflowCreate, session: Session = Depends(get_db_session)
) -> Workflow:
    """Create a new workflow."""
    db = DatabaseService(session)
    return db.create_workflow(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: int, session: Session = Depends(get_db_session)
) -> Workflow | dict[str, Any]:
    """Retrieve a specific workflow by ID."""
    db = DatabaseService(session)
    workflow = db.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.get("/", response_model=list[WorkflowResponse])
def list_workflows(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)
) -> Sequence[Workflow] | dict[str, Any]:
    """List all workflows with pagination."""
    db = DatabaseService(session)
    workflows = db.list_workflows(skip=skip, limit=limit)
    return workflows


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowCreate,
    session: Session = Depends(get_db_session),
) -> Workflow:
    """Update an existing workflow."""
    db = DatabaseService(session)
    workflow = db.update_workflow(workflow_id, workflow_update.model_dump())
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: int, session: Session = Depends(get_db_session)
) -> dict[str, bool]:
    """Delete an existing workflow."""
    db = DatabaseService(session)
    success = db.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True}


@router.post("/{workflow_id}/tasks/", response_model=TaskResponse)
def add_task(
    workflow_id: int, task: TaskCreate, session: Session = Depends(get_db_session)
) -> Task:
    """Add a task to an existing workflow."""
    db = DatabaseService(session)
    task_session = db.add_task(workflow_id, task)
    if not task_session:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return task_session


@router.put("/{workflow_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskCreate,
    session: Session = Depends(get_db_session),
) -> Task:
    """Update an existing task."""
    db = DatabaseService(session)
    task = db.update_task(task_id, task_update.model_dump())
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in this workflow")
    return task


@router.delete("/{workflow_id}/tasks/{task_id}")
def delete_task(
    workflow_id: int, task_id: int, session: Session = Depends(get_db_session)
) -> dict[str, bool]:
    """Delete an existing task from a workflow."""
    db = DatabaseService(session)
    workflow = db.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    success = db.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found in this workflow")
    return {"success": True}
