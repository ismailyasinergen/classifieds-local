# Backups

Use these scripts from the project root.

Create a database backup:

bash scripts/backup_postgres.sh

Create a media backup:

bash scripts/backup_media.sh

Restore a database backup:

bash scripts/restore_postgres.sh backups/postgres_YYYYMMDD_HHMMSS.sql.gz

Restore a media backup:

bash scripts/restore_media.sh backups/media_YYYYMMDD_HHMMSS.tar.gz

Notes:
- Database backups are saved into the local backups folder.
- Media backups are saved into the local backups folder.
- Restore commands ask for confirmation before running.
- In production, copy backups off the server regularly.
- For real production, also use server-level or managed-database backups.
