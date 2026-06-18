# ChartSmith Backend — FastAPI service

Wraps the `helm` CLI, runs schema diffs, scrapes GitHub release notes,
and synthesizes upgrade advice via GPT-4o.

## Layout

```
src/
├── main.py                 FastAPI entrypoint, CORS, router wiring
├── api/
│   ├── repos.py            POST /api/v1/repos/index, GET /api/v1/repos
│   ├── charts.py           GET  /api/v1/charts?repo=
│   ├── versions.py         GET  /api/v1/charts/{name}/versions
│   └── analyze.py          POST /api/v1/analyze
├── core/
│   ├── helm_client.py      helm repo add / pull / search / template
│   ├── unwrap.py           auto-detect ArgoCD / umbrella wrapper keys
│   ├── schema_diff.py      DeepDiff-based values diff
│   ├── manifest_diff.py    rendered manifest diff
│   └── changelog.py        GitHub Releases scraper
├── ai/
│   ├── synthesizer.py      GPT-4o structured output
│   └── prompts.py
└── models/
    └── report.py           Pydantic schemas
```
