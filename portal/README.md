# BIS Portal

Resident-facing portal for the Barangay Information System — Vite + React 19 +
Tailwind 4, modeled on `EasyPC/tracker`. Deployed to GitHub Pages at
`https://trinly01.github.io/BIS/`.

## Routes

| Route | Purpose |
|---|---|
| `/` | Home — links to request + track |
| `/request` | Document request form (doc type, name, mobile, purpose) |
| `/track` `/track/:ref/:key` | Status lookup + journey timeline (ref + mobile) |
| `/verify/:serial` | QR landing — authentic/expired/invalid result card |

## Backend

No credentials in the bundle. All data flows through public webhook flows on
`likha-playground.zyberlab.com` (`accountability: all`, server-side validation +
sanitized responses) — see `src/lib/api.js` and `scripts/build_bis_portal.py`:

- `bis_portal_options` GET — document types
- `bis_portal_request` POST — create request (returns `DOC-YYYY-NNNN` + ETA)
- `bis_portal_track` POST — status lookup (request_no/serial/OR + mobile)
- `bis_verify_doc` GET `?serial=` — released certs + active permits

## Dev / build / deploy

```bash
npm install
npm run dev      # http://localhost:5173/BIS/
npm run build    # -> portal/dist
```

Deploys automatically via `.github/workflows/deploy-portal.yml` on pushes that
touch `portal/**`. GitHub Pages SPA fallback: `public/404.html` bounces the
requested path into `sessionStorage` and `index.html` restores it.
