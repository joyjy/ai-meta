#!/usr/bin/env python3
"""Regression tests for docker_test_sweep.py: which docker deletions prune and remove actually issue."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).with_name("docker_test_sweep.py")
FAKE_DOCKER = """#!/usr/bin/env python3
import json, os, sys
state = json.load(open(os.environ["FAKE_DOCKER_STATE"]))
args = sys.argv[1:]
if args[:2] in (["ps", "-aq"],):
    print("\\n".join(c["Id"] for c in state["containers"]))
elif args[:2] == ["image", "ls"]:
    print("\\n".join(i["Id"] for i in state["images"]))
elif args[:2] == ["volume", "ls"]:
    print("\\n".join(v["Name"] for v in state["volumes"]))
elif args[1:2] == ["inspect"]:
    rows = {"container": state["containers"], "image": state["images"], "volume": state["volumes"]}[args[0]]
    key = "Name" if args[0] == "volume" else "Id"
    for wanted in args[4:]:
        print(json.dumps(next(r for r in rows if r[key] == wanted)))
elif args[:2] == ["system", "df"]:
    print(json.dumps({"Type": "Build Cache", "Size": "2GB", "Reclaimable": "1GB"}))
else:
    with open(os.environ["FAKE_DOCKER_CALLS"], "a") as log:
        log.write(" ".join(args) + "\\n")
"""


def ts(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S.123456789Z")


def compose(project: str, wd: Path, files: str = "") -> dict[str, str]:
    return {"com.docker.compose.project": project, "com.docker.compose.project.working_dir": str(wd),
            "com.docker.compose.project.config_files": files}


def container(cid: str, status: str, finished: float, labels: dict[str, str], image: str,
              volumes: tuple[str, ...] = ()) -> dict:
    return {"Id": cid, "Name": f"/{cid}", "Created": ts(60), "Image": image,
            "State": {"Status": status, "FinishedAt": ts(finished)}, "Config": {"Labels": labels},
            "Mounts": [{"Type": "volume", "Name": v} for v in volumes]}


def image(iid: str, tags: list[str], age: float, project: str | None = None, pulled: bool = False) -> dict:
    labels = {"com.docker.compose.project": project} if project else {}
    return {"Id": iid, "RepoTags": tags, "RepoDigests": [f"{tags[0]}@sha256:x"] if pulled else [],
            "Created": ts(age), "Metadata": {"LastTagTime": "0001-01-01T00:00:00Z"}, "Size": 1000,
            "Config": {"Labels": labels}}


class DockerTestSweepTest(unittest.TestCase):

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.root = self.tmp / "projects"
        app, dev = self.root / "app", self.root / "dev"
        app.mkdir(parents=True)
        dev.mkdir()
        (dev / "compose.yaml").write_text("name: dev-env\nservices: {}\n")
        anon, recent_anon = "a" * 64, "b" * 64
        self.state = {
            "containers": [
                container("repo-default", "exited", 30, compose("app", app), "sha256:repo"),
                container("batch-old", "exited", 30, compose("batch-1", app), "sha256:batch",
                          ("batch-1_db", anon)),
                container("batch-recent", "exited", 1, compose("batch-2", app), "sha256:batch2"),
                container("declared", "exited", 30, compose("dev-env", dev, str(dev / "compose.yaml")),
                          "sha256:dev"),
                container("plain-mysql", "exited", 30, {}, "sha256:mysql"),
                container("running", "running", 0, {}, "sha256:redis"),
            ],
            "images": [
                image("sha256:mysql", ["mysql:5.7"], 400, pulled=True),
                image("sha256:redis", ["redis:5"], 400, pulled=True),
                image("sha256:idle-pulled", ["kafka:2"], 400, pulled=True),
                image("sha256:repo", ["app-svc:latest"], 30, "app"),
                image("sha256:batch", ["batch-1-svc:latest"], 30, "batch-1"),
                image("sha256:batch2", ["batch-2-svc:latest"], 30, "batch-2"),
                image("sha256:dev", ["dev-env-svc:latest"], 30, "dev-env"),
                image("sha256:gone", ["gone-wt-lintest:latest"], 30, "gone-wt"),
                image("sha256:shared", ["shared-base:latest"], 30, "gone-wt"),
                image("sha256:fresh", ["gone-new-lintest:latest"], 1, "gone-new"),
                image("sha256:manual", ["verify:local"], 30),
                image("sha256:dangling0000", [], 30),
            ],
            "volumes": [
                {"Name": anon, "CreatedAt": ts(30), "Labels": {"com.docker.volume.anonymous": ""}},
                {"Name": recent_anon, "CreatedAt": ts(1), "Labels": {"com.docker.volume.anonymous": ""}},
                {"Name": "batch-1_db", "CreatedAt": ts(30), "Labels": {"com.docker.compose.project": "batch-1"}},
                {"Name": "app_db", "CreatedAt": ts(30), "Labels": {"com.docker.compose.project": "app"}},
                {"Name": "unknown_db", "CreatedAt": ts(30), "Labels": {"com.docker.compose.project": "unknown"}},
                {"Name": "plane-data", "CreatedAt": ts(30), "Labels": {}},
            ],
        }
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "docker").write_text(FAKE_DOCKER)
        (bin_dir / "docker").chmod(0o755)
        (self.tmp / "state.json").write_text(json.dumps(self.state))
        self.calls = self.tmp / "calls.log"
        self.env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                        FAKE_DOCKER_STATE=str(self.tmp / "state.json"), FAKE_DOCKER_CALLS=str(self.calls),
                        AI_META_USAGE_DIR=str(self.tmp / "usage"))

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["python3", str(SCRIPT), *args, "--root", str(self.root)],
                              capture_output=True, text=True, env=self.env)

    def issued(self) -> list[str]:
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def test_prune_removes_only_expired_ephemeral_artifacts(self) -> None:
        output = self.tmp / "report.json"
        proc = self.run_cli("prune", "--output", str(output))
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(sorted(self.issued()), sorted([
            "rm batch-old",
            "rmi batch-1-svc:latest",
            "rmi gone-wt-lintest:latest",
            "rmi sha256:dangling0000",
            "volume rm " + "a" * 64,
            "volume rm batch-1_db",
            "builder prune -f --filter until=168h",
        ]))
        verdicts = {i["name"]: i["verdict"] for i in json.loads(output.read_text())["plan"]["items"]}
        self.assertEqual(verdicts["plain-mysql"], "ask")
        self.assertEqual(verdicts["unknown_db"], "ask")
        self.assertEqual(verdicts["verify:local"], "ask")
        self.assertEqual(verdicts["shared-base:latest"], "ask")
        self.assertEqual(verdicts["kafka:2"], "keep")
        self.assertEqual(verdicts["plane-data"], "keep")

    def test_remove_acts_on_ask_and_refuses_keep(self) -> None:
        proc = self.run_cli("remove", "verify:local", "plain-mysql", "app-svc:latest")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("REFUSED app-svc:latest", proc.stdout)
        self.assertEqual(sorted(self.issued()), ["rm plain-mysql", "rmi verify:local"])


if __name__ == "__main__":
    unittest.main()
