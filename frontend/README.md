# App-apply — frontend

PWA React (Vite) consumata dall'API Django in `../backend`. Vedi `sprints/sprint-18.md` per dettagli.

## Sviluppo

```
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Il dev server proxya `/api`, `/accounts`, `/admin`, `/media`, `/static` verso `VITE_BACKEND_URL` (default `http://localhost:8000`).

## Build

```
npm run build
```

## Test e2e (Playwright)

```
npx playwright test
```

Richiede il backend Django e il dev server Vite attivi su `http://localhost:5173`.
