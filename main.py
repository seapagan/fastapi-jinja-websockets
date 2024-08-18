import logging
import os
from typing import List

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

logger = logging.getLogger("uvicorn")

# List of projects (owner/name pairs)
projects = [
    {"owner": "tiangolo", "name": "fastapi"},
    {"owner": "encode", "name": "starlette"},
    {"owner": "pallets", "name": "flask"},
    {"owner": "django", "name": "django"},
    {"owner": "seapagan", "name": "fastapi-template"},
    # Add more projects as needed
]


class ProjectStats(BaseModel):
    name: str
    stars: int
    forks: int


def generate_graphql_query(projects: List[dict]) -> tuple[str, dict]:
    query_parts = []
    variables = {}

    for i, project in enumerate(projects):
        query_part = f"""
        repo{i}: repository(owner: $owner{i}, name: $name{i}) {{
            name
            stargazerCount
            forkCount
        }}
        """
        query_parts.append(query_part)
        variables[f"owner{i}"] = project["owner"]
        variables[f"name{i}"] = project["name"]

    query = (
        "query("
        + ", ".join(
            f"$owner{i}: String!, $name{i}: String!" for i in range(len(projects))
        )
        + ") {"
        + "\n".join(query_parts)
        + "}"
    )

    return query, variables


async def fetch_github_stats():
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    query, variables = generate_graphql_query(projects)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
        )
        data = response.json()

        results = []
        for i in range(len(projects)):
            repo_data = data["data"][f"repo{i}"]

            results.append(
                ProjectStats(
                    name=repo_data["name"],
                    # owner=repo_data["owner"],
                    stars=repo_data["stargazerCount"],
                    forks=repo_data["forkCount"],
                )
            )

        return results


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "projects": projects}
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            logger.info("Update requested via WebSocket")
            stats = await fetch_github_stats()
            for stat in stats:
                await websocket.send_json(stat.dict())
    except WebSocketDisconnect:
        logger.warning("WebSocket disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
