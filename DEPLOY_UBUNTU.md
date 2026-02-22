# Deploy Yandex Market Manager on Ubuntu (without Docker)

These steps are for a **fresh Ubuntu VPS** (22.04 or 24.04). You will install PostgreSQL, Python 3.11, Node.js, run the backend and frontend, and optionally use Nginx in front.

---

## Quick start: one script

From the project root on your Ubuntu server:

```bash
chmod +x setup_and_run.sh
./setup_and_run.sh
```

The script will:

- Install PostgreSQL, Python 3.11, and Node.js (if missing)
- Create database `yandex_market` and user `yandex_user` (password: **yandex_password**)
- Create a Python venv and install all requirements
- Write a `.env` file and run database migrations
- Start the backend in the background and the frontend in the foreground

Open **http://localhost:3000** (or http://YOUR_SERVER_IP:3000) in your browser. To stop the backend later: `kill $(cat .backend.pid)`.

---

## Manual steps (if you prefer)

## 1. Update system and install basics

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git build-essential
```

---

## 2. Install PostgreSQL 15

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Create database and user:

```bash
sudo -u postgres psql -c "CREATE USER yandex_user WITH PASSWORD 'yandex_password';"
sudo -u postgres psql -c "CREATE DATABASE yandex_market OWNER yandex_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE yandex_market TO yandex_user;"
sudo -u postgres psql -c "ALTER DATABASE yandex_market SET timezone TO 'UTC';"
```

*(Change `yandex_password` to a strong password in production.)*

---

## 3. Install Python 3.11 and pip

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
```

---

## 4. Install Node.js 20 (for frontend build)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

---

## 5. Clone the project (or upload your code)

```bash
cd ~
# If using git:
# git clone <your-repo-url> "Yandex Market"
# cd "Yandex Market"

# Or create directory and upload files via scp/sftp, then:
# cd "Yandex Market"
```

---

## 6. Backend: virtualenv and dependencies

```bash
cd ~/Yandex\ Market
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

*(Or install only backend: `pip install -r backend/requirements.txt`.)*

---

## 7. Backend: environment variables

Create a `.env` in the **project root** (or in `backend/` and run from there):

```bash
cd ~/Yandex\ Market
nano .env
```

Add (adjust passwords and URLs to match your VPS):

```env
POSTGRES_USER=yandex_user
POSTGRES_PASSWORD=yandex_password
POSTGRES_DB=yandex_market
SECRET_KEY=your-very-long-random-secret-key-change-this
FRONTEND_URL=http://YOUR_SERVER_IP:3000
PUBLIC_URL=http://YOUR_SERVER_IP:3000
```

For **DATABASE_URL**: the backend expects it when running on the host (not Docker). Add:

```env
DATABASE_URL=postgresql://yandex_user:yandex_password@localhost:5432/yandex_market
```

Save and exit (Ctrl+O, Enter, Ctrl+X in nano).

---

## 8. Backend: run migrations and start

Run from the **backend** directory so Python finds the `app` package. Load `.env` from the project root:

```bash
cd ~/Yandex\ Market/backend
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Keep this terminal open, or run in the background (see “Running in background” below).

Check: `curl http://localhost:8000/api/health`

---

## 9. Frontend: install and run (development mode)

In a **new terminal**:

```bash
cd ~/Yandex\ Market/frontend
npm install
npm run dev
```

Frontend will be at `http://YOUR_SERVER_IP:3000` and will proxy `/api` to `http://localhost:8000`.

---

## 10. (Optional) Frontend: production build and serve

Build:

```bash
cd ~/Yandex\ Market/frontend
npm run build
```

Serve the built files with a simple static server (e.g. `serve`) or Nginx.

**Option A – serve (quick test):**

```bash
sudo npm install -g serve
serve -s dist -l 3000
```

**Option B – Nginx (recommended for production):**

```bash
sudo apt install -y nginx
```

Copy your existing `frontend/nginx.conf` or create a site that serves `frontend/dist` and proxies `/api` to `http://127.0.0.1:8000`. Then:

```bash
sudo systemctl reload nginx
```

---

## 11. Running backend in background (systemd)

Create a service so the backend starts on boot and restarts on failure:

```bash
sudo nano /etc/systemd/system/yandex-backend.service
```

Paste (replace `YOUR_USER` and path if different):

```ini
[Unit]
Description=Yandex Market Backend
After=network.target postgresql.service

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/Yandex Market/backend
Environment="PATH=/home/YOUR_USER/Yandex Market/venv/bin"
EnvironmentFile=/home/YOUR_USER/Yandex Market/.env
ExecStart=/home/YOUR_USER/Yandex Market/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable yandex-backend
sudo systemctl start yandex-backend
sudo systemctl status yandex-backend
```

---

## 12. Firewall (if UFW is enabled)

```bash
sudo ufw allow 22
sudo ufw allow 3000
sudo ufw allow 8000
sudo ufw enable
```

---

## Requirements summary

| Component   | File / location              | Purpose                    |
|------------|-----------------------------|----------------------------|
| Backend    | `backend/requirements.txt`  | All Python deps (complete)|
| Project    | `requirements.txt` (root)  | Same as backend (pip -r)   |
| Frontend   | `frontend/package.json`     | Node deps (npm install)   |

Backend `requirements.txt` includes: FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic, psycopg2-binary, python-jose, passlib, bcrypt, httpx, Jinja2, pypdf, reportlab, and the rest needed for the app. No extra pip packages are required for the current codebase.

---

## Troubleshooting

- **Database connection refused**  
  Ensure PostgreSQL is running: `sudo systemctl status postgresql`.  
  Use `DATABASE_URL=postgresql://...@localhost:5432/...` when running on the same host.

- **ModuleNotFoundError: app**  
  Run uvicorn from the `backend` directory:  
  `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`

- **401 / CORS**  
  Set `FRONTEND_URL` and `PUBLIC_URL` in `.env` to the URL you use in the browser (e.g. `http://144.172.117.31:3000`).

- **SMTP / emails**  
  Configure SMTP in the app Settings and ensure the VPS can reach the SMTP server (e.g. outbound port 587 allowed).
