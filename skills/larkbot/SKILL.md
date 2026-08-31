---
name: larkbot
description: "Use the local larkbot for common agent-facing Feishu workflows: send the user a bot message, send or reply in chats, read local chat history, inspect ticket snapshots, collect meeting context, or diagnose the larkbot runtime. Do not use it for Feishu Docs, Base, contacts, tasks, or other native product APIs."
---

# larkbot

Resolve the larkbot project root from the active project route; use `~/Documents/me/Projects/larkbot` only when that directory exists. Do not search by basename or guess another checkout. Ordinary command invocation is self-contained below. Read the project `AGENTS.md` before modifying or debugging larkbot, and load only the README or architecture shard needed by that engineering task.

## Intent Routes

- “bot 给我发消息”“给我发个飞书”“通知我”：`./larkbot me <text>`. This is the canonical high-frequency path and resolves the owner from `self_user_id`, or from the sole `superadmin` when unambiguous.
- Send to another chat: `./larkbot send --to <alias|oc_id> <text>`. Resolve the exact recipient; never guess a chat.
- Reply to a message: `./larkbot reply <message_id> --text <text>`.
- Read chats: `./larkbot inbox chats`, then `./larkbot inbox messages <chat_id> --limit <n> --format json`; use `inbox tail` for stable incremental consumption.
- “看工单”“我需要处理的工单”：read the local snapshot with `./larkbot tickets show --needs-me`. Refresh only when explicitly requested or when stale data would materially affect the answer and the user agrees.
- Prepare for a meeting: `./larkbot meeting context --when <time> --include-doc --include-messages`. This is read-only context; the calling agent owns interpretation and follow-up.
- Runtime health: `./larkbot status` for the concise state and `./larkbot doctor` for diagnosis. Runtime start/restart goes through `~/.ai/scripts/gtd runtime ...`, not an improvised process command.

## Safety And Failure Handling

- Actual `me`, `send`, and `reply` calls are external writes. Execute them only when the user explicitly asks to send; use `--dry-run --json` when validating syntax or target resolution. Run outbound larkbot commands with the project-required local escalation because lark-cli needs auth/keychain and network access.
- Editing and revoking require the exact `message_id`, confirmed content or target, and the existing `--yes` gate.
- Keep local snapshot reads separate from refreshes and network collection. Do not silently turn a read request into a refresh.
- If larkbot lacks the requested operation, report the exact capability gap. Never silently fall back to `lark-cli` or a `lark-*` skill.
- Prefer `--json` when another agent or script will consume the result. Preserve returned message IDs and receipts rather than inferring success from prose.
