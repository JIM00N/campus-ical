web: python -m scripts.seed_schools && uvicorn app.main:app --host 0.0.0.0 --port $PORT
cron: python -m app.tasks.update_schools
