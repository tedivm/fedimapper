#!/usr/bin/env bash

echo "Fedimapper Ingester Prestart Script Running"

sleep 10

echo "Run Database Migrations"
python -m alembic upgrade head
