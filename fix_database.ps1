# Fix Database - Remove old volume and recreate with correct user
Write-Host "Stopping all containers..."
docker stop yandex-market-postgres yandex-market-backend yandex-market-frontend 2>$null
docker rm yandex-market-postgres yandex-market-backend yandex-market-frontend 2>$null

Write-Host "Removing old database volume..."
docker volume rm yandexmarket_postgres_data 2>$null

Write-Host "Starting fresh PostgreSQL container..."
docker-compose up -d postgres

Write-Host "Waiting for PostgreSQL to initialize (10 seconds)..."
Start-Sleep -Seconds 10

Write-Host "Starting all services..."
docker-compose up -d

Write-Host ""
Write-Host "Database reset complete! PostgreSQL will now create:"
Write-Host "  - User: yandex_user"
Write-Host "  - Database: yandex_market"
Write-Host ""
Write-Host "Check logs with: docker-compose logs -f postgres"
