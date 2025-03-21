import logging
import sys

from rq import Worker

from api.grpc.execution.redis_queue import redis_conn
from db.session import create_db_and_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("rq.worker")

if __name__ == "__main__":
    # Initialize database tables
    create_db_and_tables()

    # Set up Redis connection
    worker = Worker(["default"], connection=redis_conn)
    logger.info(f"RQ Worker started, listening for jobs...")
    worker.work()
