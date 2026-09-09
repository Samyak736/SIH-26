# frontend-design — demo scaffold

This repository now includes a minimal Next.js frontend under `frontend/` to demo the `sif_dashboard` UI and make the project deployable on Vercel.

Quick start (locally):

1. `npm install --prefix frontend`
2. `npm run dev`

The root scripts delegate to the Next.js app in `frontend/`. The dashboard is
available at `http://localhost:3000`.

To deploy on Vercel: either set the project root to `frontend/` in the Vercel project settings, or rely on the included `vercel.json` which points the build to `frontend/package.json`.
