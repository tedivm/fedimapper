#!/usr/bin/env bash

echo "Fedimapper Ingester Prestart Script Running"

echo "Run Database Migrations"
python -m alembic upgrade head
