"""Read-only pipeline selection and bounded waiting for gitlab-ci."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from urllib.parse import quote, urlparse


class PipelineReader:
    def __init__(self, deadline: float):
        self.deadline = deadline
        self.hostname = ""

    def request(self, cmd: list[str]):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("pipeline query deadline exceeded")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("GitLab request exceeded pipeline query deadline") from exc
        if proc.returncode:
            raise RuntimeError(f"GitLab read failed (exit {proc.returncode}): {proc.stderr.strip()}")
        return proc.stdout

    def command(self, cmd: list[str]):
        return json.loads(self.request(cmd))

    def api(self, endpoint: str, paginate: bool = False):
        cmd = ["glab", "api", endpoint, "--hostname", self.hostname]
        if paginate:
            cmd += ["--paginate", "--output", "ndjson"]
            result = []
            for line in self.request(cmd).splitlines():
                value = json.loads(line)
                result.extend(value if isinstance(value, list) else [value])
            return result
        return self.command(cmd)


def execute(args) -> int:
    waiting = args.command == "wait"
    timeout = args.timeout if waiting else 60
    reader = PipelineReader(time.monotonic() + timeout)
    selection = {"repo": args.repo, "mr": args.mr, "sha": args.sha, "pipeline_id": args.pipeline_id}
    result = {"schemaVersion": "GitLabPipelineResult@1", "selection": selection,
              "complete": False, "outcome": "error"}
    try:
        repo = args.repo
        mr = args.mr
        if mr and "://" in mr:
            parsed = urlparse(mr)
            match = re.fullmatch(r"/(.+)/-/merge_requests/(\d+)/?", parsed.path)
            if not match or parsed.scheme not in {"https", "http"} or parsed.username:
                raise ValueError("--mr must be an MR URL or numeric IID")
            if repo:
                raise ValueError("use either an MR URL or --repo with an MR IID, not both")
            repo, mr = f"{parsed.scheme}://{parsed.netloc}/{match[1]}", match[2]
        if not repo:
            raise ValueError("pipeline selection requires --repo or a full MR URL")
        if mr and (not mr.isdigit() or int(mr) <= 0):
            raise ValueError("--mr must be a positive IID or full MR URL")
        if args.sha and not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", args.sha):
            raise ValueError("--sha requires a full commit SHA")
        project = reader.command(["glab", "repo", "view", repo, "--output", "json"])
        reader.hostname = urlparse(project["web_url"]).netloc
        project_id = int(project["id"])
        selection.update(repo=project["path_with_namespace"], hostname=reader.hostname, project_id=project_id)
        mr_endpoint = f"projects/{project_id}/merge_requests/{mr}" if mr else None
        mr_snapshot = None
        if mr_endpoint:
            mr_snapshot = reader.api(mr_endpoint)
            pipeline = mr_snapshot.get("head_pipeline")
            if not pipeline:
                raise RuntimeError("MR has no head pipeline yet; retry selection after CI creates it")
            if pipeline.get("sha") != mr_snapshot.get("sha"):
                raise RuntimeError("MR head pipeline SHA differs from MR head; select an explicit pipeline ID for merged-result pipelines")
            selection["mr_sha"] = mr_snapshot["sha"]
            project_id = int(pipeline["project_id"])
            pipeline_id = int(pipeline["id"])
        elif args.sha:
            pipelines = reader.api(f"projects/{project_id}/pipelines?sha={quote(args.sha)}&order_by=id&sort=desc&per_page=1")
            if not pipelines:
                raise RuntimeError("no pipeline exists for this SHA")
            pipeline_id = int(pipelines[0]["id"])
        else:
            pipeline_id = args.pipeline_id
        selection.update(pipeline_id=pipeline_id, pipeline_project_id=project_id)
        endpoint = f"projects/{project_id}/pipelines/{pipeline_id}"
        last_status = None
        while True:
            pipeline = reader.api(endpoint)
            if pipeline.get("id") != pipeline_id or pipeline.get("project_id") != project_id:
                raise RuntimeError("pipeline response identity differs from selected pipeline")
            if args.sha and pipeline.get("sha", "").lower() != args.sha.lower():
                raise RuntimeError("pipeline SHA differs from requested revision")
            status = pipeline["status"]
            result["pipeline"] = {k: pipeline.get(k) for k in ("id", "project_id", "sha", "ref", "status", "web_url")}
            if mr_endpoint:
                current = reader.api(mr_endpoint)
                head = current.get("head_pipeline") or {}
                if (current.get("sha") != mr_snapshot["sha"] or
                        head.get("id") != pipeline_id or head.get("project_id") != project_id):
                    result["outcome"] = "superseded"
                    return emit(result, 4)
            if status in {"success", "failed", "canceled", "skipped", "manual"} or not waiting:
                if args.with_job_details or waiting:
                    jobs = reader.api(endpoint + "/jobs?per_page=100", paginate=True)
                    result["jobs"] = [{k: job.get(k) for k in ("id", "name", "stage", "status", "allow_failure", "web_url")} for job in jobs]
                result.update(outcome=status, complete=status in {"success", "failed", "canceled", "skipped"})
                return emit(result, 0 if not waiting or status == "success" else 3)
            if status not in {"created", "waiting_for_resource", "preparing", "pending", "running", "scheduled"}:
                raise RuntimeError(f"unknown pipeline status: {status}")
            if status != last_status:
                print(f"pipeline {pipeline_id}: {status}", file=sys.stderr)
                last_status = status
            remaining = reader.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("pipeline wait deadline exceeded")
            time.sleep(min(args.interval, remaining))
    except TimeoutError as exc:
        result.update(outcome="timeout", error=str(exc))
        return emit(result, 124)
    except (RuntimeError, ValueError, KeyError, TypeError, OSError) as exc:
        result.update(outcome="error", error=str(exc))
        return emit(result, 1)


def emit(result, code):
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code
