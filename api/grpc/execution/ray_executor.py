import asyncio
import logging

import ray

from db.models import Task, TaskType, Workflow

logger = logging.getLogger(__name__)


@ray.remote
def execute_task(task: Task) -> bool:
    """Ray remote function to execute a task."""
    # Simulate task execution
    import time

    time.sleep(task.parameters.get("duration", 1))
    logger.info(f"Task {task.id} completed")
    return True


class RayExecutor:
    """Executes workflows using Ray for parallel execution."""

    def __init__(self):
        # Ensure Ray is initialized
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)

    async def execute_workflow(self, workflow: Workflow, execution_id: int) -> bool:
        """
        Execute a workflow using Ray.
        - Tasks are processed in order
        - Sync tasks: Execute and wait for completion before continuing
        - Async tasks: Execute and continue immediately without waiting
        """
        try:
            logger.info(f"Executing workflow {workflow.id} with Ray ({execution_id=})")

            # Process tasks in order
            for task in workflow.tasks:
                if task.execution_type == TaskType.SYNC:
                    # For sync tasks, wait for completion before continuing
                    logger.info(f"Executing sync task: {task.id} - {task.name}")
                    result = await asyncio.to_thread(
                        ray.get,
                        execute_task.remote(task),
                    )
                    if not result:
                        logger.error(f"Sync task {task.id} failed")
                        return False
                else:
                    # For async tasks, launch and continue immediately, no waiting
                    logger.info(
                        f"Executing async task: {task.id} - {task.name} (non-blocking)"
                    )
                    execute_task.remote(task)

            logger.info(
                f"Workflow {workflow.id} completed successfully ({execution_id=})"
            )
            return True

        except Exception as e:
            logger.error(f"Error executing workflow with Ray: {str(e)}")
            return False
