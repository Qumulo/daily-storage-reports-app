#!/bin/sh

cron
python app.py --op server

tail -f /var/log/cron /app/daily_storage_reports-master/*.log
