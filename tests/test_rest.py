# tests/test_rest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_create_workflow(rest_client: TestClient):
    # Test creating a workflow with tasks
    workflow_data = {
        "name": "Bob's Workflow",
        "description": "Test workflow for automation",
        "tasks": [
            {"name": "Task 1", "description": "First task", "order": 1},
            {"name": "Task 2", "description": "Second task", "order": 2},
        ],
    }

    response = rest_client.post("/workflows/", json=workflow_data)
    assert response.status_code == 200
    assert "id" in response.json()
    assert "tasks" in response.json()


def test_get_workflow(rest_client: TestClient):
    # Create a workflow first
    create_response = rest_client.post(
        "/workflows/",
        json={
            "name": "Bob's Workflow",
            "description": "Test workflow",
            "tasks": [{"name": "Task 1", "order": 1}],
        },
    )
    workflow_id = create_response.json()["id"]

    # Get workflow details
    response = rest_client.get(f"/workflows/{workflow_id}")
    assert response.status_code == 200
    assert response.json()["id"] == workflow_id


def test_list_workflows(rest_client: TestClient):
    # Create test workflows
    for i in range(3):
        rest_client.post(
            "/workflows/",
            json={
                "name": f"Bob's Workflow {i}",
                "tasks": [{"name": f"Task {i}", "order": 1}],
            },
        )

    # List workflows with pagination
    response = rest_client.get("/workflows/?skip=0&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_workflow(rest_client: TestClient):
    # Create workflow
    create_response = rest_client.post(
        "/workflows/",
        json={
            "name": "Bob's Workflow",
            "description": "Test workflow",
            "tasks": [{"name": "Task 1", "order": 1}],
        },
    )
    workflow_id = create_response.json()["id"]

    # Update workflow
    updated_data = {"name": "Updated Workflow", "description": "Updated test workflow"}
    response = rest_client.put(f"/workflows/{workflow_id}", json=updated_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workflow"


def test_delete_workflow(rest_client: TestClient):
    # Create workflow
    create_response = rest_client.post(
        "/workflows/",
        json={"name": "Bob's Workflow", "tasks": [{"name": "Task 1", "order": 1}]},
    )
    workflow_id = create_response.json()["id"]

    # Delete workflow
    response = rest_client.delete(f"/workflows/{workflow_id}")
    assert response.status_code == 200
    assert response.json() == {"success": True}
