# RuleShift — Personalized Policy Change & Eligibility Simulator

**Evidence-grounded, deterministic policy comparisons with applicant-specific counterfactuals.**

RuleShift is a local-first React + FastAPI project that compares two text-based policy PDFs, aligns numbered clauses, extracts explicitly stated eligibility constraints, evaluates saved applicant profiles, and displays the source evidence behind each outcome. No paid model, API key, or cloud account is required.

> **Important:** This tool is informational, not an official eligibility decision. Human review of extracted rules is essential. The included policies and applicant profiles are **fictional synthetic test data**, not actual government notices or real people.

## What's implemented

- Separate database records for policy families, original PDF versions, clauses, extracted rules, and applicant profiles.
- Embedded-text PDF extraction with PyMuPDF; exact originating page number retained.
- Weighted RapidFuzz-based lexical clause alignment and added / removed / modified / unchanged classification.
- Deterministic detection of age bounds (with explicit as-of date), degree level, marks, annual family income, explicit category allowlists, deadlines, and required documents.
- Policy rule edits / additions / rejections with source quote checking, human review status and notes.
- Before/after eligibility with **eligible**, **ineligible**, **undetermined**, proof excerpts, missing fields, extraction warnings and contradictory rule detection.
- Applicant-specific differences: changed clauses that actually change an applicant's field result, rather than just textual differences.
- Rendered original-page evidence, searchable policy history, locally generated downloadable PDF comparison reports.
- Responsive SaaS-style dashboard, upload zones, clause comparison, profile forms, review editor and error / loading / empty states.
- 8 generated synthetic PDF versions, 7 ready-to-seed demo profiles, 15 labeled evaluation cases, 32 backend tests, GitHub Actions.

## Requirements

- Windows 10/11 and VS Code
- Python **3.12** recommended (`py -3.12 --version`)
- Node.js **20.19+ or 22+**, npm (Node 22 LTS recommended; newer Node versions are typically fine)
- Git; optionally the GitHub CLI (`gh`)

### Install Python 3.12 if it's missing

Open a **new PowerShell** window:

```powershell
py -3.12 --version
```

If the launcher reports that 3.12 is missing, install it (Windows Package Manager):

```powershell
winget install --id Python.Python.3.12 --exact
```

Close and reopen PowerShell, then check `py -3.12 --version` again. Alternatively install it from https://www.python.org/downloads/ and select **Add python.exe to PATH** during setup. It is okay to have several Python versions; the explicit `py -3.12` command chooses the right one.

If Node/npm is missing, install Node.js LTS from https://nodejs.org/; check with `node --version` and `npm.cmd --version`.

## 1. Unzip and open in VS Code

Extract the ZIP to a folder named `RuleShift` (for example, inside your Desktop or Documents folder). In VS Code, use **File → Open Folder → RuleShift**.

In the VS Code PowerShell terminal, verify you're at the repository root:

```powershell
Get-ChildItem
```

You should see `backend`, `frontend`, `samples`, `scripts`, and `README.md`.

## 2. Install and initialize the backend

**PowerShell terminal 1** — from the `RuleShift` root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "from app.database import init_db; init_db(); print('Database ready')"
```

This creates `backend/data/ruleshift.db` and a local `backend/data/uploads/` folder once the API runs. The environment file is ignored by Git.

**Optional — prepopulate the whole demonstration library:**

```powershell
.\.venv\Scripts\python.exe ..\scripts\seed_demo.py
```

This is idempotent: rerunning it will not recreate policies and demo profiles with the same names. The demo seed creates four fictional policy families (eight PDFs) and seven fictional applicant profiles.

Start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check:

- Health endpoint: **http://127.0.0.1:8000/api/health**
- Interactive REST documentation: **http://127.0.0.1:8000/docs**

Keep this terminal open.

## 3. Install and run the React frontend

**PowerShell terminal 2** — open a second terminal at the `RuleShift` root:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open **http://127.0.0.1:5173** in a browser. Vite forwards `/api` requests to the FastAPI backend on port 8000.

On subsequent sessions, you can start both processes from the root using separate PowerShell windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```

```powershell
powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1
```

Neither script starts a public server; both bind to `127.0.0.1`.

### If PowerShell blocks commands

The commands above explicitly call `python.exe` and `npm.cmd`, so you **do not need to activate the Python virtual environment** or permanently change PowerShell's execution policy. To run the provided `.ps1` start scripts, use `powershell -ExecutionPolicy Bypass -File ...` as shown.

## 4. Verify the full application with sample PDFs

If you **didn't seed** the demo earlier:

1. Click **Upload policies**.
2. Policy name: `Student Advancement Support Scheme`.
3. Previous PDF: `samples/student_aid_old.pdf`.
4. Updated PDF: `samples/student_aid_new.pdf`.
5. Click **Analyze policy changes**.
6. Open **Applicant profiles**, create the applicant below, and save.
7. Return to **Compare & simulate**, choose the two versions and that applicant, and click **Run simulation**.

Use this **fictional** applicant:

| Field | Value |
|---|---|
| Profile name | `Asha – marks tightened` |
| Date of birth | `2003-01-01` |
| Education level | `Bachelor's degree` |
| Marks | `62` |
| Annual income INR | `700000` |
| Category | `EWS` |
| Application date | `2026-08-15` |
| Documents | `identity proof, degree certificate, income certificate` |

**Expected:** previous **eligible** → updated **ineligible**; applicant-specific changes include marks increasing from **60% to 65%**, and an additional **residence proof** document. Open the changed clause and inspect the highlighted source PDF page. Choose **Download PDF report** to generate an actual report.

If the demo was seeded, all corresponding policies and profiles are already available in their menus; just choose them and run the simulation.

### Additional scenarios

- `Rohan – newly eligible` (preloaded by the seed): **ineligible → eligible**, after relaxation of age, income and deadline thresholds.
- `Meera – no impact`: **eligible → eligible**, despite actual policy text changes.
- `Unknown marks`: **undetermined → undetermined** rather than a guessed threshold outcome.
- `Experimental Merit Award`: contradictory min/max marks in the updated policy return **undetermined** and show conflicts.
- Open **Rule review** to see extracted JSON thresholds, replace a rule, mark it pending or rejected, or manually add an evidence-backed interpretation. Rerun the simulator to see the effect.

All PDFs in `samples/` are made by `scripts/generate_samples.py`; the benchmark labels live in `samples/evaluation_cases.json`. To regenerate the corpus, from the backend directory with the venv installed:

```powershell
.\.venv\Scripts\python.exe ..\scripts\generate_samples.py
```

## 5. Run backend tests and evaluation

**PowerShell** from the `RuleShift` root (not from `backend`):

```powershell
$env:PYTHONPATH = "$PWD\backend;$PWD"
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q
.\backend\.venv\Scripts\python.exe scripts\evaluate.py
```

The evaluation script prints actual outcomes and timings and updates `samples/evaluation_results.json`. It returns an error code if any expected policy decision or impact label is mismatched.

### Measured development benchmark

On the supplied **15-case synthetic hand-labeled dataset**, with 30 before/after eligibility decisions, this repository's evaluation run produced:

| Metric | Basic PDF text-difference baseline | RuleShift structured engine |
|---|---:|---:|
| Applicant-impact precision | **40.0%** | **100.0%** |
| Applicant-impact recall | **100.0%** | **100.0%** |
| Eligible/ineligible/undetermined accuracy | N/A — no decisions | **100.0% (30/30)** |
| Eligibility decision coverage | **0%** | **100%** |
| Median measured runtime (this environment) | **4.376 ms** | **16.314 ms** |

The baseline predicts that **every applicant is affected whenever the full extracted document text changes**, so it has many false positives. It cannot classify eligibility; treating its unprovided statuses as correct would fabricate a comparison. The structured approach opens both PDFs, extracts and aligns clauses, and evaluates profile-specific rules. Runtime includes extraction and differs by hardware; the saved JSON contains actual timings from the run, not promised performance. A result of 100% here is **not** an estimate of real-world performance and is likely optimistic because the benchmark is small and in-domain.

The evaluation is reproducible with `python scripts/evaluate.py`; all corpus inputs, expected labels, and per-case predicted outputs are included. More diverse independent real-world annotations would be required before claiming production accuracy.

### Frontend production build

```powershell
cd frontend
npm.cmd run build
```

The built static site will be in `frontend/dist/` and is excluded from Git. `npm.cmd run dev` is the supported local deployment, requiring no separate Nginx/server configuration. GitHub Actions builds it again on each push/PR.

## 6. Push RuleShift to your GitHub

You only need to do this **after extracting the ZIP and completing the setup**. First create an empty new GitHub repository named **RuleShift** at https://github.com/new. Choose **Public** if you want recruiters to view it. **Do not** check "Add a README", "Add .gitignore", or "Choose a license"; those files are already inside this project.

Then, in VS Code PowerShell at the **RuleShift repository root**, run:

```powershell
git --version
git init
git branch -M main
git status
git add .
git commit -m "Build RuleShift policy eligibility simulator"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/RuleShift.git
git push -u origin main
```

**Replace `YOUR_GITHUB_USERNAME`** with your exact GitHub username. `git push` may open a browser for Git Credential Manager authentication. GitHub does not accept your account password for a Git HTTPS push; use the browser sign-in or a personal access token if requested.

If Git asks for your identity, set it once and retry the commit:

```powershell
git config --global user.name "YOUR DISPLAY NAME"
git config --global user.email "YOUR GITHUB EMAIL"
git commit -m "Build RuleShift policy eligibility simulator"
git push -u origin main
```

If `remote origin already exists` appears, run:

```powershell
git remote set-url origin https://github.com/YOUR_GITHUB_USERNAME/RuleShift.git
git push -u origin main
```

**Alternative with GitHub CLI**, if `gh` is installed and you're signed in (no need to make a repository in the browser first):

```powershell
gh auth login
git init
git branch -M main
git add .
git commit -m "Build RuleShift policy eligibility simulator"
gh repo create RuleShift --public --source . --remote origin --push
```

Open your new repository and check the **Actions** tab for the two jobs: backend test/evaluation and frontend build. The `.gitignore` already excludes personal SQLite databases, uploaded policy files, Python virtual environments, `.env` files, and `node_modules`. Commit only the synthetic sample corpus.

For later changes:

```powershell
git add .
git commit -m "Improve policy extraction and review UI"
git push
```

## Local data, privacy and limitations

- **Local-first:** FastAPI and Vite run on loopback `127.0.0.1` and send no documents or profiles to cloud services. There are no analytics scripts, paid AI calls or remote API keys.
- **Access:** The API has **no login/authentication**. It is intended only for a single trusted local user's laptop, **not** internet/LAN deployment. Do not expose port 8000 or 5173 publicly. Requests with foreign browser origins are rejected for mutations, and API data is marked `Cache-Control: no-store`.
- **Storage:** PDF files, applicants (including personal fields), and rules are stored **unencrypted** on your laptop in `backend/data/`. Use Windows drive encryption/BitLocker and a trusted Windows account for additional at-rest protection. Never commit this folder to Git. Deleted data is removed through the app, but SQLite deletion is **not secure erasure** of disk sectors or backups.
- **Documents:** Only text-extractable PDFs are supported. Scanned images, complicated layouts, inconsistent tables, cross-references, exceptions and jurisdiction-specific terms may require human review. Automatic extraction is intentionally conservative. Some nuanced rules may remain unparsed.
- **Education:** `education_level` compares explicitly stated levels only. Field-of-study requirements are flagged for manual review, rather than silently approximated.
- **Counterfactuals:** If a verified rule fails, the result can be ineligible even when unrelated profile fields are missing. Conflicting accepted rules always force **undetermined**. Unparsed mandatory language, pending rules and missing required inputs block a positive decision.
- **Manual edits:** A quote must occur in the original clause, but the reviewer remains responsible for ensuring any manually entered JSON faithfully represents its source. Modified rules are marked as manual and carry a reviewer note.
- **Database:** SQLAlchemy models are database-portable; SQLite is the zero-setup default. PostgreSQL is optional via a locally running instance: install `psycopg[binary]` and set `DATABASE_URL=postgresql+psycopg://...` in `backend/.env`. The MVP uses `create_all` instead of migrations.

## Troubleshooting

| Issue | Fix |
|---|---|
| `py -3.12` is missing | Install Python 3.12; reopen PowerShell. Never rely on an unsupported default interpreter. |
| `No module named pip` | Create the **3.12** virtual environment first and use `backend\.venv\Scripts\python.exe -m pip`; do not use a broken global Python install. |
| `npm.ps1 cannot be loaded` | Use **`npm.cmd install`** and **`npm.cmd run dev`**. |
| `npm ENOENT` / `package.json` missing | `cd frontend` first; the repo root has no `package.json`. |
| API connection error in the UI | Keep backend running on `127.0.0.1:8000`; check `/api/health`. |
| Port 5173 in use | Close the old Vite process; this project expects port 5173. |
| Port 8000 in use | Stop the other FastAPI process, or update `frontend/vite.config.js` proxy and startup command together. |
| PDF reports no eligibility result | Create a profile and run the simulation; missing applicant fields can legitimately return `undetermined`. |
| Scanned PDF fails extraction | Export a text-based version from an authorized source. The MVP does not implement OCR. |
| `git` is not recognized | Install Git for Windows from https://git-scm.com/downloads/win, then reopen VS Code. |
| Git push is rejected | Confirm the remote username/repo, authenticate, and create an **empty** GitHub repository. |

## API endpoints (summary)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Local API health |
| GET | `/api/dashboard` | Workspace counts and recent policies |
| POST | `/api/policies/upload-pair` | Upload old/new PDFs |
| POST | `/api/policies/{id}/versions` | Add a subsequent version |
| GET | `/api/policies?search=` | Search policy history |
| GET | `/api/versions/{id}` | Clauses, rules, warnings and page refs |
| GET | `/api/versions/{id}/pages/{page}/image` | Render original page |
| POST/PATCH/DELETE | `/api/versions/{id}/clauses/{id}/rules`, `/api/rules/{id}` | Human rule review |
| GET/POST/PATCH/DELETE | `/api/applicants` | Local applicant profile management |
| POST | `/api/simulations` | Counterfactual eligibility and impacts |
| GET | `/api/reports/comparison.pdf` | Download report with evidence |

Swagger/OpenAPI at `/docs` shows exact schemas, validation and example request structure.

## Resume-ready bullets (implemented and measurable)

- Developed **RuleShift**, a local-first React/FastAPI application for evidence-grounded policy version comparison and counterfactual applicant eligibility, using SQLAlchemy and SQLite.
- Implemented **deterministic extraction of seven eligibility criterion types** from text-based PDFs with page-referenced evidence, rule review controls and ambiguity/conflict handling.
- Built an applicant-specific rule impact engine distinguishing eligibility-changing amendments from cosmetic text changes, with three-state outcomes and downloadable PDF audit reports.
- Evaluated against **15 synthetic applicant scenarios / 30 labeled decisions**; achieved **100% impact precision/recall and 30/30 decision agreement** on the included in-domain synthetic corpus, versus **40% impact precision** for the plain text-diff baseline.
- Added **32 automated backend tests** covering PDF parsing, clause alignment, validation, SQLite persistence, API workflows, decision logic and report generation, plus GitHub Actions quality gates.

## License

MIT — see [LICENSE](LICENSE).
