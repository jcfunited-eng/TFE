#!/usr/bin/env python3
"""Build and verify the deterministic, reviewed Guala release context."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA = "guala.reviewed_release_manifest.v1"
RECEIPT_SCHEMA = "guala.reviewed_release_receipt.v1"
CANONICAL_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
CANONICAL_FILE_MODE = 0o100644
GENERATED_RECEIPT = "_release/release-receipt.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReleasePackagingError(RuntimeError):
    """One fail-closed release packaging error."""


def _fail(message: str) -> None:
    raise ReleasePackagingError(message)


def _duplicate_rejecting_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_relative(value: str, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty string")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail(f"{label} is not a canonical relative POSIX path: {value!r}")
    return path


def _read_manifest(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicate_rejecting_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"manifest is not strict canonical JSON: {error}")
    if not isinstance(value, dict):
        _fail("manifest root must be an object")
    if raw != _canonical_json(value):
        _fail("manifest bytes are not canonical sorted UTF-8 JSON")
    if value.get("schema") != SCHEMA:
        _fail(f"manifest schema must be {SCHEMA}")
    if value.get("release_name") != "guala-production":
        _fail("manifest release_name must be guala-production")
    if set(value) != {
        "schema",
        "release_name",
        "runtime_entrypoints",
        "internal_import_roots",
        "internal_import_aliases",
        "categories",
        "forbidden_source_patterns",
    }:
        _fail("manifest root keys differ from the reviewed schema")
    return value, raw


def _run_git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        _fail(
            "git command failed: "
            + " ".join(arguments)
            + ": "
            + completed.stderr.strip()
        )
    return completed.stdout


def _prove_clean_commit(root: Path) -> str:
    commit = _run_git(root, "rev-parse", "--verify", "HEAD").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        _fail("HEAD is not an exact commit")
    dirty = _run_git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if dirty:
        _fail("working tree is dirty or has untracked files")
    return commit


def _tracked_paths(root: Path) -> set[str]:
    raw = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if raw.returncode != 0:
        _fail("could not enumerate tracked files")
    return {
        item.decode("utf-8")
        for item in raw.stdout.split(b"\0")
        if item
    }


def _prove_regular_file(root: Path, relative: PurePosixPath) -> Path:
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        try:
            mode = cursor.lstat().st_mode
        except FileNotFoundError:
            _fail(f"reviewed source path is missing: {relative.as_posix()}")
        if stat.S_ISLNK(mode):
            _fail(f"symlink is forbidden in release source: {relative.as_posix()}")
    if not stat.S_ISREG(cursor.lstat().st_mode):
        _fail(f"reviewed source is not a regular file: {relative.as_posix()}")
    try:
        cursor.resolve().relative_to(root.resolve())
    except ValueError:
        _fail(f"reviewed source escapes repository: {relative.as_posix()}")
    return cursor


def _module_path(root: Path, module: str) -> set[str]:
    parts = module.split(".")
    base = root.joinpath(*parts)
    result: set[str] = set()
    source = base.with_suffix(".py")
    package = base / "__init__.py"
    if source.is_file():
        result.add(source.relative_to(root).as_posix())
    if package.is_file():
        result.add(package.relative_to(root).as_posix())
    return result


def _module_name(path: str) -> tuple[str, bool]:
    module = path[:-3].replace("/", ".")
    package = module.endswith(".__init__")
    if package:
        module = module[: -len(".__init__")]
    return module, package


def _parent_initializers(root: Path, path: str) -> set[str]:
    result: set[str] = set()
    cursor = Path(path).parent
    while cursor != Path("."):
        candidate = root / cursor / "__init__.py"
        if candidate.is_file():
            result.add(candidate.relative_to(root).as_posix())
        cursor = cursor.parent
    return result


def resolve_runtime_closure(
    root: Path,
    entrypoints: list[str],
    internal_roots: list[str],
    internal_aliases: dict[str, str] | None = None,
    used_aliases: set[str] | None = None,
) -> set[str]:
    roots = tuple(internal_roots)
    root_prefixes = tuple(item + "." for item in roots)
    aliases = internal_aliases or {}
    pending = list(entrypoints)
    resolved: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in resolved:
            continue
        source_path = _prove_regular_file(
            root,
            _safe_relative(relative, label="runtime source"),
        )
        if source_path.suffix != ".py":
            _fail(f"runtime import closure contains non-Python file: {relative}")
        resolved.add(relative)
        pending.extend(_parent_initializers(root, relative) - resolved)
        try:
            tree = ast.parse(source_path.read_bytes(), filename=relative)
        except SyntaxError as error:
            _fail(f"runtime source does not compile: {relative}: {error}")
        current_module, is_package = _module_name(relative)
        current_package = (
            current_module
            if is_package
            else current_module.rpartition(".")[0]
        )
        imported: set[str] = set()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = current_package.split(".") if current_package else []
                    retained = len(parts) - node.level + 1
                    if retained < 0:
                        _fail(f"invalid relative import in {relative}")
                    prefix = ".".join(parts[:retained])
                    base = ".".join(
                        item for item in (prefix, node.module or "") if item
                    )
                else:
                    base = node.module or ""
                names = [base]
                names.extend(
                    f"{base}.{alias.name}" if base else alias.name
                    for alias in node.names
                    if alias.name != "*"
                )
            for name in names:
                alias_path = aliases.get(name)
                if alias_path is not None:
                    imported.add(alias_path)
                    if used_aliases is not None:
                        used_aliases.add(name)
                if name in roots or name.startswith(root_prefixes):
                    imported.update(_module_path(root, name))
        pending.extend(imported - resolved)
    return resolved


def _manifest_entries(
    manifest: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, set[str]]]:
    categories = manifest.get("categories")
    if not isinstance(categories, list) or not categories:
        _fail("manifest categories must be a non-empty array")
    category_names: set[str] = set()
    source_paths: set[str] = set()
    archive_paths: set[str] = set()
    all_entries: list[dict[str, str]] = []
    by_category: dict[str, set[str]] = {}
    for category in categories:
        if not isinstance(category, dict) or set(category) != {
            "name",
            "archive_prefix",
            "reason",
            "files",
        }:
            _fail("manifest category keys differ from the reviewed schema")
        name = category["name"]
        reason = category["reason"]
        prefix = category["archive_prefix"]
        files = category["files"]
        if (
            not isinstance(name, str)
            or not name
            or name in category_names
            or not isinstance(reason, str)
            or not reason
            or not isinstance(files, list)
            or not files
        ):
            _fail("manifest category metadata is invalid or duplicated")
        category_names.add(name)
        prefix_path = (
            _safe_relative(prefix, label="archive prefix")
            if prefix
            else None
        )
        by_category[name] = set()
        for item in files:
            if not isinstance(item, str):
                _fail(f"category {name} contains a non-string file")
            source = _safe_relative(item, label=f"{name} source").as_posix()
            archive = (
                (prefix_path / source).as_posix()
                if prefix_path is not None
                else source
            )
            _safe_relative(archive, label=f"{name} archive path")
            if source in source_paths:
                _fail(f"duplicate reviewed source path: {source}")
            if archive in archive_paths or archive == GENERATED_RECEIPT:
                _fail(f"duplicate or reserved archive path: {archive}")
            source_paths.add(source)
            archive_paths.add(archive)
            by_category[name].add(source)
            all_entries.append({
                "archive_path": archive,
                "category": name,
                "reason": reason,
                "source_path": source,
            })
    return all_entries, by_category


def _validate_manifest(
    root: Path,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> tuple[list[dict[str, str]], dict[str, set[str]]]:
    entries, by_category = _manifest_entries(manifest)
    tracked = _tracked_paths(root)
    relative_manifest = manifest_path.resolve().relative_to(
        root.resolve()
    ).as_posix()
    for path in {entry["source_path"] for entry in entries} | {
        relative_manifest
    }:
        if path not in tracked:
            _fail(f"reviewed release input is not tracked: {path}")
        _prove_regular_file(root, _safe_relative(path, label="tracked source"))
    entrypoints = manifest["runtime_entrypoints"]
    internal_roots = manifest["internal_import_roots"]
    internal_aliases = manifest["internal_import_aliases"]
    if (
        not isinstance(entrypoints, list)
        or not entrypoints
        or not all(isinstance(item, str) for item in entrypoints)
        or not isinstance(internal_roots, list)
        or not internal_roots
        or not all(
            isinstance(item, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item)
            for item in internal_roots
        )
        or not isinstance(internal_aliases, dict)
        or not all(
            isinstance(name, str)
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
            and isinstance(path, str)
            for name, path in internal_aliases.items()
        )
    ):
        _fail("runtime entrypoint or internal import root contract is invalid")
    for alias_path in internal_aliases.values():
        _safe_relative(alias_path, label="internal import alias")
    runtime = by_category.get("runtime_python")
    if runtime is None:
        _fail("runtime_python category is required")
    used_aliases: set[str] = set()
    closure = resolve_runtime_closure(
        root,
        entrypoints,
        internal_roots,
        internal_aliases,
        used_aliases,
    )
    missing = sorted(closure - runtime)
    unreviewed = sorted(runtime - closure)
    unused_aliases = sorted(set(internal_aliases) - used_aliases)
    if missing or unreviewed or unused_aliases:
        _fail(
            "runtime manifest drift: "
            f"missing={missing!r} unconnected={unreviewed!r} "
            f"unused_aliases={unused_aliases!r}"
        )
    forbidden = manifest["forbidden_source_patterns"]
    if (
        not isinstance(forbidden, list)
        or not forbidden
        or not all(isinstance(item, str) and item for item in forbidden)
    ):
        _fail("forbidden source patterns must be a non-empty string array")
    for entry in entries:
        path = entry["source_path"]
        for expression in forbidden:
            try:
                matched = re.search(expression, path)
            except re.error as error:
                _fail(f"invalid forbidden source regex {expression!r}: {error}")
            if matched:
                _fail(
                    f"reviewed source violates forbidden pattern "
                    f"{expression!r}: {path}"
                )
    return entries, by_category


def _write_stage_file(stage: Path, relative: str, value: bytes) -> None:
    target = stage.joinpath(*PurePosixPath(relative).parts)
    target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if target.exists():
        _fail(f"stage path already exists: {relative}")
    target.write_bytes(value)
    target.chmod(0o644)


def _receipt(
    *,
    release_name: str,
    commit: str,
    manifest_bytes: bytes,
    entries: list[dict[str, str]],
    file_records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "release_name": release_name,
        "git_commit": commit,
        "manifest_sha256": _sha256_bytes(manifest_bytes),
        "archive_contract": {
            "entry_order": "utf8_lexicographic",
            "file_mode_octal": "100644",
            "timestamp": "1980-01-01T00:00:00Z",
            "zip_comment": "",
            "zip_entry_extra_fields": False,
        },
        "source_file_count": len(entries),
        "files": sorted(file_records, key=lambda item: item["archive_path"]),
    }


def _write_zip(stage: Path, zip_path: Path) -> None:
    paths = sorted(
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    )
    with zipfile.ZipFile(
        zip_path,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        archive.comment = b""
        for relative in paths:
            value = stage.joinpath(*PurePosixPath(relative).parts).read_bytes()
            info = zipfile.ZipInfo(relative, CANONICAL_ZIP_TIMESTAMP)
            info.create_system = 3
            info.external_attr = CANONICAL_FILE_MODE << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info.extra = b""
            archive.writestr(info, value, compresslevel=9)


def verify_context(context: Path) -> dict[str, Any]:
    context = context.resolve()
    receipt_path = context / GENERATED_RECEIPT
    if not receipt_path.is_file() or receipt_path.is_symlink():
        _fail("release context has no regular receipt")
    try:
        receipt = json.loads(
            receipt_path.read_text(encoding="utf-8"),
            object_pairs_hook=_duplicate_rejecting_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"release receipt is invalid: {error}")
    if receipt_path.read_bytes() != _canonical_json(receipt):
        _fail("release receipt is not canonical JSON")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        _fail("release receipt schema mismatch")
    expected = {GENERATED_RECEIPT}
    files = receipt.get("files")
    if not isinstance(files, list):
        _fail("release receipt files are absent")
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "archive_path",
            "category",
            "reason",
            "sha256",
            "size_bytes",
            "source_path",
        }:
            _fail("release receipt file record is invalid")
        relative_path = _safe_relative(
            item["archive_path"],
            label="receipt archive path",
        )
        relative = relative_path.as_posix()
        expected.add(relative)
        source = _prove_regular_file(context, relative_path)
        value = source.read_bytes()
        if (
            len(value) != item["size_bytes"]
            or _sha256_bytes(value) != item["sha256"]
        ):
            _fail(f"release context hash mismatch: {relative}")
    actual = {
        path.relative_to(context).as_posix()
        for path in context.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if actual != expected:
        _fail(
            "release context contains missing or unreviewed paths: "
            f"missing={sorted(expected-actual)!r} "
            f"unreviewed={sorted(actual-expected)!r}"
        )
    return receipt


def verify_archive(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        if archive.comment:
            _fail("release archive has a non-empty comment")
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if names != sorted(names) or len(names) != len(set(names)):
            _fail("release archive entries are not unique canonical order")
        for info in infos:
            _safe_relative(info.filename, label="archive entry")
            if (
                info.is_dir()
                or info.date_time != CANONICAL_ZIP_TIMESTAMP
                or info.extra
                or info.create_system != 3
                or (info.external_attr >> 16) != CANONICAL_FILE_MODE
            ):
                _fail(f"non-canonical archive metadata: {info.filename}")
        receipt_bytes = archive.read(GENERATED_RECEIPT)
        try:
            receipt = json.loads(
                receipt_bytes.decode("utf-8"),
                object_pairs_hook=_duplicate_rejecting_object,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            _fail(f"archive receipt is invalid: {error}")
        if receipt_bytes != _canonical_json(receipt):
            _fail("archive receipt is not canonical JSON")
        if receipt.get("schema") != RECEIPT_SCHEMA:
            _fail("archive receipt schema mismatch")
        expected = {
            GENERATED_RECEIPT,
            *[item["archive_path"] for item in receipt["files"]],
        }
        if set(names) != expected:
            _fail("archive entries differ from release receipt")
        for item in receipt["files"]:
            value = archive.read(item["archive_path"])
            if (
                len(value) != item["size_bytes"]
                or _sha256_bytes(value) != item["sha256"]
            ):
                _fail(f"archive content hash mismatch: {item['archive_path']}")
        return receipt


def package_release(
    *,
    root: Path,
    manifest_path: Path,
    stage: Path,
    zip_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    if stage.exists() or zip_path.exists():
        _fail("stage directory and archive path must not already exist")
    commit = _prove_clean_commit(root)
    manifest, manifest_bytes = _read_manifest(manifest_path)
    entries, _ = _validate_manifest(root, manifest, manifest_path)
    stage.mkdir(mode=0o755, parents=False)
    records: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda item: item["archive_path"]):
        source = _prove_regular_file(
            root,
            _safe_relative(entry["source_path"], label="reviewed source"),
        )
        value = source.read_bytes()
        _write_stage_file(stage, entry["archive_path"], value)
        records.append({
            **entry,
            "sha256": _sha256_bytes(value),
            "size_bytes": len(value),
        })
    receipt = _receipt(
        release_name=manifest["release_name"],
        commit=commit,
        manifest_bytes=manifest_bytes,
        entries=entries,
        file_records=records,
    )
    _write_stage_file(stage, GENERATED_RECEIPT, _canonical_json(receipt))
    verify_context(stage)
    _write_zip(stage, zip_path)
    verify_archive(zip_path)
    return {
        "schema": "guala.release_packaging_result.v1",
        "status": "verified",
        "git_commit": commit,
        "source_file_count": len(entries),
        "stage_dir": str(stage),
        "archive_path": str(zip_path),
        "archive_sha256": _sha256_bytes(zip_path.read_bytes()),
        "receipt_sha256": _sha256_bytes(
            (stage / GENERATED_RECEIPT).read_bytes()
        ),
    }


def render_runtime_manifest(
    *,
    root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Return canonical manifest data with both import closures inserted.

    This command never packages and never relaxes the clean-commit gate. Its
    output is a review candidate: the caller must inspect and commit the exact
    manifest change before `package` can succeed.
    """
    manifest, _ = _read_manifest(manifest_path.resolve())
    used_aliases: set[str] = set()
    closure = sorted(resolve_runtime_closure(
        root.resolve(),
        manifest["runtime_entrypoints"],
        manifest["internal_import_roots"],
        manifest["internal_import_aliases"],
        used_aliases,
    ))
    rendered = json.loads(json.dumps(manifest))
    runtime_matches = [
        category
        for category in rendered["categories"]
        if category["name"] == "runtime_python"
    ]
    if len(runtime_matches) != 1:
        _fail("manifest must contain exactly one runtime_python category")
    runtime_matches[0]["files"] = closure
    migration_matches = [
        category
        for category in rendered["categories"]
        if category["name"] == "migration_control"
    ]
    if len(migration_matches) > 1:
        _fail("manifest contains duplicate migration_control categories")
    if migration_matches:
        migration_closure = resolve_runtime_closure(
            root.resolve(),
            ["tools/migrate_guala_physical_state.py"],
            manifest["internal_import_roots"],
            manifest["internal_import_aliases"],
            used_aliases,
        )
        migration_matches[0]["files"] = sorted(
            migration_closure - set(closure)
        )
    rendered["internal_import_aliases"] = {
        name: path
        for name, path in sorted(
            rendered["internal_import_aliases"].items()
        )
        if name in used_aliases
    }
    return rendered


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    package = subparsers.add_parser("package")
    package.add_argument("--source-root", type=Path, required=True)
    package.add_argument("--manifest", type=Path, required=True)
    package.add_argument("--stage-dir", type=Path, required=True)
    package.add_argument("--zip-path", type=Path, required=True)
    verify = subparsers.add_parser("verify-context")
    verify.add_argument("--context", type=Path, required=True)
    archive = subparsers.add_parser("verify-archive")
    archive.add_argument("--archive", type=Path, required=True)
    render = subparsers.add_parser("render-manifest")
    render.add_argument("--source-root", type=Path, required=True)
    render.add_argument("--manifest", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "package":
            result = package_release(
                root=arguments.source_root,
                manifest_path=arguments.manifest,
                stage=arguments.stage_dir,
                zip_path=arguments.zip_path,
            )
        elif arguments.command == "verify-context":
            result = verify_context(arguments.context)
        elif arguments.command == "verify-archive":
            result = verify_archive(arguments.archive)
        else:
            result = render_runtime_manifest(
                root=arguments.source_root,
                manifest_path=arguments.manifest,
            )
    except ReleasePackagingError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(_canonical_json(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
