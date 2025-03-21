# tests/conftest.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis
from sqlmodel import Session, SQLModel, create_engine

from core.database_service import DatabaseService
from db.models import Task, Workflow


@pytest.fixture(scope="session")
def engine():
    return create_engine("sqlite:///test.db")


@pytest.fixture(scope="session")
def session():
    with Session(engine) as session:
        yield session


@pytest.fixture
def redis_client():
    return Redis(host="localhost", port=6379, db=0)


@pytest.fixture
def rest_client():
    from main import app

    client = TestClient(app)
    yield client


@pytest.fixture
def grpc_client():
    import grpc

    from api.grpc.proto import execution_pb2_grpc

    channel = grpc.insecure_channel("localhost:50051")
    yield execution_pb2_grpc.WorkflowExecutionStub(channel)
