#!/usr/bin/env bash
set -euo pipefail

has_model=false
for arg in "$@"; do
  case "$arg" in
    --model|--model=*)
      has_model=true
      break
      ;;
  esac
done

allowed_tools="Read Edit webfetch Bash(git:*) Bash(lsof:*) Bash(ls:*) Bash(cat:*) Bash(python:*) Bash(python3:*) Bash(ruby:*) Bash(node:*) Bash(npm:*)"

if [[ "$has_model" == true ]]; then
  exec ept-claude --allowedTools $allowed_tools "$@"
else
  exec ept-claude --model sonnet-4.6 --allowedTools $allowed_tools "$@"
fi
