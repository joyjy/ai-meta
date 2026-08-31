#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: clean-codex-logs.sh [--db PATH]

Delete TRACE rows from Codex logs_2.sqlite and VACUUM the database.
Run this only after fully quitting Codex Desktop. This script intentionally
does not create a backup because its purpose is to reduce disk usage.
EOF
}

db="${HOME}/.codex/logs_2.sqlite"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --db)
      if [ "$#" -lt 2 ]; then
        echo "clean-codex-logs: --db requires a path" >&2
        exit 2
      fi
      db="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "clean-codex-logs: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      echo "clean-codex-logs: unexpected argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ ! -f "$db" ]; then
  echo "clean-codex-logs: database not found: $db" >&2
  exit 1
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "clean-codex-logs: sqlite3 is required" >&2
  exit 1
fi

if command -v lsof >/dev/null 2>&1; then
  open_files="$(lsof "$db" "$db-wal" "$db-shm" 2>/dev/null || true)"
  if [ -n "$open_files" ]; then
    echo "clean-codex-logs: Codex log database is still open; quit Codex Desktop first." >&2
    echo "$open_files" >&2
    exit 1
  fi
fi

echo "==> before"
du -sh "$db"* 2>/dev/null || true

trace_rows="$(sqlite3 "$db" "select count(*) from logs where level = 'TRACE';")"
echo "TRACE rows: $trace_rows"

sqlite3 "$db" <<'SQL'
PRAGMA wal_checkpoint(TRUNCATE);
DELETE FROM logs WHERE level = 'TRACE';
VACUUM;
PRAGMA wal_checkpoint(TRUNCATE);
SQL

echo "==> after"
du -sh "$db"* 2>/dev/null || true
