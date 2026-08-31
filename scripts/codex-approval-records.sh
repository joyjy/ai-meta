#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: codex-approval-records.sh [--db PATH] [--limit N] [--raw] [--sql]

Select recent Codex approval request records from logs_2.sqlite.

This reads the desktop log database only. It is useful for a quick spot check,
but it can miss older approval requests that only remain in session JSONL files.
EOF
}

db="${HOME}/.codex/logs_2.sqlite"
limit=50
raw=0
print_sql=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --db)
      if [ "$#" -lt 2 ]; then
        echo "codex-approval-records: --db requires a path" >&2
        exit 2
      fi
      db="$2"
      shift 2
      ;;
    --limit)
      if [ "$#" -lt 2 ]; then
        echo "codex-approval-records: --limit requires a number" >&2
        exit 2
      fi
      limit="$2"
      shift 2
      ;;
    --raw)
      raw=1
      shift
      ;;
    --sql)
      print_sql=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "codex-approval-records: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      echo "codex-approval-records: unexpected argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$limit" in
  ''|*[!0-9]*)
    echo "codex-approval-records: --limit must be a non-negative integer" >&2
    exit 2
    ;;
esac

if [ ! -f "$db" ]; then
  echo "codex-approval-records: database not found: $db" >&2
  exit 1
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "codex-approval-records: sqlite3 is required" >&2
  exit 1
fi

if [ "$raw" -eq 1 ]; then
  fields="id, datetime(ts, 'unixepoch', 'localtime') as local_time, level, target, thread_id, feedback_log_body"
else
  fields="id, datetime(ts, 'unixepoch', 'localtime') as local_time, level, target, thread_id, substr(feedback_log_body, max(1, instr(feedback_log_body, 'sandbox_permissions') - 180), 900) as approval_context"
fi

sql=$(cat <<SQL
select
  ${fields}
from logs
where feedback_log_body like '%,\\"sandbox_permissions\\":\\"require_escalated\\"%'
  and feedback_log_body like '%response.output_item.done%'
  and target = 'codex_api::endpoint::responses_websocket'
order by ts desc, ts_nanos desc, id desc
limit ${limit};
SQL
)

if [ "$print_sql" -eq 1 ]; then
  printf '%s\n' "$sql"
  exit 0
fi

sqlite3 -header -column "$db" "$sql"
