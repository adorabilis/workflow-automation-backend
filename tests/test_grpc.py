# tests/test_grpc.py
import pytest
from grpc import insecure_channel

from api.grpc.proto import execution_pb2, execution_pb2_grpc


def test_execute_workflow(grpc_client, rest_client):
    # Create a test workflow via REST first
    create_response = rest_client.post(
        "/workflows/",
        json={"name": "Test Workflow"},
    )
    workflow_id = create_response.json()["id"]

    # Create a test task in the workflow
    _ = rest_client.post(
        f"/workflows/{workflow_id}/tasks/",
        json={"name": "Task 1", "order": 1},
    )

    # Execute workflow via gRPC
    request = execution_pb2.ExecuteWorkflowRequest(workflow_id=workflow_id)
    response = grpc_client.ExecuteWorkflow(request)
    assert response.execution_id > 0
    assert response.status == "in_progress"


def test_workflow_status(grpc_client):
    # Start execution
    request = execution_pb2.GetWorkflowStatusRequest(
        execution_id=1  # Replace with actual execution ID
    )
    response = grpc_client.GetWorkflowStatus(request)
    assert response.status in ["pending", "in_progress", "completed", "failed"]
