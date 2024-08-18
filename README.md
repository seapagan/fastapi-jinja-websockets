# Example FastAPI / Websocket application

A quick simple example to show using FastAPI and Jinja templates using
WebSockets to update an already served template.

This also uses `GraphQL` to access the GitHub API, and ties into the 'uvicorn'
default logger to keep consistent formatting.

No attempt has ben made to style this app, it's just for my testing and for
others to learn. Eventually I will add this a a FastAPI/Jinja based projects
showcase.

## GitHub Token

You need to add your GitHub token as an environment variable:

```console
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

> [!IMPORTANT]
> You need to have [poetry](https://python-poetry.org/) installed as that is
> used for dependency management

Install the dependencies and enter the virtualenv:

```console
poetry install
poetry shell
```

Then, run the app using `uvicorn`:

```console
uvicorn main:app --reload
```

Open the app in your browser as <http://localhost:8000> to see the app. There
is a 'Refresh Stats' button to update from the WebSocket
