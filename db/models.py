from datetime import datetime
from enum import Enum
from typing import Any

from sqlmodel import JSON, Column, Field, Relationship, SQLModel


class TaskType(str, Enum):
    """
    Defines the type of task execution.

    SYNC: Task runs sequentially as part of the workflow execution
    ASYNC: Task runs in parallel and doesn't block workflow execution
    """

    SYNC = "sync"
    ASYNC = "async"


class WorkflowStatus(str, Enum):
    """
    Represents the current status of a workflow execution.

    PENDING: Workflow is waiting to be executed
    IN_PROGRESS: Workflow is currently running
    COMPLETED: Workflow has finished successfully
    FAILED: Workflow execution failed
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskBase(SQLModel):
    """
    Base model for task containing common fields.
    """

    name: str
    description: str | None = None
    order: int
    execution_type: TaskType | None = TaskType.SYNC
    parameters: dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class Task(TaskBase, table=True):
    """
    Database model for tasks.
    Represents a single task within a workflow.
    """

    id: int = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    workflow_id: int = Field(foreign_key="workflow.id")
    workflow: "Workflow" = Relationship(back_populates="tasks")


class TaskCreate(TaskBase):
    """
    Schema for task creation API requests.
    """

    pass


class TaskResponse(TaskBase):
    """
    Schema for task retrieval API responses.
    """

    id: int
    workflow_id: int


class WorkflowBase(SQLModel):
    """
    Base model for workflow containing common fields.
    """

    name: str
    description: str | None = None


class Workflow(WorkflowBase, table=True):
    """
    Database model for workflows.
    Represents a workflow that contains multiple tasks.
    """

    id: int = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tasks: list[Task] = Relationship(
        back_populates="workflow",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "Task.order", "lazy": "selectin"},
    )


class WorkflowCreate(WorkflowBase):
    """
    Schema for workflow creation API requests.
    """

    pass


class WorkflowResponse(WorkflowBase):
    """
    Schema for workflow retrieval API requests.
    """

    id: int
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskResponse] = []


class WorkflowExecution(SQLModel, table=True):
    """
    Database model for workflow executions.
    Tracks the execution of a workflow and its current status.
    """

    id: int = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id", ondelete="CASCADE")
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
