# load-context health check

Read this reference only after the main skill resolves the route and triggers the advisory health branch. It owns health diagnosis; the main skill owns ordinary recovery and output.

## Root Resolution

- The project root is the directory containing the resolved `index.md`; do not assume it is the process cwd.
- Project-root entry checks cover only `index.md`. Repo/source-root checks cover `README.md`, `AGENTS.md`, `CLAUDE.md`, and accidental `AGENT.md`.
- Use local source roots from `index.md` Links / Source when present; otherwise use the project root. For multiple roots, scan each and report only the highest-signal 1-3 findings overall.
- Resolve the current canonical `repos[]` entry with `~/.ai/scripts/gitlab-project-lint --cwd <source-root> --index <project-root>/index.md --resolve-only --json`. Matching order is exact path, shared Git common dir, then unique normalized Git remote. Keep file scans on the actual source root, and never lint sibling repos merely because they share the project.
- A matching context `cwd` / repo / worktree may confirm the source root. Do not expand unrelated referenced files to discover it.
- Never scan a broad parent merely because it is cwd. If no safe root resolves, skip line counts and report a partial health check.

## Objective Friction

Reuse the main skill's count-only friction result. Only if it is unavailable, run `~/.ai/scripts/agent-frictions status --owner context:<abbr>:<selected-route>`. Never load event facts or message content. When `actionable_count > 0`, include `摩擦候选：N 条待下次 save-context 结算`; zero stays silent. Do not claim, interpret, or settle events during load.

## Entry And Size Probes

- Use metadata or short reads only: `test -e`, `ls -l`, `wc -l`, `wc -c`, `head`, and symlink inspection.
- Run `~/.ai/scripts/project-line-counts <source-root>` and `~/.ai/scripts/project-line-counts <source-root> --markdown`. If unavailable, use `git ls-files`; outside Git, use a pruned file listing that excludes `.git`, `node_modules`, `vendor`, `tmp`, `dist`, `build`, `.venv`, `__pycache__`, `.next`, `coverage`, and `.cache`.
- Count regular files only. The scan may count lines but must not inspect contents beyond counts and filenames.
- Report context bloat above about 200KB or 1500 lines and suggest `save-context`.
- Report entry-doc bloat above about 30KB or 600 lines and suggest moving durable detail to docs, ADR, or skills.
- Report source/config/script files above about 1200 lines as maintainability risks and above 3000 as high risk. Report Markdown above about 600 lines as bloat and above 1500 as high risk. Show only the top 1-3 findings unless asked.
- Exclude generated patch, diff, bundle, lock, snapshot, and vendored artifacts from source-size risk. When a generated artifact maps to an editable overlay, template, generator, or source module, count and report that source instead; if ownership is unclear, report the missing source mapping rather than the generated line count. A full-file overlay of an upstream module is evaluated by both its local source size and its diff against the declared upstream baseline, so a large upstream-owned base is not mislabeled as entirely local maintenance surface.
- Report missing project `index.md`, missing source-root `AGENTS.md`, missing source-root `CLAUDE.md` when `AGENTS.md` exists, and likely typo `AGENT.md`. Missing private/internal `README.md` is a human-facing entry gap, not a work blocker.
- When both agent entries exist, use symlink metadata or a short header read to verify `CLAUDE.md` delegates to `@AGENTS.md`; stay silent when correct.

## GitLab Health

- `l1`: strict MR baseline. Run lint when no recorded result exists; `PASS` is silent, `WARN` / `CHANGE` are reported.
- `l2`: transitional baseline. Run lint when no recorded result exists; `PASS` is silent, `CHANGE` is reported, and `WARN` is reported only when its date is missing or older than 14 days.
- `l3`: do not run or report GitLab settings lint.
- GitLab lint is recorded per current repo entry as `gitlab.lint: <PASS|WARN|CHANGE|SKIP>@YYYY-MM-DD`; it is not a per-load whole-project probe.
- For `l1` / `l2`, missing `gitlab.squash` defaults to `default-on`. Pass that value as a read-only lint override; do not write it or ask merely so diagnosis can run.
- For `l1` / `l2` with squash but no recorded lint, run `~/.ai/scripts/gitlab-project-lint --cwd <source-root> --index <project-root>/index.md` without `--write-index`. Keep loading if network, auth, or tooling prevents a result, and report the missing record.
- Every managed current repo entry should declare `repos[].gitlab.flow: l1|l2|l3`. Never infer it from project metadata, docs, remotes, namespace, or examples. A missing-flow tip must name the exact `index.md`, canonical repo path when known, and allowed values.
- Only a user reply containing an allowed `gitlab.flow`, an explicitly requested `gitlab.squash` value, or an explicit remediation request authorizes `--write-index` for the selected repo entry. Do not touch siblings or choose a value for the user.
- Mention a failed non-critical health command only when it changes the user's next action.

## Temporary Files

- Normal load never deletes temp files.
- Mention stale `/private/tmp` or `/tmp` paths found in context as candidates.
- Clean only when explicitly requested, limited to exact paths or a clear project/workstream prefix; never use broad globs or touch system/app entries, sockets, or permission-restricted paths.
- Before deletion, list exact paths and ask unless the user already named those exact paths.
