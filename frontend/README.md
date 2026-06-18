# ChartSmith Frontend

Next.js 16 (App Router, Turbopack) wizard UI for ChartSmith.

```
app/
├── layout.tsx              global styles + font loader
├── page.tsx                the 5-step wizard
└── report/[id]/page.tsx    shareable report links
components/
├── Stepper.tsx
├── steps/
│   ├── RepoStep.tsx
│   ├── ChartStep.tsx
│   ├── VersionStep.tsx
│   └── ValuesStep.tsx
└── Report/
    ├── SummaryCard.tsx
    ├── FindingCard.tsx
    └── UpgradePath.tsx
lib/
├── api.ts                  typed client for the backend
└── theme.ts                shared design tokens
```
