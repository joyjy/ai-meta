#!/usr/bin/env python3
"""List Docker test artifacts with cleanup verdicts and remove verified ones; pulled images are never auto-removed."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_usage  # noqa: E402

CLI = "docker-test-sweep"
COMMANDS = ["list", "prune", "remove", "usage"]
SCHEMA = "docker-test-sweep.list.v1"
PRUNE_SCHEMA = "docker-test-sweep.prune.v1"
DEFAULT_DAYS = 7
DEFAULT_ROOTS = ["~/Documents/projects", "~/Documents/reference", "~/Documents/me/Projects"]
STOPPED = {"exited", "created", "dead"}
PROJECT_LABEL = "com.docker.compose.project"
ANONYMOUS_LABEL = "com.docker.volume.anonymous"
VERDICT_ORDER = ["removable", "ask", "keep"]
VERDICT_TITLE = {"removable": "可删除", "ask": "需要你确认", "keep": "保留"}
KIND_ORDER = ["container", "image", "volume"]
KIND_TITLE = {"container": "容器", "image": "镜像", "volume": "volume"}
ROUTE_DOC = "~/.ai/tool-routes.md「Docker 测试产物清理」"


class SweepError(Exception):
    """Stable CLI error carrying a category for the caller."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run the docker CLI; failures keep the daemon's own reason."""

    try:
        proc = subprocess.run(["docker", *args], capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SweepError("docker-missing", "docker CLI not found on PATH") from exc
    if check and proc.returncode != 0:
        err = proc.stderr.strip()
        category = ("permission" if "permission denied" in err.lower()
                    else "daemon-unreachable" if "cannot connect" in err.lower() else "docker")
        raise SweepError(category, f"docker {' '.join(args[:2])} failed: {err}")
    return proc


def inspect_all(kind: str, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    out = docker(kind, "inspect", "--format", "{{json .}}", *ids).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def ids(*args: str) -> list[str]:
    return list(dict.fromkeys(line for line in docker(*args).stdout.split() if line))


def parse_time(value: str | None) -> datetime | None:
    """Docker RFC3339Nano to an aware datetime; the zero time counts as absent."""

    if not value or value.startswith("0001-"):
        return None
    match = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)?$", value)
    if not match:
        return None
    zone = match.group(3) or "Z"
    return datetime.fromisoformat(match.group(1) + (match.group(2) or "")[:7]
                                  + ("+00:00" if zone == "Z" else zone))


def latest(*values: str | None) -> datetime | None:
    times = [t for t in map(parse_time, values) if t]
    return max(times) if times else None


def normalize(name: str) -> str:
    """Compose's default project name for a directory basename."""

    return re.sub(r"[^a-z0-9_-]", "", name.lower())


def declared_name(working_dir: str, config_files: str) -> str | None:
    """Project name declared in the compose files or .env, which marks a maintained environment."""

    for path in filter(None, config_files.split(",")):
        try:
            text = Path(path).read_text()
        except OSError:
            continue
        if path.endswith(".json"):
            try:
                name = json.loads(text).get("name")
            except (ValueError, AttributeError):
                name = None
        else:
            match = re.search(r"^name:\s*['\"]?([^'\"\s#]+)", text, re.M)
            name = match.group(1) if match else None
        if name:
            return name
    try:
        env = (Path(working_dir) / ".env").read_text()
    except OSError:
        return None
    match = re.search(r"^COMPOSE_PROJECT_NAME=['\"]?([^'\"\s#]+)", env, re.M)
    return match.group(1) if match else None


def project_verdict(project: str, labels: dict[str, str]) -> tuple[str, str]:
    """keep or ephemeral for a compose project seen on a container, judged by its working dir."""

    wd = labels.get("com.docker.compose.project.working_dir", "").rstrip("/")
    if not wd or not os.path.isdir(wd):
        return "ephemeral", f"工作目录已不存在：{wd or '未知'}"
    if normalize(os.path.basename(wd)) == project:
        return "keep", "仓库默认开发环境（项目名等于目录名）"
    if declared_name(wd, labels.get("com.docker.compose.project.config_files", "")) == project:
        return "keep", "compose 配置声明了项目名"
    return "ephemeral", f"用 -p 指定的一次性项目（目录 {wd}）"


def project_dirs(roots: list[str]) -> set[str]:
    names: set[str] = set()
    for root in roots:
        try:
            names.update(normalize(p.name) for p in Path(root).iterdir() if p.is_dir())
        except OSError:
            continue
    return names


def by_age(verdict: str, reason: str, last: datetime | None, cutoff: datetime, days: int) -> tuple[str, str]:
    """An ephemeral artifact becomes removable only after the retention window."""

    if verdict != "ephemeral":
        return verdict, reason
    if last and last > cutoff:
        return "keep", f"{days} 天内创建或使用过"
    return "removable", reason


def item(kind: str, ident: str, name: str, verdict: str, reason: str, last: datetime | None,
         project: str | None = None, size: int | None = None, refs: list[str] | None = None) -> dict[str, Any]:
    return {"kind": kind, "id": ident, "name": name, "project": project, "verdict": verdict, "reason": reason,
            "last_used": last.isoformat() if last else None, "size": size, "refs": refs or [name]}


def plan(days: int, roots: list[str]) -> dict[str, Any]:
    """Inspect containers, images and volumes once and give each a verdict."""

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    containers = inspect_all("container", ids("ps", "-aq", "--no-trunc"))
    images = inspect_all("image", ids("image", "ls", "-q", "--no-trunc"))
    volumes = inspect_all("volume", ids("volume", "ls", "-q"))
    dirs = project_dirs(roots)
    projects: dict[str, tuple[str, str]] = {}
    for c in containers:
        labels = c["Config"].get("Labels") or {}
        if labels.get(PROJECT_LABEL):
            projects.setdefault(labels[PROJECT_LABEL], project_verdict(labels[PROJECT_LABEL], labels))

    def orphan(project: str, absent: str) -> tuple[str, str]:
        if project in projects:
            return projects[project]
        if project in dirs:
            return "keep", "存在同名项目目录"
        return absent, "没有容器，也没有同名项目目录"

    items: list[dict[str, Any]] = []
    for c in containers:
        labels = c["Config"].get("Labels") or {}
        project, state = labels.get(PROJECT_LABEL), c["State"]["Status"]
        last = latest(c["State"].get("FinishedAt"), c.get("Created"))
        if state not in STOPPED:
            verdict, reason = "keep", f"状态 {state}"
        elif not project:
            verdict, reason = "ask", "docker run 直接创建的容器，不自动删除"
        else:
            verdict, reason = by_age(*projects[project], last, cutoff, days)
        items.append(item("container", c["Id"], c["Name"].lstrip("/"), verdict, reason, last, project))
    gone = {i["id"] for i in items if i["verdict"] == "removable"}
    live = [c for c in containers if c["Id"] not in gone]
    used_images = {c["Image"] for c in live}
    used_volumes = {m.get("Name") for c in live for m in c.get("Mounts") or [] if m.get("Type") == "volume"}

    for img in images:
        tags = [t for t in img.get("RepoTags") or [] if t != "<none>:<none>"]
        project = ((img.get("Config") or {}).get("Labels") or {}).get(PROJECT_LABEL)
        last = latest(img.get("Created"), (img.get("Metadata") or {}).get("LastTagTime"))
        if img["Id"] in used_images:
            verdict, reason = "keep", "有容器在用"
        elif img.get("RepoDigests"):
            verdict, reason = (("keep", "从镜像仓库拉取的基础设施镜像") if tags
                               else ("ask", "已被新版本取代的拉取镜像（没有 tag）"))
        elif not tags:
            verdict, reason = by_age("ephemeral", "本地构建的悬空镜像", last, cutoff, days)
        elif project:
            verdict, reason = by_age(*orphan(project, "ephemeral"), last, cutoff, days)
            # A name without the project prefix came from an explicit `image:` and may be reused elsewhere.
            if verdict == "removable" and not any(t.rsplit("/", 1)[-1].startswith(project) for t in tags):
                verdict, reason = "ask", "compose 用 image: 显式命名，可能被其他项目复用"
        else:
            verdict, reason = "ask", "手动打 tag 的本地镜像"
        name = tags[0] if tags else img["Id"].removeprefix("sha256:")[:12]
        items.append(item("image", img["Id"], name, verdict, reason, last, project, img.get("Size"),
                          tags or [img["Id"]]))

    for v in volumes:
        labels = v.get("Labels") or {}
        name, project = v["Name"], labels.get(PROJECT_LABEL)
        last = parse_time(v.get("CreatedAt"))
        if name in used_volumes:
            verdict, reason = "keep", "有容器挂载"
        elif ANONYMOUS_LABEL in labels or (not labels and re.fullmatch(r"[0-9a-f]{64}", name)):
            verdict, reason = by_age("ephemeral", "没有容器挂载的匿名 volume", last, cutoff, days)
        elif project:
            verdict, reason = orphan(project, "ask")
            if verdict == "ask":
                reason = "compose volume，找不到所属项目，可能存有数据"
            verdict, reason = by_age(verdict, reason, last, cutoff, days)
        else:
            verdict, reason = "keep", "命名 volume，可能是长期服务数据"
        items.append(item("volume", name, name, verdict, reason, last, project))

    return {"schema": SCHEMA, "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "days": days, "roots": roots, "items": items, "build_cache": build_cache(days)}


def build_cache(days: int) -> dict[str, Any]:
    rows = [json.loads(line) for line in docker("system", "df", "--format", "{{json .}}").stdout.splitlines()
            if line.strip()]
    row = next((r for r in rows if r.get("Type") == "Build Cache"), {})
    return {"filter": f"until={days * 24}h", "size": row.get("Size"), "reclaimable": row.get("Reclaimable")}


def human(size: int | None) -> str:
    value = float(size or 0)
    for unit in ("B", "KB", "MB"):
        if value < 1000:
            return f"{value:.0f}{unit}"
        value /= 1000
    return f"{value:.1f}GB"


def render(result: dict[str, Any]) -> str:
    """Human view: removable and ask items are spelled out, kept ones are counted by reason."""

    items = result["items"]
    counts = Counter(i["kind"] for i in items)
    cache = result["build_cache"]
    out = [f"docker-test-sweep list · {result['generated_at']} · 保留期 {result['days']} 天 · "
           + " / ".join(f"{KIND_TITLE[k]} {counts[k]}" for k in KIND_ORDER),
           f"构建缓存：共 {cache['size']}，可回收 {cache['reclaimable']}；超过 {result['days']} 天未使用的部分会被清理"]
    for verdict in VERDICT_ORDER:
        group = [i for i in items if i["verdict"] == verdict]
        if not group:
            continue
        out.append(f"\n## {VERDICT_TITLE[verdict]}（{verdict}，{len(group)}）")
        for kind in KIND_ORDER:
            rows = [i for i in group if i["kind"] == kind]
            if not rows:
                continue
            size = sum(i["size"] or 0 for i in rows)
            out.append(f"### {KIND_TITLE[kind]}（{len(rows)}" + (f"，合计 {human(size)}，未扣除共享层" if size else "")
                       + "）")
            if verdict == "keep":
                out.extend(f"- {reason}：{n}" for reason, n in Counter(i["reason"] for i in rows).most_common())
                continue
            for i in rows:
                last = f" · 最近 {i['last_used'][:10]}" if i["last_used"] else ""
                size_text = f" · {human(i['size'])}" if i["size"] else ""
                out.append(f"- {i['name']} · {i['reason']}{last}{size_text}")
    ask = [i["name"] for i in items if i["verdict"] == "ask"]
    if ask:
        out.append("\n确认后的删除命令：\n  docker-test-sweep remove \\\n" + " \\\n".join(f"    {n}" for n in ask))
    return "\n".join(out)


def delete(target: dict[str, Any]) -> tuple[bool, str]:
    """Remove one planned item; docker itself still refuses anything in use."""

    try:
        if target["kind"] == "container":
            docker("rm", target["id"])
        elif target["kind"] == "image":
            for ref in target["refs"]:
                docker("rmi", ref)
        else:
            docker("volume", "rm", target["id"])
    except SweepError as exc:
        return False, str(exc)
    return True, ""


def execute(targets: list[dict[str, Any]], dry_run: bool) -> list[dict[str, Any]]:
    results = []
    for target in sorted(targets, key=lambda i: KIND_ORDER.index(i["kind"])):
        label = f"{KIND_TITLE[target['kind']]} {target['name']}"
        if dry_run:
            print(f"WOULD REMOVE {label}")
            continue
        ok, error = delete(target)
        print(f"REMOVED {label}" if ok else f"FAILED {label}: {error}")
        results.append({"kind": target["kind"], "name": target["name"], "ok": ok, "error": error or None})
    return results


def system_df() -> list[dict[str, Any]]:
    return [json.loads(line) for line in docker("system", "df", "--format", "{{json .}}").stdout.splitlines()
            if line.strip()]


def prune(days: int, roots: list[str], dry_run: bool, output: str | None) -> int:
    """Recompute the plan, then remove removable items and build cache older than the window."""

    before = system_df()
    result = plan(days, roots)
    results = execute([i for i in result["items"] if i["verdict"] == "removable"], dry_run)
    cache_filter = result["build_cache"]["filter"]
    if dry_run:
        print(f"WOULD PRUNE 构建缓存 --filter {cache_filter}")
    else:
        try:
            docker("builder", "prune", "-f", "--filter", cache_filter)
            print(f"PRUNED 构建缓存 --filter {cache_filter}")
            results.append({"kind": "build-cache", "name": cache_filter, "ok": True, "error": None})
        except SweepError as exc:
            print(f"FAILED 构建缓存: {exc}")
            results.append({"kind": "build-cache", "name": cache_filter, "ok": False, "error": str(exc)})
    failed = sum(1 for r in results if not r["ok"])
    if output and not dry_run:
        report = {"schema": PRUNE_SCHEMA, "generated_at": result["generated_at"], "days": days,
                  "plan": result, "results": results, "system_df_before": before, "system_df_after": system_df()}
        path = Path(output).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"完成：删除 {len(results) - failed} 项，失败 {failed} 项" if not dry_run else "dry-run：未删除任何内容")
    return 1 if failed else 0


def remove(targets: list[str], days: int, roots: list[str], dry_run: bool) -> int:
    """Re-plan and remove exact containers, images or volumes whose verdict is ask or removable."""

    items = plan(days, roots)["items"]
    chosen, failed = [], 0
    for target in targets:
        by_id = len(target) >= 12 and re.fullmatch(r"[0-9a-f]+", target)
        matches = [i for i in items if target in (i["name"], i["id"], *i["refs"])
                   or (by_id and i["id"].removeprefix("sha256:").startswith(target))]
        if not matches:
            print(f"REFUSED {target}: 找不到对应的容器、镜像或 volume")
            failed += 1
        for match in matches:
            if match["verdict"] == "keep":
                print(f"REFUSED {target}: {match['reason']}")
                failed += 1
            else:
                chosen.append(match)
    results = execute(chosen, dry_run)
    failed += sum(1 for r in results if not r["ok"])
    return 1 if failed else 0


def retention_days(value: str) -> int:
    """Below 1 day every test artifact and the whole build cache would fall outside the window."""

    days = int(value)
    if days < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return days


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=CLI,
        description=("List Docker test artifacts (containers, locally built images, volumes) with cleanup "
                     "verdicts; prune removes only removable ones plus old build cache. Pulled images, "
                     f"running containers and named service volumes are never auto-removed. Rules: {ROUTE_DOC}. "
                     "`usage` prints local call statistics."))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "prune", "remove"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--days", type=retention_days, default=DEFAULT_DAYS,
                         help=f"retention window in days (default {DEFAULT_DAYS})")
        cmd.add_argument("--root", action="append",
                         help="project root for directory-name checks (default ~/Documents/projects, "
                              "~/Documents/reference, ~/Documents/me/Projects)")
    sub.choices["list"].add_argument("--json", action="store_true")
    sub.choices["prune"].add_argument("--dry-run", action="store_true")
    sub.choices["prune"].add_argument("--output", help="write plan, results and docker system df as JSON")
    sub.choices["remove"].add_argument("targets", nargs="+", help="container name, image ref/id or volume name")
    sub.choices["remove"].add_argument("--dry-run", action="store_true")
    sub.add_parser("usage")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    if args.command == "usage":
        print(json.dumps(cli_usage.summarize(CLI, COMMANDS), ensure_ascii=False, indent=2))
        cli_usage.record(CLI, "usage", started, 0)
        return 0
    roots = [os.path.abspath(os.path.expanduser(r)) for r in (args.root or DEFAULT_ROOTS)]
    try:
        if args.command == "list":
            result = plan(args.days, roots)
            print(json.dumps(result, ensure_ascii=False, indent=1) if args.json else render(result))
            code = 0
        elif args.command == "prune":
            code = prune(args.days, roots, args.dry_run, args.output)
        else:
            code = remove(args.targets, args.days, roots, args.dry_run)
    except (SweepError, OSError) as exc:
        category = getattr(exc, "category", "os")
        print(f"error[{category}]: {exc}", file=sys.stderr)
        code = 1
    cli_usage.record(CLI, args.command, started, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
