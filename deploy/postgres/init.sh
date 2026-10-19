#!/bin/bash
# Runs once, on the first start of the postgres container (empty data dir).
# POSTGRES_DB already created marketmind_core; this adds the other five so
# every service owns its database on the same server, same user and password.
set -euo pipefail

for db in marketmind_orchestrator marketmind_pytrends marketmind_worldbank marketmind_oecd marketmind_undata; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE $db OWNER $POSTGRES_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
  echo "database $db ready"
done
