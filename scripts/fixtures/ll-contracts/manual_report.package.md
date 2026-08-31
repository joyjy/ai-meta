# Manual Report Package

- contract: engineering-exit
- mode: full
- outcome: 收束当前 diff，并在 gates 通过后按 gitlab.flow 完成 commit / push / open MR
- verification:
  - `git diff --check`
  - `git status --short`
- exit: done
- privileged_git_exit: true
- call_user_when: scope_change, destructive_action, acceptance_gap, risk_acceptance, business_judgment
- next_action: open_mr
