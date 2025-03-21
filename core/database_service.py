import logging
from datetime import datetime
from typing import Any, Sequence

from sqlmodel import Session, select

from cache.redis_cache import get_redis_cache
from db.models import (
    Task,
    TaskCreate,
    Workflow,
    WorkflowCreate,
    WorkflowExecution,
    WorkflowStatus,
)

logger = logging.getLogger("uvicorn.error")


class DatabaseService:
    """
    Unified service for managing workflows, tasks, and executions with caching.
    Handles all database interactons.
    """

    def __init__(self, db: Session):
        self.db = db
        self.cache = get_redis_cache()

    #
    # Workflow operations
    #

    def create_workflow(self, workflow_data: WorkflowCreate) -> Workflow:
        """Create a new workflow."""
        data = workflow_data.model_dump()
        workflow = Workflow(**data)
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)

        # Invalidate list cache since a new workflow is added
        self.cache.delete_pattern("workflows:list:*")
        return workflow

    def get_workflow(self, workflow_id: int) -> Workflow | dict[str, Any] | None:
        """Get a workflow by ID."""
        # Try cache first
        cache_key = f"workflow:{workflow_id}"
        if cached_workflow := self.cache.get(cache_key):
            logger.debug(f"Cache hit for workflow {workflow_id}")
            return cached_workflow

        # Not in cache, query database
        workflow = self.db.get(Workflow, workflow_id)

        # Store in cache for future requests
        if workflow:
            self.cache.set(cache_key, workflow)

        return workflow

    def get_workflow_with_tasks(
        self, workflow_id: int
    ) -> Workflow | dict[str, Any] | None:
        """Get a workflow with its tasks."""
        cache_key = f"workflow:{workflow_id}:with_tasks"
        if cached_data := self.cache.get(cache_key):
            logger.debug(f"Cache hit for workflow with tasks {workflow_id}")
            workflow = Workflow.model_validate(cached_data)
            return workflow

        workflow = self.get_workflow(workflow_id)
        if workflow:
            self.cache.set(cache_key, workflow)

        return workflow

    def list_workflows(
        self, skip: int = 0, limit: int = 5
    ) -> Sequence[Workflow] | dict[str, Any]:
        """List workflows with pagination."""
        cache_key = f"workflows:list:{skip}:{limit}"
        if cached_list := self.cache.get(cache_key):
            logger.debug(f"Cache hit for workflow list {skip}:{limit}")
            return cached_list

        workflows = self.db.exec(select(Workflow).offset(skip).limit(limit)).all()
        self.cache.set(cache_key, workflows)
        return workflows

    def update_workflow(
        self, workflow_id: int, workflow_data: dict[str, Any]
    ) -> Workflow | None:
        """Update a workflow with data from dictionary or WorkflowCreate object."""
        workflow = self.db.get(Workflow, workflow_id)
        if not workflow:
            return None

        # Update workflow attributes
        for key, value in workflow_data.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)

        workflow.updated_at = datetime.now()
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        self._invalidate_workflow_caches(workflow_id)
        return workflow

    def delete_workflow(self, workflow_id: int) -> bool:
        """Delete a workflow and all its tasks."""
        workflow = self.db.get(Workflow, workflow_id)
        if not workflow:
            return False

        self.db.delete(workflow)
        self.db.commit()
        self._invalidate_workflow_caches(workflow_id)
        return True

    #
    # Task operations
    #

    def get_task(self, task_id: int) -> Task | None:
        """Get a task by ID."""
        return self.db.get(Task, task_id)

    def add_task(self, workflow_id: int, task_data: TaskCreate) -> Task | None:
        """Add a task to a workflow."""
        workflow = self.db.get(Workflow, workflow_id)
        if not workflow:
            return None

        data = task_data.model_dump()
        task = Task(**data)
        task.workflow_id = workflow_id

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self._invalidate_workflow_caches(workflow_id)
        return task

    def update_task(self, task_id: int, task_data: dict[str, Any]) -> Task | None:
        """Update a task with data from dictionary or TaskCreate object."""
        task = self.db.get(Task, task_id)
        if not task:
            return None

        # Store workflow_id for cache invalidation
        workflow_id = task.workflow_id

        # Update task attributes
        for key, value in task_data.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now()
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self._invalidate_workflow_caches(workflow_id)
        return task

    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        task = self.db.get(Task, task_id)
        if not task:
            return False

        workflow_id = task.workflow_id
        self.db.delete(task)
        self.db.commit()
        self._invalidate_workflow_caches(workflow_id)
        return True

    #
    # Execution operations
    #

    def get_execution(self, execution_id: int) -> WorkflowExecution | None:
        """Get a workflow execution by ID."""
        # Try cache first
        cache_key = f"execution:{execution_id}"
        if cached_execution := self.cache.get(cache_key):
            logger.debug(f"Cache hit for execution {execution_id}")
            return WorkflowExecution.model_validate(cached_execution)

        execution = self.db.get(WorkflowExecution, execution_id)
        if execution:
            self.cache.set(cache_key, execution)

        return execution

    def list_executions(
        self, workflow_id: int | None = None, skip: int = 0, limit: int = 10
    ) -> Sequence[WorkflowExecution]:
        """List workflow executions with optional filtering by workflow ID."""
        # Try cache first
        cache_key = f"executions:list:{workflow_id or 'all'}:{skip}:{limit}"
        if cached_list := self.cache.get(cache_key):
            logger.debug(f"Cache hit for execution list {cache_key}")
            return [WorkflowExecution.model_validate(item) for item in cached_list]

        query = select(WorkflowExecution)
        if workflow_id:
            query = query.where(WorkflowExecution.workflow_id == workflow_id)

        executions = self.db.exec(query.offset(skip).limit(limit)).all()
        self.cache.set(cache_key, executions)
        return executions

    def create_execution(self, workflow_id: int) -> WorkflowExecution:
        """Create a new workflow execution."""
        # Verify workflow exists
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        self._invalidate_execution_caches(workflow_id)
        return execution

    def update_execution_status(
        self,
        execution_id: int,
        status: WorkflowStatus,
    ) -> WorkflowExecution:
        """Update the status of a workflow execution."""
        execution = self.get_execution(execution_id)
        if not execution:
            raise ValueError(f"Workflow execution {execution_id} not found")

        workflow_id = execution.workflow_id
        execution.status = status

        if status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
            execution.completed_at = datetime.now()

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        self._invalidate_execution_caches(workflow_id, execution_id)
        return execution

    #
    # Cache invalidation helpers
    #

    def _invalidate_workflow_caches(self, workflow_id: int) -> None:
        """Invalidate all caches related to a specific workflow."""
        # Delete specific workflow cache
        self.cache.delete(f"workflow:{workflow_id}")

        # Delete list caches that might include this workflow
        self.cache.delete_pattern("workflows:list:*")

        # Delete related execution list caches
        self.cache.delete_pattern(f"executions:list:{workflow_id}:*")
        logger.debug(f"Cache invalidated for {workflow_id=}")

    def _invalidate_execution_caches(
        self, workflow_id: int | None = None, execution_id: int | None = None
    ) -> None:
        """Invalidate execution-related caches."""
        # Delete specific execution cache if execution_id provided
        if execution_id:
            self.cache.delete(f"execution:{execution_id}")
            logger.debug(f"Cache invalidated for execution {execution_id}")

        # Delete list caches that might include this execution
        self.cache.delete_pattern("executions:list:*")
        logger.debug(f"Cache invalidated for execution list {execution_id}")

        # Delete workflow-specific execution lists if workflow_id provided
        if workflow_id:
            self.cache.delete_pattern(f"executions:list:{workflow_id}:*")
            logger.debug(f"Cache invalidated for workflow {workflow_id}")
