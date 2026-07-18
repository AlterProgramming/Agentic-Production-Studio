from __future__ import annotations

import copy
import difflib
import fnmatch
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable


class BuilderError(RuntimeError):
    """Raised when a plan is unsafe, stale, or fails validation."""


MISSING = object()
NO_DEFAULT = object()
TEXT_SUFFIXES = {".csv", ".gd", ".json", ".md", ".py", ".tres", ".tscn", ".txt", ".yaml", ".yml"}


def sha256_bytes(value: bytes | None) -> str | None:
    return None if value is None else hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def load_plan(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuilderError(f"Cannot load plan {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BuilderError("Plan root must be an object")
    return value


def normalize_rel(path: Any) -> str:
    if not isinstance(path, str) or not path.strip():
        raise BuilderError("Path must be a non-empty string")
    pure = PurePosixPath(path.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts:
        raise BuilderError(f"Path escapes workspace: {path}")
    normalized = pure.as_posix()
    if normalized in {"", "."}:
        raise BuilderError(f"Path must name a file: {path}")
    return normalized


def allowed(path: str, patterns: list[str]) -> bool:
    for raw in patterns:
        pattern = raw.replace("\\", "/")
        if pattern.endswith("/**") and (path == pattern[:-3] or path.startswith(pattern[:-2])):
            return True
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False


def pointer_parts(pointer: Any) -> list[str]:
    if pointer == "":
        return []
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise BuilderError(f"Invalid JSON pointer: {pointer!r}")
    return [item.replace("~1", "/").replace("~0", "~") for item in pointer[1:].split("/")]


def get_pointer(document: Any, pointer: str, default: Any = NO_DEFAULT) -> Any:
    current = document
    for token in pointer_parts(pointer):
        try:
            current = current[int(token)] if isinstance(current, list) else current[token]
        except (KeyError, IndexError, ValueError, TypeError):
            if default is NO_DEFAULT:
                raise BuilderError(f"JSON pointer does not exist: {pointer}")
            return default
    return current


def set_pointer(document: Any, pointer: str, value: Any, create_missing: bool = False) -> Any:
    parts = pointer_parts(pointer)
    if not parts:
        return copy.deepcopy(value)
    current = document
    for token in parts[:-1]:
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as exc:
                raise BuilderError(f"Cannot traverse JSON pointer: {pointer}") from exc
        elif isinstance(current, dict):
            if token not in current:
                if not create_missing:
                    raise BuilderError(f"JSON pointer parent does not exist: {pointer}")
                current[token] = {}
            current = current[token]
        else:
            raise BuilderError(f"Cannot traverse JSON pointer: {pointer}")
    final = parts[-1]
    if isinstance(current, list):
        try:
            current[int(final)] = copy.deepcopy(value)
        except (ValueError, IndexError) as exc:
            raise BuilderError(f"Cannot set JSON pointer: {pointer}") from exc
    elif isinstance(current, dict):
        if final not in current and not create_missing:
            raise BuilderError(f"JSON pointer does not exist: {pointer}")
        current[final] = copy.deepcopy(value)
    else:
        raise BuilderError(f"Cannot set JSON pointer: {pointer}")
    return document


class State:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.values: dict[str, bytes | None] = {}

    def resolve(self, rel: str) -> Path:
        candidate = (self.root / normalize_rel(rel)).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise BuilderError(f"Path escapes workspace: {rel}") from exc
        return candidate

    def read(self, rel: str) -> bytes | None:
        rel = normalize_rel(rel)
        if rel not in self.values:
            path = self.resolve(rel)
            self.values[rel] = path.read_bytes() if path.is_file() else None
        return self.values[rel]

    def write(self, rel: str, value: bytes | None) -> None:
        self.values[normalize_rel(rel)] = value


class Context:
    def __init__(self, state: State, patterns: list[str], touched: dict[str, list[str]]):
        self.state, self.patterns, self.touched = state, patterns, touched

    def target(self, path: Any, operation_id: str) -> str:
        path = normalize_rel(path)
        if not allowed(path, self.patterns):
            raise BuilderError(f"Operation {operation_id!r} targets disallowed path: {path}")
        self.touched.setdefault(path, []).append(operation_id)
        return path


Handler = Callable[[Context, dict[str, Any]], list[str]]


class OperationRegistry:
    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}

    def register(self, name: str, handler: Handler) -> None:
        if not name or name in self.handlers:
            raise BuilderError(f"Operation already registered: {name!r}")
        self.handlers[name] = handler

    def get(self, name: Any) -> Handler:
        if name not in self.handlers:
            raise BuilderError(f"Unsupported operation type: {name}")
        return self.handlers[name]

    @property
    def names(self) -> list[str]:
        return sorted(self.handlers)


def operation_id(operation: dict[str, Any]) -> str:
    value = operation.get("id")
    if not isinstance(value, str) or not value.strip():
        raise BuilderError("Each operation requires a non-empty id")
    return value


def write_text(ctx: Context, op: dict[str, Any]) -> list[str]:
    oid, path, content = operation_id(op), None, op.get("content")
    path = ctx.target(op.get("path"), oid)
    if not isinstance(content, str):
        raise BuilderError(f"Operation {oid!r} requires string content")
    before, after = ctx.state.read(path), content.encode(op.get("encoding", "utf-8"))
    if before != after:
        if before is not None and not op.get("overwrite", False):
            raise BuilderError(f"Operation {oid!r} refuses to overwrite {path}")
        ctx.state.write(path, after)
    return [path]


def replace_text(ctx: Context, op: dict[str, Any]) -> list[str]:
    oid, path = operation_id(op), ctx.target(op.get("path"), operation_id(op))
    old, new, expected = op.get("old"), op.get("new"), op.get("expected_count", 1)
    if not isinstance(old, str) or not old or not isinstance(new, str) or not isinstance(expected, int) or expected < 1:
        raise BuilderError(f"Operation {oid!r} has invalid replacement fields")
    before = ctx.state.read(path)
    if before is None:
        raise BuilderError(f"Operation {oid!r} requires existing file: {path}")
    try:
        text = before.decode(op.get("encoding", "utf-8"))
    except UnicodeDecodeError as exc:
        raise BuilderError(f"Operation {oid!r} requires text: {path}") from exc
    count = text.count(old)
    if count == 0 and op.get("allow_already_applied", True) and text.count(new) >= expected:
        return [path]
    if count != expected:
        raise BuilderError(f"Operation {oid!r} expected {expected} matches in {path}, found {count}")
    ctx.state.write(path, text.replace(old, new, expected).encode(op.get("encoding", "utf-8")))
    return [path]


def json_patch(ctx: Context, op: dict[str, Any]) -> list[str]:
    oid, path = operation_id(op), ctx.target(op.get("path"), operation_id(op))
    before = ctx.state.read(path)
    if before is None:
        raise BuilderError(f"Operation {oid!r} requires existing JSON: {path}")
    try:
        document = json.loads(before.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuilderError(f"Operation {oid!r} requires valid JSON: {path}") from exc
    changes = op.get("changes")
    if not isinstance(changes, list) or not changes:
        raise BuilderError(f"Operation {oid!r} requires changes")
    changed = False
    for item in changes:
        if not isinstance(item, dict) or "pointer" not in item or "value" not in item:
            raise BuilderError(f"Operation {oid!r} contains an invalid change")
        current, desired = get_pointer(document, item["pointer"], MISSING), item["value"]
        if current is not MISSING and current == desired:
            continue
        if "expect" in item and current != item["expect"]:
            found = "<missing>" if current is MISSING else repr(current)
            raise BuilderError(f"Operation {oid!r} stale JSON expectation at {path}{item['pointer']}: found {found}")
        document = set_pointer(document, item["pointer"], desired, bool(item.get("create_missing", False)))
        changed = True
    if changed:
        ctx.state.write(path, canonical_json(document))
    return [path]


def copy_file(ctx: Context, op: dict[str, Any]) -> list[str]:
    oid, source = operation_id(op), normalize_rel(op.get("source"))
    target = ctx.target(op.get("target"), oid)
    value = ctx.state.read(source)
    if value is None:
        raise BuilderError(f"Operation {oid!r} source does not exist: {source}")
    if op.get("expect_source_sha256") not in (None, sha256_bytes(value)):
        raise BuilderError(f"Operation {oid!r} source checksum mismatch: {source}")
    before = ctx.state.read(target)
    if before != value:
        if before is not None and not op.get("overwrite", False):
            raise BuilderError(f"Operation {oid!r} refuses to overwrite {target}")
        ctx.state.write(target, value)
    return [target]


def delete_file(ctx: Context, op: dict[str, Any]) -> list[str]:
    oid, path, expected = operation_id(op), ctx.target(op.get("path"), operation_id(op)), op.get("expect_sha256")
    if not isinstance(expected, str) or not expected:
        raise BuilderError(f"Operation {oid!r} requires expect_sha256")
    before = ctx.state.read(path)
    if before is None:
        if op.get("allow_missing", True):
            return [path]
        raise BuilderError(f"Operation {oid!r} cannot delete missing file: {path}")
    if sha256_bytes(before) != expected:
        raise BuilderError(f"Operation {oid!r} deletion checksum mismatch for {path}")
    ctx.state.write(path, None)
    return [path]


def default_registry() -> OperationRegistry:
    registry = OperationRegistry()
    for name, handler in (("copy_file", copy_file), ("delete_file", delete_file), ("json_patch", json_patch), ("replace_text", replace_text), ("write_text", write_text)):
        registry.register(name, handler)
    from .image_ops import register_image_operations
    register_image_operations(registry)
    return registry


def validate_plan(plan: dict[str, Any], registry: OperationRegistry) -> None:
    if plan.get("schema_version") != "1.0" or not isinstance(plan.get("plan_id"), str) or not plan["plan_id"].strip():
        raise BuilderError("Plan requires schema_version 1.0 and a plan_id")
    patterns, operations = plan.get("allowed_paths"), plan.get("operations")
    if not isinstance(patterns, list) or not patterns or not all(isinstance(item, str) and item for item in patterns):
        raise BuilderError("Plan requires allowed_paths")
    if not isinstance(operations, list) or not operations:
        raise BuilderError("Plan requires operations")
    ids: set[str] = set()
    for op in operations:
        if not isinstance(op, dict):
            raise BuilderError("Each operation must be an object")
        oid = operation_id(op)
        if oid in ids:
            raise BuilderError(f"Duplicate operation id: {oid}")
        ids.add(oid)
        registry.get(op.get("type"))
    for key in ("preconditions", "postconditions"):
        if not isinstance(plan.get(key, []), list):
            raise BuilderError(f"{key} must be a list")


def condition(state: State, item: dict[str, Any]) -> dict[str, Any]:
    ctype, path, expected = item.get("type"), normalize_rel(item.get("path")), item.get("value")
    value, passed, detail = state.read(path), False, ""
    if ctype == "exists":
        passed, detail = (value is not None) is bool(item.get("value", True)), f"exists={value is not None}"
    elif ctype == "sha256":
        actual = sha256_bytes(value); passed, detail = actual == expected, f"sha256={actual}"
    elif ctype == "max_bytes":
        actual = None if value is None else len(value); passed, detail = isinstance(expected, int) and actual is not None and actual <= expected, f"bytes={actual}"
    elif ctype == "text_contains":
        try: text = "" if value is None else value.decode()
        except UnicodeDecodeError: text = ""
        passed, detail = isinstance(expected, str) and expected in text, f"contains={expected!r}"
    elif ctype == "json_pointer_equals":
        try: actual = get_pointer(json.loads(value.decode()), item.get("pointer"), MISSING) if value is not None else MISSING
        except (UnicodeDecodeError, json.JSONDecodeError, BuilderError): actual = MISSING
        passed, detail = actual is not MISSING and actual == expected, f"actual={'<missing>' if actual is MISSING else repr(actual)}"
    else:
        raise BuilderError(f"Unsupported condition type: {ctype}")
    return {"id": item.get("id", ctype), "type": ctype, "path": path, "status": "PASS" if passed else "FAIL", "detail": detail}


def check_conditions(state: State, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = [condition(state, item) for item in items]
    failures = [item for item in results if item["status"] == "FAIL"]
    if failures:
        raise BuilderError("Condition failure: " + "; ".join(f"{item['id']}: {item['detail']}" for item in failures))
    return results


def text_diff(path: str, before: bytes | None, after: bytes | None) -> str | None:
    if Path(path).suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        old, new = "" if before is None else before.decode(), "" if after is None else after.decode()
    except UnicodeDecodeError:
        return None
    lines = list(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=f"a/{path}", tofile=f"b/{path}"))
    return "".join(lines[:240] + (["... diff truncated ...\n"] if len(lines) > 240 else []))


class StudioBuilder:
    def __init__(self, root: str | Path, registry: OperationRegistry | None = None):
        self.root, self.registry = Path(root).resolve(), registry or default_registry()

    def simulate(self, plan: dict[str, Any], mode: str) -> tuple[dict[str, Any], State]:
        validate_plan(plan, self.registry)
        state, originals, touched = State(self.root), {}, {}
        pre = check_conditions(state, plan.get("preconditions", []))
        operation_results = []
        ctx = Context(state, plan["allowed_paths"], touched)
        for op in plan["operations"]:
            paths = self.registry.get(op["type"])(ctx, op)
            for path in paths:
                if path not in originals:
                    disk = state.resolve(path); originals[path] = disk.read_bytes() if disk.is_file() else None
            operation_results.append({"id": op["id"], "type": op["type"], "paths": sorted(set(paths))})
        post = check_conditions(state, plan.get("postconditions", []))
        changes = []
        for path, before in sorted(originals.items()):
            after = state.read(path)
            if before == after:
                continue
            changes.append({"path": path, "operation_ids": touched.get(path, []), "before_sha256": sha256_bytes(before), "after_sha256": sha256_bytes(after), "before_bytes": None if before is None else len(before), "after_bytes": None if after is None else len(after), "action": "delete" if after is None else "create" if before is None else "update", "diff": text_diff(path, before, after)})
        receipt = {"schema_version": "1.0", "plan_id": plan["plan_id"], "plan_sha256": sha256_bytes(canonical_json(plan)), "mode": mode, "status": "PASS", "workspace_root": str(self.root), "generated_at": datetime.now(timezone.utc).isoformat(), "supported_operations": self.registry.names, "preconditions": pre, "operations": operation_results, "postconditions": post, "changes": changes, "summary": {"operations": len(operation_results), "changed_files": len(changes), "created": sum(c["action"] == "create" for c in changes), "updated": sum(c["action"] == "update" for c in changes), "deleted": sum(c["action"] == "delete" for c in changes)}}
        return receipt, state

    def preview(self, plan: dict[str, Any]) -> dict[str, Any]:
        return self.simulate(plan, "preview")[0]

    def apply(self, plan: dict[str, Any], receipt_path: str | Path | None = None) -> dict[str, Any]:
        receipt, state = self.simulate(plan, "apply")
        backups: dict[str, bytes | None] = {}
        try:
            for change in receipt["changes"]:
                rel, path = change["path"], state.resolve(change["path"])
                backups[rel] = path.read_bytes() if path.is_file() else None
                after = state.read(rel)
                if after is None:
                    if path.exists(): path.unlink()
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                    temp = Path(handle.name); handle.write(after); handle.flush(); os.fsync(handle.fileno())
                os.replace(temp, path)
        except Exception as exc:
            for rel, backup in backups.items():
                path = state.resolve(rel)
                if backup is None:
                    if path.exists(): path.unlink()
                else:
                    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(backup)
            raise BuilderError(f"Apply failed and workspace was rolled back: {exc}") from exc
        destination = Path(receipt_path) if receipt_path else self.root / ".studio-builder" / "receipts" / f"{plan['plan_id']}-{receipt['plan_sha256'][:12]}.json"
        if not destination.is_absolute(): destination = self.root / destination
        destination = destination.resolve(strict=False)
        try: destination.relative_to(self.root)
        except ValueError as exc: raise BuilderError("Receipt path must remain inside workspace") from exc
        receipt["receipt_path"] = destination.relative_to(self.root).as_posix()
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(canonical_json(receipt))
        return receipt

    def verify_receipt(self, receipt: dict[str, Any]) -> dict[str, Any]:
        if receipt.get("schema_version") != "1.0" or not isinstance(receipt.get("changes"), list):
            raise BuilderError("Receipt is invalid")
        state, checks = State(self.root), []
        for change in receipt["changes"]:
            actual, expected = sha256_bytes(state.read(change["path"])), change.get("after_sha256")
            checks.append({"path": change["path"], "status": "PASS" if actual == expected else "FAIL", "expected_sha256": expected, "actual_sha256": actual})
        return {"schema_version": "1.0", "plan_id": receipt.get("plan_id"), "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL", "checks": checks}
