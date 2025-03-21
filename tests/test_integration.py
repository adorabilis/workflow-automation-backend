# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy import select
from sqlmodel import Session

from api.grpc.proto import execution_pb2, execution_pb2_grpc


def test_workflow_integration(
    rest_client: TestClient, grpc_client, redis_client: Redis
):
    """
    Integration test covering:
    1. Create a workflow via REST API
    2. Trigger execution via gRPC
    3. Check workflow status via gRPC
    4. Verify Redis cache invalidation
    """

    # Step 1: Create a workflow via REST API
    workflow_data = {
        "name": "Test Integration Workflow",
        "description": "Test workflow for integration testing",
        "tasks": [
            {"name": "Task 1", "description": "First task", "order": 1},
            {"name": "Task 2", "description": "Second task", "order": 2},
        ],
    }

    # Create workflow
    create_response = rest_client.post("/workflows/", json=workflow_data)
    assert create_response.status_code == 200
    workflow = create_response.json()
    workflow_id = workflow["id"]

    # Trigger workflow execution via gRPC
    request = execution_pb2.ExecuteWorkflowRequest(workflow_id=workflow_id)
    response = grpc_client.ExecuteWorkflow(request)
    assert response.execution_id > 0
    assert response.status == "in_progress"
    execution_id = response.execution_id

    # Check workflow status via gRPC
    status_request = execution_pb2.GetWorkflowStatusRequest(execution_id=execution_id)
    status_response = grpc_client.GetWorkflowStatus(status_request)
    assert status_response.status in ["pending", "in_progress", "completed", "failed"]

    # Verify workflow cache in Redis
    cache_key = f"workflow:{workflow_id}"
    assert redis_client.exists(cache_key) == 1  # Cache exists

    # Update workflow via REST API
    updated_data = {"name": "Updated Integration Workflow"}
    update_response = rest_client.put(f"/workflows/{workflow_id}", json=updated_data)
    assert update_response.status_code == 200

    # Verify cache was invalidated
    assert redis_client.exists(cache_key) == 0  # Cache should be gone

    # Verify final workflow status
    final_status_response = grpc_client.GetWorkflowStatus(status_request)
    assert final_status_response.status == "completed"

    # Cleanup
    delete_response = rest_client.delete(f"/workflows/{workflow_id}")
    assert delete_response.status_code == 200
    assert redis_client.exists(cache_key) == 0  # Cache should be gone
