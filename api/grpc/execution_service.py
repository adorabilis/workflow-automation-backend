import asyncio
import logging

import grpc
from api.grpc.proto.execution_pb2 import (
    ExecuteWorkflowResponse,
    WorkflowStatusResponse,
)
from api.grpc.proto.execution_pb2_grpc import WorkflowExecutionServicer
from core.database_service import DatabaseService
from db.models import Task, TaskType, WorkflowStatus
from db.session import get_db_session

from .execution.ray_executor import RayExecutor
from .execution.redis_queue import RedisQueueExecutor

logger = logging.getLogger(__name__)


class WorkflowExecutionService(WorkflowExecutionServicer):
    """gRPC service implementation for workflow execution."""

    def __init__(self, use_rq: bool = False, use_ray: bool = False):
        self.use_rq = use_rq
        self.use_ray = use_ray

        # Initialize executors based on configuration
        if use_ray:
            self.ray_executor = RayExecutor()

        if use_rq:
            self.rq_executor = RedisQueueExecutor()

    async def ExecuteWorkflow(self, request, context):
        """
        Execute a workflow with the given ID.
        Supports both synchronous execution and background execution via RQ.
        Can use Ray for parallel task execution within the workflow.
        """
        workflow_id = request.workflow_id
        logger.info(f"Received execution request for workflow: {workflow_id}")

        try:
            # Get a DB session
            session = next(get_db_session())
            db = DatabaseService(session)

            # Verify workflow exists
            workflow = db.get_workflow_with_tasks(workflow_id)
            if not workflow:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND, f"Workflow {workflow_id} not found"
                )

            # Create execution record
            execution = db.create_execution(workflow_id)
            execution_id = execution.id

            # Update status to IN_PROGRESS
            db.update_execution_status(execution_id, WorkflowStatus.IN_PROGRESS)

            # Execute workflow based on chosen method
            if self.use_rq:
                # Use Redis Queue for background processing
                logger.info(f"Enqueuing workflow {workflow_id} in RQ")
                self.rq_executor.execute_workflow(workflow_id, execution_id)

            elif self.use_ray:
                # Use Ray for parallel execution
                logger.info(
                    f"Executing workflow {workflow_id} with Ray ({execution_id=})"
                )
                asyncio.create_task(self._execute_with_ray(workflow_id, execution_id))
            else:
                # Execute tasks sequentially with asyncio for async tasks
                logger.info(f"Executing workflow {workflow_id} ({execution_id=})")
                asyncio.create_task(self._execute_sync(workflow_id, execution_id))

            # Return the execution ID to the client
            return ExecuteWorkflowResponse(
                execution_id=execution_id, status=WorkflowStatus.IN_PROGRESS.value
            )

        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            await context.abort(
                grpc.StatusCode.INTERNAL, f"Error executing workflow: {str(e)}"
            )

    async def GetWorkflowStatus(self, request, context):
        """Get the status of a workflow execution."""
        execution_id = request.execution_id
        logger.info(f"Checking status for execution: {execution_id}")

        try:
            # Get a DB session
            session = next(get_db_session())
            db = DatabaseService(session)

            # Get execution details
            execution = db.get_execution(execution_id)
            if not execution:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND, f"Execution {execution_id} not found"
                )
            else:
                # Format the dates as ISO strings
                started_at = execution.started_at.isoformat()
                completed_at = (
                    execution.completed_at.isoformat()
                    if execution.completed_at
                    else None
                )
                workflow_id = execution.workflow_id

                # Return the status
                return WorkflowStatusResponse(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    status=execution.status.value,
                    started_at=started_at,
                    completed_at=completed_at,
                )

        except Exception as e:
            logger.error(f"Error getting workflow status: {str(e)}")
            await context.abort(
                grpc.StatusCode.INTERNAL, f"Error getting workflow status: {str(e)}"
            )

    async def _execute_sync(self, workflow_id: int, execution_id: int):
        """Execute workflow tasks one by one in order."""
        session = next(get_db_session())
        db_service = DatabaseService(session)

        try:
            # Get workflow with tasks
            workflow = db_service.get_workflow_with_tasks(workflow_id)
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return

            # Execute each task in order
            for task in workflow.tasks:
                if task.execution_type == TaskType.SYNC:
                    # Execute sync task and wait
                    logger.info(f"Executing sync task: {task.id} - {task.name}")
                    # Simulating execution
                    await asyncio.sleep(task.parameters.get("duration", 1))
                else:
                    # For async tasks, launch and continue immediately
                    logger.info(
                        f"Launching async task in background: {task.id} - {task.name}"
                    )
                    asyncio.create_task(self._execute_async_task(task))

            # Update execution status to COMPLETED
            db_service.update_execution_status(execution_id, WorkflowStatus.COMPLETED)
            logger.info(
                f"Workflow {workflow_id} completed successfully ({execution_id=})"
            )

        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            # Update execution status to FAILED
            db_service.update_execution_status(execution_id, WorkflowStatus.FAILED)

    async def _execute_async_task(self, task: Task):
        """Execute an async task in the background."""
        try:
            logger.info(f"Executing async task: {task.id} - {task.name} (non-blocking)")
            # Simulating execution
            await asyncio.sleep(task.parameters.get("duration", 1))
            logger.info(f"Async task {task.id} completed")
        except Exception as e:
            logger.error(f"Async task {task.id} failed: {str(e)}")

    async def _execute_with_ray(self, workflow_id: int, execution_id: int):
        """Execute workflow using Ray for parallel execution."""
        session = next(get_db_session())
        db = DatabaseService(session)

        try:
            # Get workflow with tasks
            workflow = db.get_workflow_with_tasks(workflow_id)
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return

            # Execute workflow with Ray
            success = await self.ray_executor.execute_workflow(workflow, execution_id)

            # Update execution status based on result
            status = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
            db.update_execution_status(execution_id, status)

        except:
            # Update execution status to FAILED
            db.update_execution_status(execution_id, WorkflowStatus.FAILED)
