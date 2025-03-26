# Workflow Automation Backend

This Workflow Automation Backend enables users to define, execute, and track workflows with multiple tasks. It offers both RESTful and gRPC APIs, uses a relational database for persistence, integrates Redis for caching, and is containerised for deployment. Ray is also available as an option for concurrent task execution.

## Setup Instructions

### Prerequisites

The project uses the following components but you will only need Docker to run the application.

- **Python 3.12** (Ray doesn’t support Python 3.13)
- **PostgreSQL 17**
- **Redis 7.2.7**

### Running the Application

Go to the project root directory and use Docker Compose to start the application:

```bash
docker-compose up --build
```

This will start all required services:
- PostgreSQL database
- Redis cache
- FastAPI application (REST API)
- gRPC server
- RQ worker for background execution

Access points:
- REST API: https://localhost:8000
- gRPC API: localhost:50051

The gRPC server handles all workflow execution requests. By default, synchronous tasks are processed sequentially and asynchronous tasks are handled using `asyncio`. However, the server also supports using RQ for background processing or Ray for executing asynchronous tasks.

```bash
# Stop the running grpc_server container
docker-compose stop grpc_server

# Start grpc_server with RQ for background processing
docker-compose run --rm grpc_server --use-rq

# OR start grpc_server with Ray for background processing
docker-compose run --rm grpc_server --use-ray
```

## API Documentation

### REST API

**Base URL:** ```http://localhost:8000```

#### Workflow Management

- **Create Workflow:** ```POST /workflows/```

  Request body:
  ```
  {
    "name": "Data Processing Workflow",
    "description": "Process and transform data files"
  }
  ```

  Response:
  ```
  {
    "name": "Data Processing Workflow",
    "description": "Process and transform data files",
    "id": 1,
    "created_at": "2025-03-21T16:12:16.828774",
    "updated_at": "2025-03-21T16:12:16.828894",
    "tasks": []
  }
  ```

- **Get Workflow:** ```GET /workflows/{workflow_id}```
- **List Workflows:** ```GET /workflows/?skip={skip}&limit={limit}```
- **Update Workflow:** ```PUT /workflows/{workflow_id}```
- **Delete Workflow:** ```DELETE /workflows/{workflow_id}```

#### Task Management

- **Add Task:** ```POST /workflows/{workflow_id}/tasks/```

  ```json
  {
    "name": "My Task",
    "description": "A simple task",
    "order": 1,
    "execution_type": "sync",
    "parameters": {}
  }
  ```

- **Update Task:** ```PUT /workflows/{workflow_id}/tasks/{task_id}```
- **Delete Task:** ```DELETE /workflows/{workflow_id}/tasks/{task_id}```

This project includes a [bruno](https://www.usebruno.com/) collection in the directory which you can use for API testing.

### gRPC API

**Server Address:** ```localhost:50051```

#### Endpoints

- **ExecuteWorkflow:** Triggers workflow execution
  ```protobuf
  rpc ExecuteWorkflow (ExecuteWorkflowRequest) returns (ExecuteWorkflowResponse) {}
  ```
- **GetWorkflowStatus:** Retrieves workflow execution status
  ```protobuf
  rpc GetWorkflowStatus (GetWorkflowStatusRequest) returns (WorkflowStatusResponse) {}
  ```

### CLI Usage

This project includes a command-line interface for API interaction:

```bash
# Show help
python cli.py

# Create workflow
python cli.py create "My Workflow" --description "A simple workflow"

# List workflows
python cli.py list --skip 0 --limit 10

# Execute workflow
python cli.py execute 1

# Get execution status
python cli.py status 1
```

You may need to install dependencies first:

```bash
# Create a virtual environment
python3 -m venv myenv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Architectural Decisions

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  REST API   │     │ gRPC Service│     │ Ray Executor│
│  (FastAPI)  │     │             │     │  (Optional) │
└──────┬──────┘     └──────┬──────┘     └───────┬─────┘
       │                   │                    │
       └──────────┬────────┘             ┌──────┘
                  │                      │
         ┌────────▼─────────┐   ┌────────▼──────────┐
         │ Database Service │◄──│ Execution Service │
         └────────┬─────────┘   └───────────────────┘
                  │
         ┌────────▼─────────┐   ┌───────────────────┐
         │      Redis       │◄──│  Worker Service   │
         └────────┬─────────┘   └───────────────────┘
                  │
         ┌────────▼─────────┐
         │   PostgreSQL     │
         └──────────────────┘
```

The project follows a modular architecture with these key components:

### API Layer
- **REST API (FastAPI)** for workflow and task management
- **gRPC API** for workflow execution and status monitoring

### Execution Layer
- Synchronous tasks are executed sequentially by order.
- **asyncio** for asynchronous task execution
- **Redis Queue (RQ) Executor** for background processing
- **Ray Executor** as an alternative for asynchronous task execution

### Database Layer
- **SQLModel** for database model definition
- **PostgreSQL** for persistent storage

### Cache Layer
- **Redis** for performance-enhancing caching
- Responses are cached after access and invalidated when stale

## Testing

Tests are located in the ```tests/``` directory. Run the test suite with:

```bash
pytest
```
