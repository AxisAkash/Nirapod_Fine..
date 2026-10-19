# Nirapod Fine

A web app that checks Bangladeshi traffic fine receipts (mamla) against structured Road Transport Act 2018 data.
The AI model reads the receipt and writes the explanation. A deterministic rule engine makes every legal decision.

```text
frontend/   Next.js app
backend/    FastAPI + PostgreSQL
contracts/  Hardhat project with the AuditRegistry smart contract
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
| `POST /api/receipts/upload` | Store a JPG/PNG/PDF, hash it, open a case, and read it with the AI (`read=false` to skip) |
| `POST /api/receipts/{id}/read` | Read a stored receipt again |
| `POST /api/cases/manual` | Create and analyse a case from typed fields only |
| `POST /api/cases/{id}/analyze` | Run the engine; optional fields correct the case first; safe to repeat |
| `GET /api/cases`, `GET /api/cases/{id}` | The signed-in user's cases only |
| `GET /api/dummy-url/preview`, `POST /api/dummy-url/analyze` | Mock external mamla source, same pipeline |
| `GET /api/offence-rules` | Active dataset's rules |
| `/api/admin/dataset-versions`, `/offence-rules`, `/exception-rules` | Admin: clone to a draft, edit, activate |

### AI: reading receipts and explanations (optional)

Set `OPENROUTER_API_KEY` in `backend/.env` (model: `OPENROUTER_MODEL`, default `openai/gpt-5.6-luna`). Without a key
everything still works: details are typed in and explanations use fixed templates.

- **Upload** reads the file with the AI (images are shrunk first; PDFs with a text layer are read as text, scans as
  images). It returns the offence, amount, date, location, vehicle, receipt number, section and notes. Each receipt is
  read twice in parallel, and any field the two readings disagree on is flagged "Check this".
- **The user reviews** every field next to the original receipt, and what they confirm or clear always wins over the AI.
- **The explanation** is worded by the AI from the engine's output only. The backend then checks it: any section, law
  reference or amount that the engine did not produce, any link or formatting, and the text is replaced by the template.
- **The AI never decides.** The status always comes from the rule engine. Text printed on a receipt is treated as data.
- **Limits and privacy:** 20 receipt reads per user per hour (`AI_READS_PER_HOUR`). The file is sent to the AI provider to
  be read, and the text read is stored with the receipt. No names, emails or file names are put in any prompt.

Checking accuracy on your own receipts:

```bash
.venv/bin/python scripts/make_receipts.py                    # synthetic receipts (Bangla/English, photos, PDFs, a blurry one)
.venv/bin/python scripts/eval_extraction.py [folder]         # per-field accuracy and cost per receipt (needs a manifest.json)
RUN_LIVE_AI=1 .venv/bin/python -m pytest tests/test_ai_live.py   # real-model checks, a fraction of a cent
```

On the synthetic set, `gpt-5.6-luna` reads about 98% of fields correctly for roughly 0.1 cent per receipt. Its weak spot
is digits in noisy Bangla photos (for example ৪ read as 8), which no second reading catches, so a person must check
the amount and date against the receipt. Switch models with `OPENROUTER_MODEL` and re-run the evaluation.

### Blockchain audit (optional)

The chain stores hashes only, never receipt data. It protects two things: sealed case results and the legal dataset.

- Every analysis is sealed: a salted SHA-256 of the case, receipt fields and result (including the explanation) is
  recorded on-chain. "Verify now" on a result recomputes the hash and compares it with the chain.
- Each dataset version is anchored when activated, with a fingerprint per rule. Before every analysis the rules are
  re-hashed; if they differ from the chain the analysis is refused, and the admin page names the changed rules.
- Database triggers also block edits to the rules of any non-draft version.
- If the chain is unreachable the case is still analysed, flagged "not sealed", and can be retried later.

Local setup (three terminals):

```bash
cd contracts && npm install && npm run node        # local chain on :8545
cd contracts && npm run deploy                     # writes contracts/deployments/localhost.json
cd backend && python -m app.chain anchor           # anchors the active dataset
```

Then set `BLOCKCHAIN_ENABLED=true` in `backend/.env` and restart the API. The local Hardhat chain resets whenever
the node restarts, so redeploy and re-anchor after a restart. For a testnet set `BLOCKCHAIN_RPC_URL`,
`BLOCKCHAIN_PRIVATE_KEY` and `BLOCKCHAIN_CONTRACT_ADDRESS`. Tests use an in-memory chain and never a real one.

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

Done: the dataset and rule engine, the database and API with Clerk sign-in, the frontend, and AI receipt reading and
explanations, and the blockchain audit of results and the legal dataset.

This is an informational tool and not legal advice. The fine limits come from two summary guides, not the statute text.
