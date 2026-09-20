#!/bin/sh
set -eu
tag="jw$(date +%s)"
printf 'ALTER USER "%s" WITH PASSWORD $%s$%s$%s$;\n' "$POSTGRES_USER" "$tag" "$POSTGRES_PASSWORD" "$tag" > /tmp/alter-user.sql
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f /tmp/alter-user.sql
rm -f /tmp/alter-user.sql
