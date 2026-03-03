# Run Yandex Market Manager on Windows (PowerShell)

Use these commands when testing on your **Windows laptop** in PowerShell. (For the VPS, use the bash commands in `DEPLOY_UBUNTU.md`.)

---

## Python version: 3.11, 3.12, or 3.13

The project works with **Python 3.11, 3.12, or 3.13**. If you only have 3.13, the backend requirements are set so `pip install` uses pre-built wheels (no Rust needed).

1. Create a new venv (from project root). Use whichever Python you have:

   ```powershell
   cd "C:\Users\ezeki\PycharmProjects\Yandex Market"
   # If you have Python 3.11:  py -3.11 -m venv .venv
   # If you have Python 3.12:  py -3.12 -m venv .venv
   # If you only have Python 3.13 (e.g. C:\Python313):
   py -3.13 -m venv .venv
   # Or with full path:
   # & "C:\Python313\python.exe" -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Then run the backend and frontend as below (use `python -m uvicorn`).

---

## Paths on your machine

- Project root: `C:\Users\ezeki\PycharmProjects\Yandex Market` (note the **space** in "Yandex Market")
- Not valid on Windows: `~/Yandex-Market` (that path doesn’t exist)

---

## 1. Backend (Terminal 1)

From the **project root** (recommended):

```powershell
cd "C:\Users\ezeki\PycharmProjects\Yandex Market"
.\.venv\Scripts\Activate.ps1
cd backend
```

If you’re already in the **backend** folder and need to activate the venv, use one level up:

```powershell
..\.venv\Scripts\Activate.ps1
```

**Database on Windows:** The default config uses host `postgres` (for Docker/Linux). If PostgreSQL runs on your machine, set `DATABASE_URL` in `.env` or `backend\.env` to use `localhost`, for example:

```env
DATABASE_URL=postgresql://yandex_user:YourStrongPassword123!@#@localhost:5432/yandex_market
```

(Use the same user/password/db as in your `.env`; replace the password if yours is different.)

If `.env` is only in the project root, copy it into `backend` once:

```powershell
Copy-Item "..\.env" ".\.env"
```

Start the backend (use `python -m uvicorn` so the venv’s Python is used):

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

(Ensure `backend\.env` exists or that the app can load the root `.env`.)

---

## 2. Frontend (Terminal 2)

```powershell
cd "C:\Users\ezeki\PycharmProjects\Yandex Market\frontend"
npm run dev
```

---

## 3. Open the app

In the browser: **http://localhost:3000**

---

## Why the earlier commands failed

| You ran (Linux/bash) | On Windows PowerShell |
|----------------------|------------------------|
| `cd ~/Yandex-Market` | Path doesn’t exist. Use `cd "C:\Users\ezeki\PycharmProjects\Yandex Market"`. |
| `cd backend` (from backend) | Tries `backend\backend`. From project root use `cd backend` once. |
| `source ../venv/bin/activate` | Use `.\.venv\Scripts\Activate.ps1` (or `..\.venv\Scripts\Activate.ps1` from backend). |
| `export $(grep -v '^#' ../.env \| xargs)` | Not needed if `backend\.env` exists; the app loads it automatically. |

---

## One-liner (backend, from project root)

```powershell
cd "C:\Users\ezeki\PycharmProjects\Yandex Market"; .\.venv\Scripts\Activate.ps1; cd backend; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## If pip install failed (Rust / pydantic-core)

If you see errors about Rust or building pydantic-core, ensure you’re using the project’s **backend/requirements.txt** (pydantic>=2.10 for 3.13 wheels). From project root run `pip install -r requirements.txt`; that file includes the backend. If it still fails, install Python 3.11 or 3.12 and create the venv with that version (see “Python version” above).
