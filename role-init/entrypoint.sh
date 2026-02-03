#!/bin/bash
set -e

IFS=',' read -ra USERS <<< "$ANALYST_NAMES"

cat <<EOF > /tmp/create_roles.sql
-- Создание групповой роли
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analytic') THEN
      CREATE ROLE analytic NOLOGIN;
   END IF;
END
\$\$;

-- Предоставление прав на чтение всем таблицам в public
GRANT USAGE ON SCHEMA public TO analytic;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytic;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytic;
EOF

for user in "${USERS[@]}"; do
  echo "CREATE ROLE ${user} LOGIN PASSWORD '${user}_123' IN ROLE analytic;" >> /tmp/create_roles.sql
done

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_roles.sql
