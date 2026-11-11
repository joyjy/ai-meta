"""Git evidence and revision-bound review documents; never deletes resources."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Callable


SCHEMA = "amt.branch-review.v1"


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def evidence(run: Callable, tip: str, default_tip: str) -> dict:
    """Compare content as well as history; failed Git probes never imply coverage."""
    def read(args):
        result = run(args)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout.strip()

    ancestor = run(["merge-base", "--is-ancestor", tip, default_tip])
    if ancestor.returncode not in (0, 1):
        raise RuntimeError(ancestor.stderr.strip())
    commits = read(["log", "--max-count=101", "--format=%H%x09%cs%x09%s", f"{default_tip}..{tip}"]).splitlines()
    result = {
        "tip": tip, "contained_in_default": ancestor.returncode == 0,
        "commits": [dict(zip(("sha", "date", "subject"), line.split("\t", 2))) for line in commits[:100]],
        "commits_truncated": len(commits) > 100,
    }
    if ancestor.returncode == 0:
        return result | {"coverage": "ancestor"}
    base = read(["merge-base", default_tip, tip])
    paths = read(["diff", "--name-only", "--no-renames", base, tip]).splitlines()
    result["changed_files"] = paths
    result["diff_stat"] = read(["diff", "--stat", base, tip])
    manifests = [p for p in paths if p.rsplit("/", 1)[-1] in {"build.gradle", "gradle.properties", "package.json", "pyproject.toml"}]
    if manifests:
        diff = read(["diff", "--unified=2", base, tip, "--", *manifests])
        result["manifest_diff"] = diff[:8000]
        result["manifest_diff_truncated"] = len(diff) > 8000
    # Compare every path touched by the branch, including deletions and renames.
    same = bool(paths)
    for start in range(0, len(paths), 100):
        probe = run(["diff", "--quiet", tip, default_tip, "--", *paths[start:start + 100]])
        if probe.returncode not in (0, 1):
            raise RuntimeError(probe.stderr.strip())
        same = same and probe.returncode == 0
    if not paths:
        same = read(["rev-parse", f"{tip}^{{tree}}"] ) == read(["rev-parse", f"{default_tip}^{{tree}}"])
    if same:
        return result | {"coverage": "changed_files_equal"}
    patches = read(["cherry", default_tip, tip]).splitlines()
    result["unmatched_patches"] = sum(line.startswith("+") for line in patches)
    result["equivalent_patches"] = sum(line.startswith("-") for line in patches)
    result["coverage"] = "patch_equivalent" if patches and not result["unmatched_patches"] else "unresolved"
    return result


def enrich_repository(report: dict, local: dict, remote_refs: dict, default: str, default_tip: str, run: Callable) -> None:
    """Add deterministic classifications to all entries, including closed/no-MR branches."""
    report.update(default_branch=default, default_sha=default_tip)
    cache = {}
    for item in report["branches"]:
        name = item["branch"]
        item.update(local_sha=local.get(name, ""), remote_sha=remote_refs.get(name, ""))
        item["entry_id"] = digest({k: report[k] for k in ("path", "host", "project")} | {
            k: item[k] for k in ("branch", "local_sha", "remote_sha")})[:20]
        if item.get("reason") in {"checked_out_in_worktree", "open_mr_exists", "protected_branch", "default_branch"}:
            item["classification"] = "retain"
            continue
        if not default or not default_tip or item.get("reason", "").endswith("failed"):
            item["classification"] = "insufficient_evidence"
            continue
        proofs = []
        try:
            for tip in dict.fromkeys(filter(None, (item["local_sha"], item["remote_sha"]))):
                if tip not in cache:
                    cache[tip] = evidence(run, tip, default_tip)
                proofs.append(cache[tip])
        except RuntimeError as error:
            item.update(classification="insufficient_evidence", evidence_error=str(error))
            report["failures"].append({"branch": name, "stage": "content_evidence", "error": str(error)})
            continue
        item["evidence"] = proofs
        if proofs and all(p["coverage"] == "ancestor" for p in proofs):
            item["classification"] = "redundant"
        elif proofs and all(p["coverage"] != "unresolved" for p in proofs):
            item["classification"] = "possibly_replaced"
        elif item.get("eligible"):
            # Existing MR checks prove source identity, not reachability in the default branch.
            squash = item.get("squash_commit_sha")
            covered = run(["merge-base", "--is-ancestor", squash, default_tip]) if squash else None
            item["classification"] = "redundant" if covered and covered.returncode == 0 else "unique_content"
        else:
            item["classification"] = "unique_content"
    # The public candidate list must agree with the revision-bound review.
    for item in report["branches"]:
        item["eligible"] = item["classification"] == "redundant"
        if item["eligible"]:
            item["action"] = "dry_run"
            item.pop("reason", None)
    report["candidates"] = [item for item in report["branches"] if item["eligible"]]
    report["skipped"] = [item for item in report["branches"] if not item["eligible"]]


def build_review(cleanup: dict, worktrees: dict, previous: dict | None) -> dict:
    entries = []
    for repo in cleanup.get("repositories", []):
        for item in repo["branches"]:
            if not item.get("entry_id"):
                continue
            entries.append({k: repo[k] for k in ("path", "host", "project", "default_branch", "default_sha")} | item)
    material = {"entries": entries, "worktrees": worktrees,
                "failures": [{"path": r["path"], "failures": r["failures"]} for r in cleanup.get("repositories", []) if r["failures"]]}
    # Exclude timestamps and action counters from the change notification key.
    fingerprint = digest(material)
    prior = (previous or {}).get("review", {})
    prior_entries = {x["entry_id"]: x for x in prior.get("entries", [])}
    changed = [e["entry_id"] for e in entries if prior_entries.get(e["entry_id"]) != e]
    removed = sorted(set(prior_entries) - {e["entry_id"] for e in entries})
    return {"schema": SCHEMA, "fingerprint": fingerprint, **material,
            "changed_entries": changed, "removed_entries": removed,
            "attention_required": fingerprint != prior.get("fingerprint"),
            "counts": dict(Counter(e["classification"] for e in entries))}


def render_review(review: dict) -> str:
    rows = ["# Git 分支清理候选", "", "本报告是待分析数据，不授予删除权限。entry_id 绑定仓库、分支和扫描时的本地／远端 SHA。", "",
            "| entry_id | 项目 / 分支 | 分类 | MR / 原因 |", "| --- | --- | --- | --- |"]
    for e in review["entries"]:
        text = lambda v: str(v).replace("|", "\\|").replace("\n", " ")
        rows.append(f"| `{e['entry_id']}` | {text(e['project'])} / `{text(e['branch'])}` | {e['classification']} | {text(e.get('reason', e.get('mr_iid', '')))} |")
    for e in review["entries"]:
        if e["classification"] in {"retain", "redundant"}:
            continue
        rows.extend(["", f"## {e['project']} / {e['branch']}", ""])
        for proof in e.get("evidence", []):
            rows.append(f"提交 `{proof['tip']}`；内容比较：`{proof['coverage']}`。")
            rows.extend(f"- `{c['sha'][:10]}` {c['date']} {c['subject']}" for c in proof["commits"])
            if proof.get("commits_truncated"):
                rows.append("- 提交超过 100 个，明细已截断。")
            rows.extend(["", "```text", proof.get("diff_stat", ""), "```"])
            if proof.get("manifest_diff"):
                rows.extend(["", "```diff", proof["manifest_diff"], "```"])
                if proof["manifest_diff_truncated"]:
                    rows.append("依赖清单 diff 已截断。")
    rows.extend(["", "## Worktree", "", "仅盘点，删除仍使用 wt-sweep 的生命周期规则。", ""])
    for item in review["worktrees"].get("items", []):
        rows.append(f"- `{item['path']}`：{item['verdict']}；{'；'.join(item.get('reasons', []))}")
    if review["worktrees"].get("error"):
        rows.append(f"worktree 盘点失败：{review['worktrees']['error']}")
    if review["worktrees"].get("skipped_outside_roots"):
        rows.append(f"扫描根目录外的 worktree 未纳入：{review['worktrees']['skipped_outside_roots']} 个。")
    return "\n".join(rows) + "\n"
