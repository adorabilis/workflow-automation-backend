# tests/test_redis.py
import pytest
from fastapi.testclient import TestClient
from redis import Redis


def test_cache_invalidation(rest_client: TestClient, redis_client: Redis):
    # Create workflow
    create_response = rest_client.post(
        "/workflows/",
        json={"name": "Test Workflow", "tasks": [{"name": "Task 1", "order": 1}]},
    )
    workflow_id = create_response.json()["id"]

    # Check if workflow is cached
    cache_key = f"workflow:{workflow_id}"
    # Workflow is not cached on creation
    assert redis_client.exists(cache_key) == 0

    # Retrieve workflow
    rest_client.get(f"/workflows/{workflow_id}")
    # Workflow is only cached on retrieval
    assert redis_client.exists(cache_key) == 1

    # Update workflow
    rest_client.put(f"/workflows/{workflow_id}", json={"name": "Updated Workflow"})
    # Verify cache was invalidated
    assert redis_client.exists(cache_key) == 0
