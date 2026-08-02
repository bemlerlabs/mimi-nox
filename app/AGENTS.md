# MiMi Nox App

## Stack
- React 19 + Vite 6 + TypeScript
- Tailwind CSS v4
- React Router (HashRouter)
- date-fns, lucide-react

## Commands
- `npm run dev` — Vite dev server
- `npm run build` — tsc -b && vite build
- `npm run preview` — Vite preview

## Conventions
- components/ nach Feature (dashboard/, landing/, ui/)
- ui/ für shared primitives (Button, Card, Input)
- lib/ für utilities (api.ts, utils.ts)
- Keine Class Components, nur Function Components + Hooks
- Tailwind utility classes, kein CSS-in-JS

## Build
- index.html im Projekt-Root (nicht in src/)
- `@/` alias zeigt auf `src/`
- TypeScript strict mode
