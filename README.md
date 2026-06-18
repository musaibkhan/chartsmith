# ChartSmith

> Forecast every breaking change **before** you upgrade a Helm chart.

ChartSmith indexes any Helm repo, deep-diffs your `values.yaml` against two
chart versions, scrapes the release notes between them, and asks GPT-4o to
synthesize a per-key migration plan — with severity, exact YAML snippets, and
a recommended stepped upgrade path.

Built for the LGTM stack pain (Loki 6.x → 17.x is painful) but works on any
Helm chart.

## Architecture

```
┌──────────────┐   POST /analyze   ┌──────────────────┐
│  Next.js 16  │ ────────────────► │  FastAPI         │
│  (wizard UI) │ ◄──────────────── │  + helm CLI      │
└──────────────┘    report JSON    │  + DeepDiff      │
                                   │  + GPT-4o        │
                                   └────────┬─────────┘
                                            │
                                   ┌────────▼─────────┐
                                   │  Postgres        │
                                   │  (cached reports │
                                   │   + indexed repos)│
                                   └──────────────────┘
```

## Quick start

```bash
cp .env.example .env       # add your OPENAI_API_KEY
podman-compose up --build  # or docker-compose
```

- Frontend → http://localhost:3000
- Backend  → http://localhost:8000/docs

## Repo layout

```
chartsmith/
├── backend/        FastAPI service (Python 3.11)
├── frontend/       Next.js 16 wizard UI
├── infra/          Postgres init + helper scripts
└── docker-compose.yml
```

See `backend/README.md` and `frontend/README.md` for component-specific docs.

## Status

- [x] Repo indexing (`helm repo add` + search)
- [x] Version dropdown population
- [x] ArgoCD/umbrella wrapper auto-detection
- [x] Values schema diff (DeepDiff)
- [x] `helm template` rendered diff
- [x] GitHub release notes scraping
- [x] GPT-4o synthesis layer
- [ ] Full LGTM stack (v0.2)
- [ ] Slack bot integration (v0.3)
