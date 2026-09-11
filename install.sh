#!/usr/bin/env bash
# install.sh — 发布 ai-meta 软链、Codex skills 和本机客户端适配配置
# 幂等：已存在的软链和 ai-meta 受管配置块会原位更新，不影响其他项目的条目
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
AI="$HOME/.ai"
AGENTS_SKILLS="$HOME/.agents/skills"

symlink() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  ln -sfn "$src" "$dst"
  echo "  linked: $dst -> $src"
}

cleanup_ai_only_command_skill() {
  local name="$1"
  local dst="$AI/skills/$name"
  if [ -L "$dst" ]; then
    rm -f "$dst"
    echo "  removed stale skill: $dst"
  elif [ -e "$dst" ]; then
    echo "  [WARN] not removing non-symlink skill: $dst"
  fi
}

cleanup_skill_symlink() {
  local root="$1" name="$2"
  local dst="$root/$name"
  if [ -L "$dst" ]; then
    rm -f "$dst"
    echo "  removed stale skill: $dst"
  elif [ -e "$dst" ]; then
    echo "  [WARN] not removing non-symlink skill: $dst"
  fi
}

cleanup_ai_script_symlink() {
  local name="$1"
  local dst="$AI/scripts/$name"
  if [ -L "$dst" ]; then
    rm -f "$dst"
    echo "  removed stale script: $dst"
  elif [ -e "$dst" ]; then
    echo "  [WARN] not removing non-symlink script: $dst"
  fi
}

cleanup_ai_command_symlink() {
  local name="$1"
  local dst="$AI/commands/$name"
  if [ -L "$dst" ]; then
    rm -f "$dst"
    echo "  removed stale command: $dst"
  elif [ -e "$dst" ]; then
    echo "  [WARN] not removing non-symlink command: $dst"
  fi
}

publish_project_skill() {
  local name="$1" src="$2"
  if [ ! -f "$src/SKILL.md" ]; then
    cleanup_skill_symlink "$AI/skills" "$name"
    cleanup_skill_symlink "$AGENTS_SKILLS" "$name"
    echo "  [WARN] project skill unavailable: $name ($src)"
    return
  fi
  if [ ! -f "$src/agents/openai.yaml" ]; then
    echo "  [ERROR] project skill lacks Codex metadata: $src/agents/openai.yaml" >&2
    return 1
  fi
  symlink "$src" "$AI/skills/$name"
  symlink "$src" "$AGENTS_SKILLS/$name"
}

echo "==> ai-meta install (repo: $REPO)"
mkdir -p "$AI/agents/opencode" "$AI/agents/claude"

echo ""
echo "[preflight] Codex command entries"
"$REPO/scripts/check-codex-command-entries"

echo ""
echo "[preflight] cross-client skill invocation policies"
"$REPO/scripts/check-skill-invocation-policies"

# ── core files ────────────────────────────────────────────────────────────────
echo ""
echo "[core] instructions.md -> ~/.ai/"
symlink "$REPO/instructions.md" "$AI/instructions.md"
symlink "$REPO/tool-routes.md" "$AI/tool-routes.md"
symlink "$REPO/route-context.json" "$AI/route-context.json"
if [ ! -e "$AI/agent-frictions.md" ]; then
  touch "$AI/agent-frictions.md"
  echo "  created local runtime: $AI/agent-frictions.md"
fi

# ── commands ──────────────────────────────────────────────────────────────────
echo ""
echo "[commands] commands/ -> ~/.ai/commands/"
for f in "$REPO/commands"/*.md; do
  symlink "$f" "$AI/commands/$(basename "$f")"
done
for name in rr.md; do
  cleanup_ai_command_symlink "$name"
done

# ── skills ────────────────────────────────────────────────────────────────────
echo ""
echo "[skills] skills/ -> ~/.ai/skills/"
cleanup_ai_only_command_skill "load-context"
cleanup_ai_only_command_skill "save-context"
cleanup_skill_symlink "$AI/skills" "agent-status"
cleanup_skill_symlink "$AI/skills" "architecture-review"
cleanup_skill_symlink "$AI/skills" "document-slimming"
cleanup_skill_symlink "$AI/skills" "ll"
cleanup_skill_symlink "$AI/skills" "lark-ticket-insights"
cleanup_skill_symlink "$AI/skills" "rr"
for d in "$REPO/skills"/*/; do
  if [ -L "${d%/}" ]; then
    continue
  fi
  if [ ! -f "$d/SKILL.md" ]; then
    continue
  fi
  if [ "$(basename "$d")" = "load-context" ] || [ "$(basename "$d")" = "save-context" ]; then
    continue
  fi
  symlink "$d" "$AI/skills/$(basename "$d")"
done

echo ""
echo "[codex skills] skills/ -> ~/.agents/skills/"
cleanup_skill_symlink "$AGENTS_SKILLS" "agent-status"
cleanup_skill_symlink "$AGENTS_SKILLS" "architecture-review"
cleanup_skill_symlink "$AGENTS_SKILLS" "document-slimming"
cleanup_skill_symlink "$AGENTS_SKILLS" "ll"
cleanup_skill_symlink "$AGENTS_SKILLS" "lark-ticket-insights"
cleanup_skill_symlink "$AGENTS_SKILLS" "rr"
for d in "$REPO/skills"/*/; do
  if [ -L "${d%/}" ]; then
    continue
  fi
  if [ ! -f "$d/SKILL.md" ]; then
    continue
  fi
  symlink "$d" "$AGENTS_SKILLS/$(basename "$d")"
done

echo ""
echo "[project skills] owner repos -> shared discovery"
larkbot_project_root="${AI_META_LARKBOT_PROJECT_ROOT:-$HOME/Documents/me/Projects/larkbot}"
publish_project_skill "larkbot" "$larkbot_project_root/skills/larkbot"

for name in \
  bmad-brainstorming \
  bmad-help \
  bmad-create-prd \
  bmad-create-architecture \
  bmad-create-epics-and-stories \
  bmad-check-implementation-readiness \
  bmad-sprint-planning \
  bmad-create-story \
  bmad-dev-story \
  bmad-code-review \
  bmad-quick-dev; do
  cleanup_skill_symlink "$AI/skills" "$name"
done

# ── tool-layer dirs (整目录软链，首次安装时建立) ──────────────────────────────
echo ""
echo "[tool-layer] ~/.config/opencode & ~/.claude -> ~/.ai/"

declare -A TOOL_DIRS=(
  ["$HOME/.config/opencode/commands"]="$AI/commands"
  ["$HOME/.config/opencode/agents"]="$AI/agents/opencode"
  ["$HOME/.config/opencode/skills"]="$AI/skills"
  ["$HOME/.config/opencode/AGENTS.md"]="$AI/instructions.md"
  ["$HOME/.claude/commands"]="$AI/commands"
  ["$HOME/.claude/agents"]="$AI/agents/claude"
  ["$HOME/.claude/skills"]="$AI/skills"
  ["$HOME/.claude/CLAUDE.md"]="$AI/instructions.md"
  ["$HOME/.codex/AGENTS.md"]="$AI/instructions.md"
)

for dst in "${!TOOL_DIRS[@]}"; do
  src="${TOOL_DIRS[$dst]}"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    echo "  ok (exists): $dst"
  else
    symlink "$src" "$dst"
  fi
done

# ── scripts ───────────────────────────────────────────────────────────────────
echo ""
echo "[scripts] selected helpers -> ~/.ai/scripts/"
symlink "$REPO/scripts/claude-bypass.sh" "$AI/claude-bypass.sh"
symlink "$REPO/scripts/clean-codex-logs.sh" "$AI/scripts/clean-codex-logs.sh"
symlink "$REPO/scripts/gitlab-mr" "$AI/scripts/gitlab-mr"
symlink "$REPO/scripts/gitlab-ci" "$AI/scripts/gitlab-ci"
symlink "$REPO/scripts/gitlab-project-lint" "$AI/scripts/gitlab-project-lint"
symlink "$REPO/scripts/gitlab-inline-comment" "$AI/scripts/gitlab-inline-comment"
symlink "$REPO/scripts/mr-comments.sh" "$AI/scripts/mr-comments.sh"
symlink "$REPO/scripts/project-line-counts" "$AI/scripts/project-line-counts"
symlink "$REPO/scripts/context-ff-merge" "$AI/scripts/context-ff-merge"
symlink "$REPO/scripts/context_ff_merge.py" "$AI/scripts/context_ff_merge.py"
symlink "$REPO/scripts/save-context" "$AI/scripts/save-context"
symlink "$REPO/scripts/save_context_orchestrator.py" "$AI/scripts/save_context_orchestrator.py"
symlink "$REPO/scripts/save_context.py" "$AI/scripts/save_context.py"
symlink "$REPO/scripts/save-context-audit-rs" "$AI/scripts/save-context-audit-rs"
symlink "$REPO/scripts/save_context_audit_rs.py" "$AI/scripts/save_context_audit_rs.py"
symlink "$REPO/scripts/save_context_audit_archive.py" "$AI/scripts/save_context_audit_archive.py"
symlink "$REPO/scripts/save_context_audit_io.py" "$AI/scripts/save_context_audit_io.py"
symlink "$REPO/scripts/save-context-recover" "$AI/scripts/save-context-recover"
symlink "$REPO/scripts/save_context_recover.py" "$AI/scripts/save_context_recover.py"
symlink "$REPO/scripts/save-context-timeline" "$AI/scripts/save-context-timeline"
symlink "$REPO/scripts/save_context_timeline.py" "$AI/scripts/save_context_timeline.py"
symlink "$REPO/scripts/codex_session_titles.py" "$AI/scripts/codex_session_titles.py"
symlink "$REPO/scripts/verify-ll-contract" "$AI/scripts/verify-ll-contract"
symlink "$REPO/scripts/ll-goal-objective" "$AI/scripts/ll-goal-objective"
symlink "$REPO/scripts/ll-brief" "$AI/scripts/ll-brief"
symlink "$REPO/scripts/ll-ledger" "$AI/scripts/ll-ledger"
symlink "$REPO/scripts/ll-hot-block" "$AI/scripts/ll-hot-block"
symlink "$REPO/scripts/ll-turn" "$AI/scripts/ll-turn"
symlink "$REPO/scripts/ll-compile" "$AI/scripts/ll-compile"
symlink "$REPO/scripts/ll-workitem" "$AI/scripts/ll-workitem"
symlink "$REPO/scripts/ll_contract_file.py" "$AI/scripts/ll_contract_file.py"
symlink "$REPO/scripts/ll_compiler.py" "$AI/scripts/ll_compiler.py"
symlink "$REPO/scripts/agent-frictions" "$AI/scripts/agent-frictions"
symlink "$REPO/scripts/agent_frictions.py" "$AI/scripts/agent_frictions.py"
symlink "$REPO/scripts/skill-verification" "$AI/scripts/skill-verification"
symlink "$REPO/scripts/skill_verification.py" "$AI/scripts/skill_verification.py"
symlink "$REPO/scripts/amt-git-refresh" "$AI/scripts/amt-git-refresh"
symlink "$REPO/scripts/sync-mcp-config" "$AI/scripts/sync-mcp-config"
symlink "$REPO/scripts/sync_mcp_config.py" "$AI/scripts/sync_mcp_config.py"
symlink "$REPO/scripts/validate-skill" "$AI/scripts/validate-skill"
symlink "$REPO/sync-conventions.sh" "$AI/scripts/sync-conventions.sh"
symlink "$REPO/skills/coding-conventions/node-test-kit/bin/node-test-kit.mjs" "$AI/scripts/node-test-kit"
cleanup_ai_script_symlink "ll-state"
cleanup_ai_script_symlink "rr-state"
cleanup_ai_script_symlink "verify-rr-contract"
cleanup_ai_script_symlink "install-sync-conventions.sh"
cleanup_ai_script_symlink "agent_status.py"
cleanup_ai_script_symlink "agent_status_check.sh"
cleanup_ai_script_symlink "restart_agent_status.sh"

cleanup_ai_script_symlink "resolve_config.py"
cleanup_ai_script_symlink "resolve_customization.py"

# ── runtime registrations ─────────────────────────────────────────────────────
echo ""
echo "[runtime] ai-meta periodic jobs -> ~/.ai/gtd/runtime/services/"
if [ "${AI_META_INSTALL_PERSONAL_RUNTIME:-0}" = "1" ]; then
  "$REPO/scripts/install-amt-runtime.sh"
else
  echo "  skipped: set AI_META_INSTALL_PERSONAL_RUNTIME=1 to install personal runtime registrations"
fi

echo ""
echo "==> done"
