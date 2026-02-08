# Reset Database Script
# This script will remove old database volumes and recreate them with the correct name

Write-Host "Stopping containers..."
docker-compose down

Write-Host "Removing old database volumes..."
docker volume rm yandex-market_postgres_data 2>$null
docker volume rm yandex-market-postgres_data 2>$null

Write-Host "Creating .env file with correct database name..."
@"
POSTGRES_USER=yandex_user
POSTGRES_PASSWORD=yandex_password
POSTGRES_DB=yandex_market
POSTGRES_PORT=5432

YANDEX_MARKET_API_TOKEN=
YANDEX_BUSINESS_ID=
YANDEX_MARKET_CAMPAIGN_ID=
YANDEX_MARKET_API_URL=https://api.partner.market.yandex.ru
"@ | Out-File -FilePath .env -Encoding utf8

Write-Host "Starting containers with fresh database..."
docker-compose up -d --build

Write-Host "Waiting for database to initialize..."
Start-Sleep -Seconds 10

Write-Host "Database reset complete!"
Write-Host "The database 'yandex_market' should now be created correctly."
