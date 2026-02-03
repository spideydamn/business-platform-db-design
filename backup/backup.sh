#!/bin/bash

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="/backups/${POSTGRES_DB}_${TIMESTAMP}.sql"

echo "[INFO] Starting backup at $TIMESTAMP"

PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"

if [ $? -ne 0 ]; then
    echo "[ERROR] Backup failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

echo "[INFO] Backup saved to $BACKUP_FILE"

# Удаление старых бэкапов, если превышено количество
BACKUPS=($(ls -1t /backups/*.sql 2>/dev/null))

if [ ${#BACKUPS[@]} -gt "$BACKUP_RETENTION_COUNT" ]; then
    for ((i=BACKUP_RETENTION_COUNT; i<${#BACKUPS[@]}; i++)); do
        echo "[INFO] Removing old backup: ${BACKUPS[$i]}"
        rm -f "${BACKUPS[$i]}"
    done
fi
