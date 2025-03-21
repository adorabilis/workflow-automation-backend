import argparse
import asyncio
import logging
import signal

import grpc

from api.grpc.execution_service import WorkflowExecutionService
from api.grpc.proto.execution_pb2_grpc import add_WorkflowExecutionServicer_to_server
from db.session import create_db_and_tables

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Workflow Execution Service")
    parser.add_argument("--use-rq", action="store_true", help="Use Redis Queue")
    parser.add_argument(
        "--use-ray", action="store_true", help="Use Ray for parallel execution"
    )
    return parser.parse_args()


async def serve():
    """Start the gRPC server."""
    logging.basicConfig(level=logging.INFO)

    # Create database tables
    create_db_and_tables()

    # Parse arguments
    args = parse_args()

    # Create gRPC server
    server = grpc.aio.server()
    service = WorkflowExecutionService(use_rq=args.use_rq, use_ray=args.use_ray)
    add_WorkflowExecutionServicer_to_server(service, server)

    # Set up graceful shutdown
    # https://grpc.io/docs/guides/server-graceful-stop/
    async def graceful_shutdown(sig: signal.Signals):
        logger.info(f"Received signal {sig.name}...")
        logger.info("Shutting down server gracefully...")
        # Give clients 5 seconds to complete ongoing RPCs
        await server.stop(5)
        logger.info("Server stopped.")

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(graceful_shutdown(s))
        )

    # Start server
    server_address = "[::]:50051"
    server.add_insecure_port(server_address)
    logger.info(f"Starting gRPC server on {server_address}")

    await server.start()
    logger.info("Server started successfully!")
    if args.use_rq:
        logger.info(f"Redis Queue enabled")
    if args.use_ray:
        logger.info("Ray parallel execution enabled")

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
