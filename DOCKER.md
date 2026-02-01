# Docker Setup Guide

This guide explains how to run the Yandex Market Manager using Docker.

## Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (usually comes with Docker Desktop)

## Quick Start

### 1. Create Environment File

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Yandex Market API credentials:

```env
YANDEX_MARKET_API_TOKEN=your_api_token
YANDEX_MARKET_CAMPAIGN_ID=your_actual_campaign_id
```

### 2. Build and Run (Production)

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Development Mode

For development with hot-reload:

```bash
# Start in development mode
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop
docker-compose -f docker-compose.dev.yml down
```

## Docker Compose Files

### `docker-compose.yml` (Production)
- Builds optimized production images
- Frontend served via Nginx
- Backend runs with uvicorn
- Database stored in `backend/data/` volume

### `docker-compose.dev.yml` (Development)
- Hot-reload enabled for both frontend and backend
- Source code mounted as volumes
- Frontend uses Vite dev server
- Backend uses uvicorn with `--reload`

## Container Details

### PostgreSQL Container
- **Image**: PostgreSQL 15-alpine
- **Port**: 5432 (configurable via `POSTGRES_PORT`)
- **Volume**: `postgres_data` (persistent storage)
- **Health Check**: `pg_isready` command

### Backend Container
- **Image**: Python 3.11-slim
- **Port**: 8000
- **Depends on**: PostgreSQL
- **Health Check**: `/api/health` endpoint

### Frontend Container
- **Production**: Nginx serving built React app
- **Development**: Node.js with Vite dev server
- **Port**: 3000 (mapped to 80 in production)
- **API Proxy**: Routes `/api/*` to backend

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Rebuild Containers
```bash
# Rebuild after code changes
docker-compose build

# Rebuild without cache
docker-compose build --no-cache

# Rebuild and restart
docker-compose up -d --build
```

### Access Container Shell
```bash
# Backend container
docker-compose exec backend bash

# Frontend container (production)
docker-compose exec frontend sh

# Frontend container (development)
docker-compose -f docker-compose.dev.yml exec frontend sh
```

### Database Access
```bash
# Access PostgreSQL via backend container
docker-compose exec backend bash
# Then use psql or Python to connect

# Or connect directly to PostgreSQL container
docker-compose exec postgres psql -U yandex_user -d yandex_market

# Or from host (if port is exposed)
psql -h localhost -p 5432 -U yandex_user -d yandex_market
```

### Clean Up
```bash
# Stop and remove containers
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Environment Variables

All environment variables are passed from the `.env` file to containers. Key variables:

**Database:**
- `POSTGRES_USER` - PostgreSQL username (default: yandex_user)
- `POSTGRES_PASSWORD` - PostgreSQL password (default: yandex_password)
- `POSTGRES_DB` - Database name (default: yandex_market)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)

**Yandex Market:**
- `YANDEX_MARKET_API_TOKEN` - Required (Create in Partner Dashboard → API and modules → Create a new token)
- `YANDEX_MARKET_CAMPAIGN_ID` - Required (Found in Partner Dashboard URL or settings)

**Email (Optional):**
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` - For email sending

**Security:**
- `SECRET_KEY` - Change in production

## Volumes

### Production
- `./backend/data` - Database storage (persists between restarts)

### Development
- `./backend/data` - Database storage
- `./backend/app` - Backend source code (hot-reload)
- `./frontend/src` - Frontend source code (hot-reload)
- `/app/node_modules` - Node modules (excluded from mount)

## Networking

Containers communicate via Docker's internal network:
- Frontend can reach backend at `http://backend:8000`
- Nginx proxy forwards `/api/*` requests to backend
- External access via `localhost:3000` (frontend) and `localhost:8000` (backend)

## Troubleshooting

### Containers won't start
```bash
# Check logs
docker-compose logs

# Check if ports are in use
netstat -an | grep 3000
netstat -an | grep 8000
```

### Database issues
```bash
# Remove database volume and restart
docker-compose down -v
docker-compose up -d

# Check PostgreSQL logs
docker-compose logs postgres

# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U yandex_user
```

### Frontend can't reach backend
- Check backend is running: `docker-compose ps`
- Check backend logs: `docker-compose logs backend`
- Verify API URL in frontend config

### Rebuild after dependency changes
```bash
# Backend dependencies
docker-compose build backend

# Frontend dependencies
docker-compose build frontend

# Both
docker-compose build
```

## Production Deployment

### 1. Update Environment Variables
- Set strong `SECRET_KEY`
- Configure production database (PostgreSQL recommended)
- Set proper `FRONTEND_URL`

### 2. Use Production Compose File
```bash
docker-compose -f docker-compose.yml up -d
```

### 3. Set Up Reverse Proxy (Optional)
Use Nginx or Traefik in front of containers for:
- SSL/TLS termination
- Domain routing
- Load balancing

### 4. Database Backup
```bash
# Backup SQLite database
docker-compose exec backend cp data/yandex_market.db data/yandex_market.db.backup

# Or use volume backup
docker run --rm -v yandex-market_backend_data:/data -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz /data
```

## Docker Images

### Building Individual Images

```bash
# Backend
cd backend
docker build -t yandex-market-backend .

# Frontend (production)
cd frontend
docker build -t yandex-market-frontend .

# Frontend (development)
cd frontend
docker build -f Dockerfile.dev -t yandex-market-frontend-dev .
```

### Running Individual Containers

```bash
# Backend
docker run -p 8000:8000 \
  -e YANDEX_MARKET_API_TOKEN=your_token \
  -v $(pwd)/backend/data:/app/data \
  yandex-market-backend

# Frontend
docker run -p 3000:80 yandex-market-frontend
```

## Health Checks

Both containers have health checks:
- Backend: Checks `/api/health` endpoint
- Frontend: Checks if Nginx is responding

View health status:
```bash
docker-compose ps
```

## Performance Tips

1. **Use Production Build**: Production images are optimized and smaller
2. **Volume Mounts**: In development, only mount necessary directories
3. **Resource Limits**: Set memory/CPU limits in production
4. **Database**: Consider PostgreSQL for production instead of SQLite

## Security Notes

1. **Never commit `.env` file** - It contains secrets
2. **Use secrets management** in production (Docker Secrets, AWS Secrets Manager, etc.)
3. **Update SECRET_KEY** - Generate a strong random key
4. **Network isolation** - Use Docker networks to isolate services
5. **Image scanning** - Regularly scan images for vulnerabilities

## Next Steps

- Set up CI/CD pipeline
- Configure production database (PostgreSQL)
- Set up monitoring and logging
- Configure SSL certificates
- Set up automated backups
