# TFE Frontend Migration Plan

## Goal
Migrate from Streamlit UI to a production-grade web frontend while keeping UF/SES Python logic as backend services.

## Approved Stack
- Frontend: Next.js (React + TypeScript)
- Styling: Tailwind + custom CSS design system
- Backend API: Python service layer (FastAPI recommended)
- Auth/Roles: backend-issued session/JWT + role-based route guards

## Architecture
- `web/`: frontend app (customer and admin interfaces)
- `api/` (next step): backend endpoints for auth, recommendations, watchlist, portfolio, admin
- Existing Python UF/SES modules remain source of decision logic

## Delivery Phases
1. Foundation (current)
- Scaffold Next.js app
- Build modern landing page with top navigation and top-right login actions
- Establish visual system and responsive layout baseline

2. Data Integration
- Create API routes/services for ticker lookup, recommendations, watchlist, portfolio advisor
- Replace placeholder UI blocks with live data

3. Admin Console
- Build admin-only routes
- Add visual asset manager with page-specific hero/overlay config
- Add test-user management and audit views

4. Commerce + Access
- Implement subscription/cart/checkout flows
- Enforce entitlement rules and survey requirements

5. Hardening + Deploy
- E2E tests and accessibility checks
- Production build pipeline and AWS deployment

## First Implementation Step Completed
- Next.js project scaffold created at `web/`
- New polished landing page implemented at `web/src/app/page.tsx`
- Design system implemented at `web/src/app/globals.css`

## Run Commands
- `cd web`
- `npm run dev`

