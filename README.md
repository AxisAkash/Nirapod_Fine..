# Nirapod Fine

A web app that checks Bangladeshi traffic fine receipts (mamla) against structured Road Transport Act 2018 data.
The AI model reads the receipt and writes the explanation. A deterministic rule engine makes every legal decision.

```text
frontend/   Next.js app (Phase 3)
backend/    FastAPI + PostgreSQL
data/source The two source PDFs the rules are derived from
```

## Backend

Requires Python 3.13 and Docker (for PostgreSQL).

```bash
docker compose up -d                       # PostgreSQL 17 on :5432, plus a nirapod_test database
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/alembic upgrade head             # create the tables
.venv/bin/python -m app.seed               # load the 42 offence rules and 15 exception rules (safe to repeat)
.venv/bin/uvicorn app.main:app --reload    # http://localhost:8000/docs
```

Try it without any sign-in service. `AUTH_MODE=dev` accepts `Authorization: Bearer dev-user` (or `dev-admin`):

```bash
.venv/bin/python -m app.engine "over speed" --amount 3000 --vehicle motorcycle     # engine only, no database
curl -H "Authorization: Bearer dev-user" -H "Content-Type: application/json" \
     -d '{"reason":"exceeding speed limit","amount":15000,"section":"87"}' localhost:8000/api/cases/manual
```

### Tests

```bash
.venv/bin/python -m pytest -q              # engine tests need nothing; API tests use the nirapod_test database
.venv/bin/python scripts/verify_seed.py    # compares every section and fine limit with the fines PDF (needs pdftotext)
```

### Authentication

`AUTH_MODE=clerk` verifies Clerk session tokens (RS256, issuer and optional audience). Set `CLERK_ISSUER`
(or `CLERK_JWKS_URL`). The admin role comes from the Clerk user's public metadata `{"role": "admin"}` or from
`ADMIN_EMAILS`. `AUTH_MODE=dev` is refused when `ENVIRONMENT=production`.

### API

| Endpoint | Purpose |
|---|---|
| `GET /api/me` | Signed-in user and role |
| `POST /api/receipts/upload` | Store a JPG/PNG/PDF, hash it, open a case (optional typed fields) |
| `POST /api/cases/manual` | Create and analyse a case from typed fields only |
| `POST /api/cases/{id}/analyze` | Run the engine; optional fields correct the case first; safe to repeat |
| `GET /api/cases`, `GET /api/cases/{id}` | The signed-in user's cases only |
| `GET /api/dummy-url/preview`, `POST /api/dummy-url/analyze` | Mock external mamla source, same pipeline |
| `GET /api/offence-rules` | Active dataset's rules |
| `/api/admin/dataset-versions`, `/offence-rules`, `/exception-rules` | Admin: clone to a draft, edit, activate |

### How it works

- `backend/app/engine/` is plain Python with no database or AI imports: normalise, score every rule, pick the
  section, check the amount (including the repeat-offence rule), check exceptions, choose one status.
- Rules live in PostgreSQL. The active dataset version is read-only; admins edit a draft and then activate it, so
  earlier cases keep pointing at the exact version they were checked against.
- Repeat offence (thesis rule): allowed fine = `min(previous fine x 2, maximum for the section)`. Only fines that
  were themselves within the limit count as history.
- The statuses: `VALID`, `INVALID_FINE_TOO_HIGH`, `INVALID_REASON_MISMATCH`, `VALID_BUT_EXCEPTION_POSSIBLE`,
  `INVALID_EXCEPTION_NOT_APPLICABLE`, `NEEDS_MANUAL_REVIEW` (plus `PENDING_ANALYSIS` before a case is analysed).

## Status

Phase 1 (dataset and engine) and Phase 2 (database, API, auth, storage) are done. Receipt reading with OCR and
OpenRouter, the blockchain audit record and the frontend come next.

This is an informational tool and not legal advice. The fine limits come from two summary guides, not the statute text.
