from fastapi import FastAPI

from api.rest.workflows import router as workflows_router
from db.session import create_db_and_tables

create_db_and_tables()

app = FastAPI(
    title="Workflow Automation Backend",
    description="API to define, execute, and track workflows consisting of multiple tasks.",
    version="1.0.0",
    # lifespan=lifespan,
)

app.include_router(workflows_router)


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


if __name__ == "__main__":
    import os

    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
