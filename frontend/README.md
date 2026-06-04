# Frontend — EchoscopeAI Dashboard

**Next.js 14 (App Router) + TypeScript + Tailwind CSS**, professional UI with **dark/light mode**.

> Note: the HLD specified Vite; this was built in **Next.js** per the project owner's request.

## Stack

- Next.js App Router, React 18, TypeScript, Tailwind (`darkMode: "class"`) + `next-themes`
- **Zustand** (auth store, persisted) + **TanStack React Query** (server state, polling)
- **Axios** client with JWT attach + **auto-refresh on 401** (`src/lib/api.ts`)
- **Recharts** (area/line/pie/bar), **react-hot-toast**, **lucide-react** icons
- Real-time via `src/hooks/useWebSocket.ts` + `useDashboardSocket.ts` (→ notification-service WS)

## Pages

- `/login`, `/register` — auth
- `/dashboard` — KPI cards, mention-volume area chart, recent alerts, **live WS** indicator
- `/mentions` — filterable, paginated mention feed
- `/analytics` — tabs: Trends / Sentiment (pie) / Keywords (bar) / Sources
- `/alerts` — alert-rule create/list/delete + triggered history
- `/reports` — generate PDF/CSV, poll status, download

`src/components/html-content.tsx` renders trusted server HTML via `dangerouslySetInnerHTML`.

## Run

```bash
cp .env.local.example .env.local     # NEXT_PUBLIC_API_BASE=http://localhost:8000, WS=ws://localhost:8005
npm install
npm run dev                          # http://localhost:3000
```

Requires the API gateway (:8000) + notification WS (:8005) running. `npm run build` type-checks + builds.
