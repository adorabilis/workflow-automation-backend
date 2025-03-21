import logging
from concurrent.futures import ThreadPoolExecutor

import redis
from rq import Queue

from core.config import REDIS_DB, REDIS_HOST, REDIS_PORT
from core.database_service import DatabaseService
from db.models import Task, TaskType, WorkflowStatus
from db.session import get_db_session

logger = logging.getLogger(__name__)

# Create connection to Redis
redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Create RQ queue
task_queue = Queue(connection=redis_conn)


def execute_task_background(task: Task):
    """Execute a task in the background."""
    logger.info(f"Background execution of async task: {task.id} - {task.name}")
    # Simulate task execution
    import time

    time.sleep(task.parameters.get("duration", 1))
    logger.info(f"Task {task.id} completed")


def process_workflow(workflow_id: int, execution_id: int) -> bool:
    """
    Process a workflow in the background using RQ.
    This function will be executed by a worker.
    """
    try:
        logger.info(f"Executing workflow {workflow_id} ({execution_id=})")

        session = next(get_db_session())
        db = DatabaseService(session)

        # Get workflow with tasks
        workflow = db.get_workflow_with_tasks(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            db.update_execution_status(execution_id, WorkflowStatus.FAILED)
            return False

        # Create thread pool for async tasks
        executor = ThreadPoolExecutor(max_workers=10)

        # Process tasks in order
        for task in workflow.tasks:
            if task.execution_type == TaskType.SYNC:
                # Execute sync task and wait for completion
                logger.info(f"Executing sync task: {task.id} - {task.name}")
                # Simulate task execution
                import time

                time.sleep(task.parameters.get("duration", 1))
            else:
                # Execute async task without waiting
                logger.info(
                    f"Launching async task: {task.id} - {task.name} (non-blocking)"
                )
                executor.submit(execute_task_background, task)

        # Update execution status to completed
        db.update_execution_status(execution_id, WorkflowStatus.COMPLETED)
        logger.info(f"Workflow {workflow_id} completed successfully ({execution_id=})")

        # Shutdown executor (don't wait for tasks to complete)
        executor.shutdown(wait=False)
        return True

    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        # Update execution status to FAILED
        try:
            session = next(get_db_session())
            db = DatabaseService(session)
            db.update_execution_status(execution_id, WorkflowStatus.FAILED)
        except Exception as inner_e:
            logger.error(f"Error updating execution status: {str(inner_e)}")

        return False


class RedisQueueExecutor:
    """Executes workflows asynchronously using Redis Queue."""

    def __init__(self):
        self.queue = task_queue

    def execute_workflow(self, workflow_id: int, execution_id: int) -> None:
        """Enqueue a workflow for background processing."""
        logger.info(f"Enqueuing workflow {workflow_id} for background processing")
        self.queue.enqueue(
            process_workflow,
            workflow_id,
            execution_id,
            job_timeout=3600,  # 1 hour timeout
        )
