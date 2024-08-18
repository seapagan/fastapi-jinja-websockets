from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
import asyncio
import os
from typing import List

app = FastAPI()
templates = Jinja2Templates(directory="templates")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

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
            stats = await fetch_github_stats()
            for stat in stats:
                await websocket.send_json(stat.dict())
    except WebSocketDisconnect:
        print("WebSocket disconnected")


# HTML template (you would typically save this in a separate file)
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>GitHub Project Stats</title>
    <script>
        let ws;
        function connectWebSocket() {
            ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const projectElement = document.getElementById(data.name);
                if (projectElement) {
                    projectElement.innerHTML = `${data.name}: ${data.stars} stars, ${data.forks} forks`;
                }
            };
            ws.onopen = function() {
                console.log("WebSocket connected");
                requestUpdate();
            };
            ws.onclose = function() {
                console.log("WebSocket disconnected. Reconnecting in 5 seconds...");
                setTimeout(connectWebSocket, 5000);
            };
        }
        
        function requestUpdate() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send("update");
            }
        }

        window.onload = connectWebSocket;
    </script>
</head>
<body>
    <h1>GitHub Project Stats</h1>
    <button onclick="requestUpdate()">Refresh Stats</button>
    <ul>
    {% for project in projects %}
        <li id="{{ project.name }}">{{ project.name }}: Loading...</li>
    {% endfor %}
    </ul>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
