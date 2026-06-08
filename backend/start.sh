#!/bin/bash
# SmartJourney backend startup script
cd /home/administrator/software/SmartJourney/backend
source .venv/bin/activate
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio --workers 4
