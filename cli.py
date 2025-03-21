import json
import os
import sys
from argparse import ArgumentParser, Namespace
from typing import Any

import grpc
import httpx

from api.grpc.proto.execution_pb2 import (
    ExecuteWorkflowRequest,
    GetWorkflowStatusRequest,
)
from api.grpc.proto.execution_pb2_grpc import WorkflowExecutionStub


class WorkflowCLI:
    """
    Command-line interface for interacting with workflow automation APIs.
    Supports both REST and gRPC APIs.
    """

    def __init__(self):
        self.rest_api_url = os.environ.get("REST_API_URL", "http://localhost:8000")
        self.grpc_api_url = os.environ.get("GRPC_API_URL", "localhost:50051")

    def run(self):
        """Parse arguments and execute the appropriate command."""
        parser = ArgumentParser(description="Workflow Automation CLI")
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")

        # Commands for workflow management (REST API)
        create_parser = subparsers.add_parser("create", help="Create a new workflow")
        create_parser.add_argument("name", help="Workflow name")
        create_parser.add_argument("--description", help="Workflow description")

        list_parser = subparsers.add_parser("list", help="List workflows")
        list_parser.add_argument("--skip", type=int, default=0, help="Skip N workflows")
        list_parser.add_argument("--limit", type=int, default=5, help="Limit results")

        get_parser = subparsers.add_parser("get", help="Get workflow by ID")
        get_parser.add_argument("workflow_id", type=int, help="Workflow ID")

        # Commands for task management (REST API)
        add_task_parser = subparsers.add_parser("add-task", help="Add task to workflow")
        add_task_parser.add_argument("workflow_id", type=int, help="Workflow ID")
        add_task_parser.add_argument("name", help="Task name")
        add_task_parser.add_argument("--description", help="Task description")
        add_task_parser.add_argument(
            "--order", type=int, required=True, help="Task order"
        )
        add_task_parser.add_argument(
            "--type",
            choices=["sync", "async"],
            default="sync",
            help="Task execution type (sync or async)",
        )
        add_task_parser.add_argument(
            "--params",
            type=json.loads,
            default={},
            help="Task parameters as JSON string",
        )

        # Commands for workflow execution (gRPC API)
        execute_parser = subparsers.add_parser("execute", help="Execute a workflow")
        execute_parser.add_argument("workflow_id", type=int, help="Workflow ID")

        status_parser = subparsers.add_parser(
            "status", help="Get workflow execution status"
        )
        status_parser.add_argument("execution_id", type=int, help="Execution ID")

        # Parse arguments
        args = parser.parse_args()
        if not args.command:
            parser.print_help()
            return

        try:
            # Dynamic method dispatch to call appropriate method
            method = getattr(self, f"cmd_{args.command.replace('-', '_')}")
            method(args)
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)

    def cmd_create(self, args: Namespace):
        """Create a new workflow."""
        data = {"name": args.name, "description": args.description}
        response = self._rest_api_call("POST", "/workflows/", json=data)
        self._print_response(response)

    def cmd_list(self, args: Namespace):
        """List workflows."""
        params = {"skip": args.skip, "limit": args.limit}
        response = self._rest_api_call("GET", "/workflows/", params=params)
        self._print_response(response)

    def cmd_get(self, args: Namespace):
        """Get a workflow by ID."""
        response = self._rest_api_call("GET", f"/workflows/{args.workflow_id}")
        self._print_response(response)

    def cmd_add_task(self, args: Namespace):
        """Add a task to a workflow."""
        data = {
            "name": args.name,
            "description": args.description,
            "order": args.order,
            "execution_type": args.type,
            "parameters": args.params,
        }
        response = self._rest_api_call(
            "POST", f"/workflows/{args.workflow_id}/tasks", json=data
        )
        self._print_response(response)

    def cmd_execute(self, args: Namespace):
        """Execute a workflow using gRPC."""
        with grpc.insecure_channel(self.grpc_api_url) as channel:
            stub = WorkflowExecutionStub(channel)
            request = ExecuteWorkflowRequest(workflow_id=args.workflow_id)
            response = stub.ExecuteWorkflow(request)

            print(f"Execution started with ID: {response.execution_id}")
            print(f"Status: {response.status}")

    def cmd_status(self, args: Namespace):
        """Get workflow execution status using gRPC."""
        with grpc.insecure_channel(self.grpc_api_url) as channel:
            stub = WorkflowExecutionStub(channel)
            request = GetWorkflowStatusRequest(execution_id=args.execution_id)
            response = stub.GetWorkflowStatus(request)

            print(f"Execution ID: {response.execution_id}")
            print(f"Workflow ID: {response.workflow_id}")
            print(f"Status: {response.status}")
            print(f"Started at: {response.started_at}")
            if response.completed_at:
                print(f"Completed at: {response.completed_at}")

    def _rest_api_call(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a REST API call."""
        url = f"{self.rest_api_url}{endpoint}"

        with httpx.Client(follow_redirects=True) as client:
            response = client.request(method=method, url=url, params=params, json=json)

            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                error_msg = f"API Error ({response.status_code}): "
                try:
                    error_data = response.json()
                    error_msg += error_data.get("detail", str(error_data))
                except:
                    error_msg += response.text or "Unknown error"

                raise Exception(error_msg)

    def _print_response(self, data: dict[str, Any]):
        """Print API response data in a formatted way."""
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    cli = WorkflowCLI()
    cli.run()
