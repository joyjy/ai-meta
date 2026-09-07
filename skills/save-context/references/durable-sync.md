# save-context: durable layer sync details

## Layer Classification

Review the full conversation and classify new information before writing:

| Layer | File | What to write | Standard |
|---|---|---|---|
| Global preferences | `~/.ai/instructions.md` | User habits, cross-project rules, tool environment | Applies across projects |
| Tool routes | `~/.ai/tool-routes.md` | Stable default entrypoints for tool-oriented task intents | Agent only needs to know which entrypoint to use |
| Agent frictions | `~/.ai/agent-frictions.md` | Reproducible tool/route obstacles and improvement candidates | Fix the default path instead of teaching a workaround |
| Project architecture | `<project>/AGENTS.md` | Mission, structure, symlinks, conventions, workflow rules | Project-specific but not task-specific |
| Project plan docs | `<project-root>/docs/plan/` | Agent-authored execution plans, migration plans, staged rollout plans not yet implemented | Not current architecture |
| Implemented durable docs | `<repo>/docs/architecture/index.md`, `<repo>/docs/decisions.md`, `index.md` | ADRs, implemented decisions, current architecture, backlog status | Needs traceability |
| Temporary state | `~/.ai/contexts/<abbr>.md` | Current Doing / Blocked / Next Steps | Next-session recovery only |

Ownership rule:

- First classify the repo as personal/self-managed or team/external.
- Personal/self-managed projects may record project-wide maintenance rules in
  `AGENTS.md`.
- Team/external projects may update `AGENTS.md` only for team-shared,
  repo-native facts suitable for every collaborator or agent.
- Never put local environment facts, private tool paths, personal preferences,
  or one user's AI-agent routing choices into a team/external `AGENTS.md`.
- If ownership is ambiguous, prefer context and ask one short question.

Durable-first rule:

- If information is already written to durable files, do not repeat it in
  context; reference the file only when the next session must open it.
- If a fact should be durable but no suitable layer exists, keep it temporarily
  in context as `pending durable home` and revisit on the next save.
- Context answers where work stopped, why it stopped, and what to do next.
- Preserve recovery anchors: cwd, repo/worktree path, branch, tools, temp
  worktrees, output paths, generated files, URLs, MR/issue links, and command or
  skill names needed to resume.
- Do not use context as an encyclopedia, changelog, architecture summary, or
  backup copy of durable rules.

## Agent Frictions And Tool Routes

During every `save-context`, scan for reproducible agent runtime friction:
default route failed, needed repeated retries, needed avoidable escalation,
produced unusable output, or required fallback due to tool description,
permissions, sandbox, API capability, client mismatch, missing helper scripts,
or unclear skill routing.

Treat owned objective friction events as evidence inputs to this same scan, not
as a second durable queue. Event counts, aborts, and repeated edits do not by
themselves satisfy the recording boundary below. Settle noise explicitly; when
an event is promoted, create or update the matching durable entry or preserve a
user-confirmed follow-up final-form in the same save.

Also scan for quiet fallback patterns the user did not explicitly name. If an
agent naturally tries or mentions a recommended/default tool that is unavailable
in the current client environment, then silently falls back to another route,
treat it as a friction candidate even when the fallback succeeded. Example:
`fd` is referenced as a preferred project-tree search tool but is unavailable,
so the agent repeatedly uses `rg --files` or approved `find` instead.

Record friction in `~/.ai/agent-frictions.md` only when it is likely to recur
and could be fixed by a script, skill, tool description, install step, approval
prefix, thin wrapper, or routing rule.

Before adding an Open entry, compare its normalized mechanism Signature with existing Open entries. A match never creates a second title or copies the full incident narrative. For a settled global friction, use `agent-frictions record-occurrence` so the receipt-derived `thread_id + project_cwd` identity is idempotently recorded and `复现` is computed as distinct occurrences minus one; use `--initialize` only immediately after creating a new entry. A legacy entry without Occurrence identities requires exact-evidence migration and must not infer `+0` from a missing counter.

Do not record ordinary coding pitfalls, project progress, active Doing /
Blocked / Next Steps, raw transcripts, or one-off failures with no plausible
system improvement. Similar frictions should update an existing entry instead
of creating near-duplicates.

When a stable helper, skill, plugin, script, or project-native command resolves
a recurring route, record the default in `~/.ai/tool-routes.md`. Keep tool
routes intent-oriented and short: intent, default entrypoint, minimal precheck,
and only necessary "do not default to" notes.

Suggested friction entry:

```markdown
### YYYY-MM-DD <short title>
- 场景：<what the agent naturally tried to do>
- 障碍：<why the default route failed or was costly>
- fallback：<what route/tool was used instead>
- 影响：<retry/token/user-interruption/quality impact>
- 改善方向：<script/skill/tool description/prefix_rule/wrapper/routing fix>
- 状态：open
```

Suggested route entry:

```markdown
### <task intent>

- 默认入口：`<command / skill / helper>`
- 适用：<when to use it>
- 预检：<optional dry-run/check>
- 不默认使用：`<fragile old route>`
```

## Project And Task Docs

Plan docs:

- Agent-authored plans that describe intended execution, migration, phased
  rollout, or candidate implementation but are not yet implemented belong under
  the project root `docs/plan/`.
- The project root is the directory that owns `index.md`; it may be separate
  from the source repo root.
- Do not put unimplemented plans into the source repo `docs/` as architecture,
  ADR, runbook, or design facts.
- After implementation and verification, promote only the surviving current
  facts, decisions, invariants, and change guidance into the source repo durable
  docs; do not copy the whole plan forward.

Intermediate doc lifecycle check:

- During `save-context`, scan the current changed paths and session artifacts for
  document placement risks. This is advisory, not a cleanup pass.
- Risk signals include `<repo>/docs/plan/*`, repo docs named or described as
  `plan`, `draft`, `proposal`, `migration plan`, `change list`, phased rollout,
  execution checklist, unfinished roadmap, or implementation notes.
- If a risk is found, record the risk in recovery state without choosing the
  cleanup timing for the user, for example:
  - `Doing`: `doc_lifecycle_risk: plan or draft content may be in repo docs; needs doc lifecycle decision before MR if this change is headed to review.`
  - Optional context note: `Candidate cleanup path: engineering-exit / doc-arch-review can decide which repo docs stay, move to project docs/plan, become ADR, or return to context/backlog when the user asks for that exit step.`
- Do not turn this advisory finding into a default `Next Steps` action to run
  `engineering-exit`, `doc-arch-review`, or another cleanup workflow. The user
  decides when to enter exit/review cleanup.
- Do not move, delete, archive, or rewrite documents as part of this advisory
  check unless the user explicitly asked for those edits in the same request.
- Do not decide final repo-doc admissibility in `save-context`; `doc-arch-review`
  is the authority for `<repo>/docs` architecture, and `engineering-exit` is the
  收尾 workflow that applies that judgment before MR.

`AGENTS.md`:

- Before editing, confirm the repo is personal/self-managed or the proposed
  content is team-shared and repo-native.
- If missing, create a small project entry:

```markdown
# <project-name>
<one-sentence mission>

## 目录结构 / 架构
## 约定
## 流程
```

- If present, update only for directory changes, symlink changes, workflow
  changes, or convention-level decisions.
- Merge instead of appending duplicates; delete stale content directly.

`index.md` Backlog:

- Use the discoverable `gtd` skill entrypoint and its backlog convention.
- Do not bypass `gtd` by directly mutating underlying tools or runtime state,
  and do not treat `~/.ai` as project content.

Decision records:

- Convention-level decisions go to `AGENTS.md`, not decisions docs.
- ADRs require an ADR-fit decision: long-lived, cross-boundary, reasonably
  disputable, externally constrained, or costly to migrate. Use
  `doc-arch-review` when fit is unclear.
- Architecture decisions that pass ADR fit go to `docs/architecture/index.md` or
  the relevant architecture shard as
  `ADR-00N` for ADR projects, or to `docs/decisions.md` when a project keeps
  decisions there.
- Decisions that do not pass ADR fit stay in the appropriate source of truth:
  workflow rules in skills or `AGENTS.md`, plans in `docs/plan/`, recovery
  state in context, and one-off small decisions in Daily Note when useful.
- If no appropriate decision layer exists and creating one is not safe or
  confirmed, preserve as `pending durable home` in context and ask later.
- Unclear decisions go under `待确认`; do not write automatically.

Global preferences:

- Read existing `~/.ai/instructions.md`.
- Add only cross-project preferences, rules, or tool environment facts.
- Do not write project-specific content there.
- Be conservative; prefer no change over noisy memory.

## Git Commit Preflight

Before writing the context snapshot, decide whether current durable changes
should be committed now.

Commit-likely signals:

- Added or modified files under `commands/`, `agents/`, or `skills/`.
- Appended an ADR to `docs/architecture/index.md` or the relevant architecture
  shard.
- Updated `AGENTS.md`, `index.md`, or files under `docs/`.
- The user said the result is accepted, done, okay, or similar.

Procedure:

1. Run `git status` and `git diff --stat`.
2. Apply the global local-commit boundary to complete, verified changes within
   the current session's authorized scope; inspect the staged diff and report
   hash/message. Preserve unrelated changes and unfinished work.
3. Saving context does not grant push or MR/PR permissions.
4. If commit is deferred, do not make committing the default Next Step.

Commit message format:

```text
<type>: <concise summary>

- <key change 1>
- <key change 2>
```

Types: `feat`, `refactor`, `docs`, `chore`.
