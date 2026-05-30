#!/bin/bash
set -e
cd backend
exec gunicorn \
  --worker-class gthread \
  --workers 1 \
  --threads 5 \
  --bind 0.0.0.0:$PORT \
  --timeout 120 \
  api.server:app
