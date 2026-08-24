# HL

A minimal Node.js task manager: an Express REST API with an in-memory store and a static single-page frontend. It exists to provide a real, runnable development experience for Cloud Agents.

## Requirements

- Node.js >= 20 (developed on Node 22)
- npm

## Getting started

```bash
npm ci        # install dependencies (use `npm install` for a fresh lockfile)
npm run dev   # start the dev server with auto-reload on http://localhost:3000
```

Then open http://localhost:3000 to use the task manager UI.

## Scripts

| Command | Description |
| --- | --- |
| `npm start` | Start the production server |
| `npm run dev` | Start the server with `--watch` auto-reload |
| `npm test` | Run the test suite (`node --test`) |
| `npm run lint` | Lint with ESLint |

## REST API

Base path: `/api`

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/tasks` | List all tasks |
| `POST` | `/api/tasks` | Create a task — body `{ "title": "..." }` |
| `PATCH` | `/api/tasks/:id` | Update `title` and/or `done` |
| `DELETE` | `/api/tasks/:id` | Delete a task |

A `GET /health` endpoint returns `{ "status": "ok" }`.

## Project layout

```
src/app.js      Express app factory (routes + in-memory store)
src/server.js   HTTP entrypoint
public/         Static frontend (HTML/CSS/JS)
test/           node:test suite exercising the API
```
