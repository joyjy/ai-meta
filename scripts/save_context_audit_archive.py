"""Build and verify lossless save-context audit archives before cleanup."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
from typing import Any

from save_context_audit_io import parse_json_object, run, write_text_atomic


ARCHIVE_SCHEMA = "save-context.audit-archive.v1"
ARCHIVE_DIRECTORY = "archived"
ARCHIVE_WORKSPACE_FILES = {
    "AUDITOR.md",
    "AUDIT_TASK.md",
    "recovery-packet.md",
    "effective-ll.md",
    "agent-audit.yaml",
    "audit-summary.json",
}
ARCHIVE_ROOT_FILES = {
    "receipt.json",
    "settlement.json",
    "inspection.json",
    "run.json",
}


def path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and not item.is_symlink()
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_month(settlement: dict[str, Any]) -> str:
    settled_at = settlement.get("settled_at")
    if not isinstance(settled_at, str):
        raise RuntimeError("settlement is missing settled_at")
    try:
        parsed = datetime.fromisoformat(settled_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("settlement settled_at is invalid") from error
    return parsed.astimezone(timezone.utc).strftime("%Y-%m")


def archive_paths(
    receipt_path: Path,
    settlement: dict[str, Any],
    audit_id: str,
    archive_root: str | None,
) -> tuple[Path, Path]:
    root = (
        Path(archive_root).expanduser().resolve()
        if archive_root
        else receipt_path.parent.parent / ARCHIVE_DIRECTORY
    )
    bundle = root / archive_month(settlement) / f"{audit_id}.tar.zst"
    try:
        bundle.relative_to(receipt_path.parent)
    except ValueError:
        pass
    else:
        raise RuntimeError(f"archive destination is inside the source audit: {bundle}")
    return bundle, bundle.with_suffix(bundle.suffix + ".sha256")


def archive_source_files(receipt_path: Path, workspace: Path) -> list[tuple[Path, str]]:
    audit_dir = receipt_path.parent
    files: list[tuple[Path, str]] = []
    for name in sorted(ARCHIVE_ROOT_FILES):
        path = audit_dir / name
        if path.is_symlink():
            raise RuntimeError(f"archive input must not be a symlink: {path}")
        if path.is_file():
            files.append((path, name))

    if workspace.exists():
        if workspace.is_symlink() or not workspace.is_dir():
            raise RuntimeError(f"archive workspace must be a real directory: {workspace}")
        unexpected: list[str] = []
        for path in workspace.rglob("*"):
            relative = path.relative_to(workspace)
            if relative.parts and relative.parts[0] == ".git":
                continue
            if path.is_symlink():
                unexpected.append(str(path))
            elif path.is_file() and relative.as_posix() not in ARCHIVE_WORKSPACE_FILES:
                unexpected.append(str(path))
            elif path.is_dir():
                unexpected.append(str(path))
        if unexpected:
            raise RuntimeError(
                "archive workspace contains non-whitelisted paths: "
                + ", ".join(sorted(unexpected))
            )
        for name in sorted(ARCHIVE_WORKSPACE_FILES):
            path = workspace / name
            if path.is_file():
                files.append((path, f"workspace/{name}"))
    return files


def archive_manifest(
    receipt: dict[str, Any],
    settlement: dict[str, Any],
    files: list[tuple[Path, str]],
) -> dict[str, Any]:
    return {
        "schema": ARCHIVE_SCHEMA,
        "audit_id": receipt["audit_id"],
        "run_id": receipt["run_id"],
        "settlement_status": settlement["status"],
        "settled_at": settlement["settled_at"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            {
                "path": archive_name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path, archive_name in files
        ],
        "excluded": ["workspace/.git/"],
    }


def write_tar(path: Path, files: list[tuple[Path, str]], manifest: dict[str, Any]) -> None:
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as archive:
        for source, archive_name in files:
            info = tarfile.TarInfo(archive_name)
            info.size = source.stat().st_size
            info.mode = 0o600
            info.mtime = 0
            with source.open("rb") as content:
                archive.addfile(info, content)
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest_bytes)
        info.mode = 0o600
        info.mtime = 0
        archive.addfile(info, io.BytesIO(manifest_bytes))


def verify_bundle(
    bundle: Path,
    digest_path: Path,
    audit_id: str,
    run_id: str,
    zstd_command: str,
) -> dict[str, Any]:
    if not bundle.is_file():
        raise RuntimeError(f"archive bundle not found: {bundle}")
    digest = sha256_file(bundle)
    if digest_path.is_file():
        digest_tokens = digest_path.read_text(encoding="utf-8").strip().split()
        if not digest_tokens:
            raise RuntimeError(f"archive bundle digest file is empty: {digest_path}")
        expected = digest_tokens[0]
        if expected != digest:
            raise RuntimeError(f"archive bundle digest mismatch: {bundle}")

    with tempfile.NamedTemporaryFile(
        prefix=f".{audit_id}.", suffix=".verify.tar", dir=bundle.parent, delete=False
    ) as temporary:
        tar_path = Path(temporary.name)
    try:
        run([zstd_command, "-q", "-d", "-f", str(bundle), "-o", str(tar_path)])
        with tarfile.open(tar_path, "r") as archive:
            members = archive.getmembers()
            if any(not member.isfile() for member in members):
                raise RuntimeError(f"archive bundle contains a non-file member: {bundle}")
            member_names = [member.name for member in members]
            if len(member_names) != len(set(member_names)):
                raise RuntimeError(f"archive bundle contains duplicate members: {bundle}")
            manifest_member = next(
                (member for member in members if member.name == "manifest.json"),
                None,
            )
            if manifest_member is None:
                raise RuntimeError(f"archive bundle is missing manifest.json: {bundle}")
            manifest_file = archive.extractfile(manifest_member)
            if manifest_file is None:
                raise RuntimeError(f"archive manifest is unreadable: {bundle}")
            manifest = parse_json_object(
                manifest_file.read().decode("utf-8"), "archive manifest"
            )
            if (
                manifest.get("schema") != ARCHIVE_SCHEMA
                or manifest.get("audit_id") != audit_id
                or manifest.get("run_id") != run_id
            ):
                raise RuntimeError(f"archive manifest identity mismatch: {bundle}")
            entries = manifest.get("files")
            if not isinstance(entries, list):
                raise RuntimeError(f"archive manifest files are invalid: {bundle}")
            expected_names = {"manifest.json"}
            for entry in entries:
                if not isinstance(entry, dict):
                    raise RuntimeError(f"archive manifest entry is invalid: {bundle}")
                name = entry.get("path")
                expected_hash = entry.get("sha256")
                expected_bytes = entry.get("bytes")
                allowed_name = (
                    name in ARCHIVE_ROOT_FILES
                    or isinstance(name, str)
                    and name.startswith("workspace/")
                    and name.removeprefix("workspace/") in ARCHIVE_WORKSPACE_FILES
                )
                if (
                    not isinstance(name, str)
                    or not allowed_name
                    or not isinstance(expected_hash, str)
                    or not isinstance(expected_bytes, int)
                    or expected_bytes < 0
                ):
                    raise RuntimeError(f"archive manifest entry is incomplete: {bundle}")
                try:
                    member = archive.getmember(name)
                except KeyError as error:
                    raise RuntimeError(f"archive member is missing: {name}") from error
                content = archive.extractfile(member)
                payload = content.read() if content is not None else None
                if (
                    payload is None
                    or len(payload) != expected_bytes
                    or hashlib.sha256(payload).hexdigest() != expected_hash
                ):
                    raise RuntimeError(f"archive member digest mismatch: {name}")
                expected_names.add(name)
            if {member.name for member in members} != expected_names:
                raise RuntimeError(f"archive bundle has unmanifested members: {bundle}")
    finally:
        tar_path.unlink(missing_ok=True)
    return {"sha256": digest, "manifest": manifest}


def ensure_bundle(
    receipt_path: Path,
    receipt: dict[str, Any],
    settlement: dict[str, Any],
    workspace: Path,
    archive_root: str | None,
    zstd_command: str,
) -> tuple[Path, Path, str]:
    audit_id = receipt.get("audit_id")
    run_id = receipt.get("run_id")
    if not isinstance(audit_id, str) or not isinstance(run_id, str):
        raise RuntimeError("receipt is missing audit_id or run_id")
    bundle, digest_path = archive_paths(
        receipt_path, settlement, audit_id, archive_root
    )
    bundle.parent.mkdir(parents=True, exist_ok=True)
    if bundle.exists():
        verified = verify_bundle(bundle, digest_path, audit_id, run_id, zstd_command)
        if not digest_path.exists():
            write_text_atomic(digest_path, f"{verified['sha256']}  {bundle.name}\n")
        return bundle, digest_path, verified["sha256"]

    files = archive_source_files(receipt_path, workspace)
    manifest = archive_manifest(receipt, settlement, files)
    with tempfile.NamedTemporaryFile(
        prefix=f".{audit_id}.", suffix=".tar", dir=bundle.parent, delete=False
    ) as temporary:
        tar_path = Path(temporary.name)
    compressed_path = tar_path.with_suffix(".tar.zst.tmp")
    try:
        write_tar(tar_path, files, manifest)
        run([zstd_command, "-q", "-f", str(tar_path), "-o", str(compressed_path)])
        verified = verify_bundle(
            compressed_path,
            compressed_path.with_suffix(compressed_path.suffix + ".sha256"),
            audit_id,
            run_id,
            zstd_command,
        )
        compressed_path.replace(bundle)
        write_text_atomic(digest_path, f"{verified['sha256']}  {bundle.name}\n")
        return bundle, digest_path, verified["sha256"]
    finally:
        tar_path.unlink(missing_ok=True)
        compressed_path.unlink(missing_ok=True)


def archived_runs(runtime_db: Path) -> dict[str, bool]:
    if not runtime_db.is_file():
        raise RuntimeError(f"Rollerskate runtime database not found: {runtime_db}")
    try:
        connection = sqlite3.connect(f"file:{runtime_db}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT run_id, archived_at IS NOT NULL FROM agent_runs"
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise RuntimeError(
            f"cannot read Rollerskate runtime database {runtime_db}: {error}"
        ) from error
    return {str(run_id): bool(archived) for run_id, archived in rows}
