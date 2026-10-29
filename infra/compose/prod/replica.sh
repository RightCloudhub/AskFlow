#!/bin/sh
set -eu
if [ "$(id -u)" = 0 ]; then
  mkdir -p /var/lib/postgresql/data
  chown postgres:postgres /var/lib/postgresql/data
  chmod 700 /var/lib/postgresql/data
  exec gosu postgres sh /replica.sh
fi
if [ ! -s /var/lib/postgresql/data/PG_VERSION ]; then
  pg_basebackup -h postgres -U replicator -D /var/lib/postgresql/data -R -X stream
fi
exec postgres -c hot_standby=on
