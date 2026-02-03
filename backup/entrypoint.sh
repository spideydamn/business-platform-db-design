#!/bin/bash

# Запись значений ENV в crontab
envsubst < /crontab.txt > /tmp/crontab.txt
crontab /tmp/crontab.txt

# Запуск cron + удержание контейнера
crond -f -l 2
