#!/bin/bash

BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "Creating backup: $DATE"

# Backup database
pg_dump -U lableadger_user -d lableadger_db > $BACKUP_DIR/db_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /var/www/projects/LabLedger-Backend/media/

# Backup code (optional)
tar -czf $BACKUP_DIR/code_$DATE.tar.gz /var/www/projects/LabLedger-Backend/ --exclude=venv --exclude=media

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
