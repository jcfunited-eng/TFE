"""Static guards for authenticated, fail-closed generation recovery.

Old state may never be recalled silently. Mutable flat S3 restore remains
human-only and force-gated. The live boot path may not call either flat S3
restore or the retired unauthenticated local-generation fallback.
"""

import ast
import os


_HERE = os.path.dirname(__file__)
_APP_PY = os.path.normpath(os.path.join(_HERE, "..", "app.py"))
_RUNNER_PY = os.path.normpath(
    os.path.join(_HERE, "..", "substrate_runner.py")
)


def _parents(tree):
    table = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            table[child] = node
    return table


def _enclosing_func(node, parents):
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
        current = parents.get(current)
    return None


def _guarded_by_force_flag(node, parents):
    current = parents.get(node)
    while current is not None:
        if (
            isinstance(current, ast.If)
            and "FORCE_S3_RESTORE" in ast.dump(current.test)
        ):
            return True
        current = parents.get(current)
    return False


def test_app_restore_from_s3_calls_are_human_only():
    with open(_APP_PY, encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)
    parents = _parents(tree)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id == "_restore_from_s3":
            function_definition = _enclosing_func(node, parents)
            function_name = (
                function_definition.name
                if function_definition is not None
                else "<module>"
            )
            is_admin = (
                function_name.startswith("admin_")
                or "restore_from_s3_prefix" in function_name
            )
            if not (is_admin or _guarded_by_force_flag(node, parents)):
                offenders.append((function_name, node.lineno))
    assert not offenders, (
        "automatic flat S3 restore reintroduced; references must be "
        f"FORCE_S3_RESTORE-gated or human admin endpoints: {offenders}"
    )


def test_gl_init_wires_no_unauthenticated_recovery_fallback():
    with open(_APP_PY, encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)
    gl_init = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_gl_init"
    )
    call_names = {
        call.func.id
        for call in ast.walk(gl_init)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }

    assert "_recover_from_local_generations" not in call_names, (
        "_gl_init reintroduced unauthenticated local-generation recovery"
    )
    assert "_restore_from_s3" not in call_names, (
        "_gl_init reintroduced mutable flat S3 restore"
    )


def test_boot_substrate_s3_restore_is_force_gated():
    with open(_RUNNER_PY, encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)
    boot = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "boot_substrate"
        ),
        None,
    )
    if boot is None:
        return
    boot_source = ast.get_source_segment(source, boot) or ""
    if (
        "list_objects_v2" not in boot_source
        and "download_file" not in boot_source
    ):
        return
    assert "FORCE_S3_RESTORE" in boot_source, (
        "boot_substrate performs an S3 restore without a force gate"
    )
