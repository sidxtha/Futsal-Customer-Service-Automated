# FutsalHub Support frontend
    npm install && npm run dev
Mock data is on by default. For the real backend: copy `.env.example` to `.env`, set `VITE_USE_MOCK=false`.
Only `POST /api/messages` exists in the backend today; the staff endpoints (`/api/tickets...`) must be added, and FastAPI needs CORSMiddleware.
