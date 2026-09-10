# save-context: offline recovery

Read only for an explicitly requested recovery of an interrupted or stuck task.

Offline recovery:

- If the source Codex thread is too long, stuck, or already interrupted before
  `save-context` can complete, do not resume that same thread just to save.
- In a fresh thread, run
  `~/.ai/scripts/save-context-recover
  --thread-id <id>` or `--rollout <jsonl>` to extract a compact recovery packet
  from `~/.codex/sessions` / `~/.codex/archived_sessions`.
- Treat the packet as evidence, not as the context itself. The agent still
  writes a clean context.v3 snapshot with the fixed `save-context` script.
