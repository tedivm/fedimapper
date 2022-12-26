#!/usr/bin/env bash

echo "FastAPI Prestart Script Running"

echo "Run Database Migrations"
python -m alembic upgrade head

