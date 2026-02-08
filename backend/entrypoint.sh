#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
# Wait for PostgreSQL to be ready with URL-encoded password
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if python -c "
import sys
from urllib.parse import quote_plus
import psycopg2

url = '${DATABASE_URL}'
# URL encode password if needed
if '://' in url and '@' in url:
    scheme, rest = url.split('://', 1)
    auth_part, db_part = rest.rsplit('@', 1)
    if ':' in auth_part:
        user, password = auth_part.split(':', 1)
        password_encoded = quote_plus(password)
        url = f'{scheme}://{user}:{password_encoded}@{db_part}'

try:
    conn = psycopg2.connect(url)
    conn.close()
    print('PostgreSQL is ready!')
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
    echo "PostgreSQL is ready!"
    break
  fi
  attempt=$((attempt + 1))
  if [ $attempt -ge $max_attempts ]; then
    echo "Failed to connect to PostgreSQL after $max_attempts attempts"
    exit 1
  fi
  echo "PostgreSQL is unavailable - sleeping (attempt $attempt/$max_attempts)"
  sleep 1
done

echo "PostgreSQL is up - initializing database"
python init_db.py

echo "Starting application..."
exec "$@"
