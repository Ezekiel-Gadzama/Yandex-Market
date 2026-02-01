#!/bin/bash
echo "Starting Yandex Market Manager Backend..."
cd backend
python -m uvicorn app.main:app --reload --port 8000
