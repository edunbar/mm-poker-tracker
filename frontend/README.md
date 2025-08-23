# Frontend — Poker Analytics App

This folder contains the React + TypeScript frontend for the Poker Analytics App. It uses React Query for data fetching and local UI primitives under `shared/ui`.

## Quick start

```bash
cd /Users/ericdunbar/Developer/mm_poker_tracker/frontend
npm install
npm start
```

App runs at http://localhost:3000 by default.

## Project structure (relevant files)

frontend
├── src
│ ├── app
│ │ ├── App.tsx # App composition / routes
│ │ ├── errors
│ │ │ └── AppErrorBoundary.tsx
│ │ └── providers
│ │ └── QueryProvider.tsx # React Query client/provider
│ ├── index.tsx # root bootstrap (wraps QueryProvider & ErrorBoundary)
│ ├── shared
│ │ └── ui # UI primitives (table, button, etc.)
│ └── features
│ └── game
│ ├── api
│ │ ├── getGame.ts # fetchGameData + useGetGame
│ │ └── uploadGame.ts # uploadGameToSheets + useUploadGame
│ ├── components
│ │ ├── GameActionBar.tsx
│ │ ├── GameDataTable.tsx
│ │ ├── GameStatusCard.tsx
│ │ ├── GameSummaryTiles.tsx
│ │ ├── GameTotals.tsx
│ │ └── GameUrlForm.tsx
│ ├── lib
│ │ ├── deriveTotals.ts
│ │ └── validation.ts
│ └── pages
│ └── GameIngestPage.tsx # container only — composes components + hooks
├── package.json
├── tsconfig.json
└── README.md

## Important notes

- QueryProvider (src/app/providers/QueryProvider.tsx) sets global React Query defaults (no refetch on window focus, retry behavior).
- index.tsx boots the app inside QueryProvider and AppErrorBoundary.
- GameIngestPage is a container only — all presentation and helpers live under `features/game/components` and `features/game/lib`.
- API calls live in `features/game/api` (`getGame.ts`, `uploadGame.ts`). Delete old/duplicate API files to avoid conflicts.
- Shared types are under `src/entities/game/types.ts` — import these in components to keep types consistent (e.g. PlayerInfo.names is string[]).

## Environment / backend

- The frontend expects the backend API at http://localhost:8000 by default (see axios calls in `features/game/api`).
- If your backend URL differs, update axios base URLs or use an environment variable (e.g. REACT_APP_API_URL) and reference it in the API modules.

## Troubleshooting

- Type mismatches between files usually mean different local type definitions — import the canonical type from `src/entities/game/types.ts`.
- If multiple React Query providers exist or provider filename mismatches import paths, ensure `QueryProvider.tsx` filename matches the import in `src/index.tsx`.
- To prevent repeated refetching during table edits, ensure queries are enabled only when a submitted URL exists and that table editing uses local state (the app already copies fetched data into an editable local array).

## Contributing

Add new components under `features/game/components` and helpers under `features/game/lib`. Keep the page component (`pages/GameIngestPage.tsx`) focused on composition only.
