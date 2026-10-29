#!/bin/sh
set -eu
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=replication_password="$REPLICATION_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE replicator REPLICATION LOGIN PASSWORD %L', :'replication_password') \gexec
SQL
printf '%s\n' 'host replication replicator all scram-sha-256' >> "$PGDATA/pg_hba.conf"
