"""GL-FIX-ATOMIC-SAVE-GENERATIONS guard test.

Joe's standing order (2026-07-15): "old state can never be silently recalled."
S3 restore must be reachable ONLY through an explicit, human-triggered path
(the FORCE_S3_RESTORE=1 env flag, or an authenticated admin endpoint). No
automatic boot/recovery code path may silently time-travel to a days-old S3
backup.

These are static (AST + source) assertions over the real boot files, so the
build fails if any future edit reintroduces an automatic S3 restore.
"""

import ast
import os

_HERE = os.path.dirname(__file__)
_APP_PY = os.path.normpath(os.path.join(_HERE, "..", "app.py"))
_RUNNER_PY = os.path.normpath(os.path.join(_HERE, "..", "substrate_runner.py"))


def _parents(tree):
    table = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            table[child] = node
    return table


def _enclosing_func(node, parents):
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
        cur = parents.get(cur)
    return None


def _guarded_by_force_flag(node, parents):
    """True if any ancestor `if` test references FORCE_S3_RESTORE."""
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, ast.If):
            if "FORCE_S3_RESTORE" in ast.dump(cur.test):
                return True
        cur = parents.get(cur)
    return False


def test_app_restore_from_s3_calls_are_human_only():
    """Every _restore_from_s3(...) call in app.py must be either guarded by a
    FORCE_S3_RESTORE env check or inside an admin (human API) endpoint."""
    src = open(_APP_PY).read()
    tree = ast.parse(src)
    parents = _parents(tree)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "_restore_from_s3":
            func_def = _enclosing_func(node, parents)
            fname = func_def.name if func_def else "<module>"
            is_admin = fname.startswith("admin_") or "restore_from_s3_prefix" in fname
            if not (is_admin or _guarded_by_force_flag(node, parents)):
                offenders.append((fname, node.lineno))
    assert not offenders, (
        "AUTOMATIC S3 restore reintroduced (must be FORCE_S3_RESTORE-gated or "
        f"an admin endpoint): {offenders}")


def test_gl_init_wires_local_generation_recovery_not_silent_s3():
    """The live boot (_gl_init) must recover from LOCAL generations on load
    failure, and must NOT silently attempt S3 (only the explicit
    FORCE_S3_RESTORE block may reference _restore_from_s3)."""
    src = open(_APP_PY).read()
    tree = ast.parse(src)
    gl_init = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "_gl_init")
    calls = [n for n in ast.walk(gl_init) if isinstance(n, ast.Call)]
    names = {c.func.id for c in calls
             if isinstance(c.func, ast.Name)}
    assert "_recover_from_local_generations" in names, (
        "_gl_init no longer wires local-generation recovery")
    # Any _restore_from_s3 inside _gl_init must be FORCE_S3_RESTORE-gated.
    parents = _parents(gl_init)
    for c in calls:
        if isinstance(c.func, ast.Name) and c.func.id == "_restore_from_s3":
            assert _guarded_by_force_flag(c, parents), (
                "_gl_init reaches S3 restore without a FORCE_S3_RESTORE guard "
                f"at line {c.lineno}")


def test_boot_substrate_s3_restore_is_force_gated():
    """The dead duplicate boot path (substrate_runner.boot_substrate) also gates
    its inline S3 restore behind FORCE_S3_RESTORE, so no dormant path can be
    revived into a silent time-travel."""
    src = open(_RUNNER_PY).read()
    tree = ast.parse(src)
    boot = next((n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "boot_substrate"),
                None)
    if boot is None:
        return  # function removed entirely -- also acceptable
    boot_src = ast.get_source_segment(src, boot) or ""
    if "list_objects_v2" not in boot_src and "download_file" not in boot_src:
        return  # no inline S3 restore remains
    assert "FORCE_S3_RESTORE" in boot_src, (
        "boot_substrate performs an S3 restore without a FORCE_S3_RESTORE gate")


if __name__ == "__main__":
    test_app_restore_from_s3_calls_are_human_only()
    test_gl_init_wires_local_generation_recovery_not_silent_s3()
    test_boot_substrate_s3_restore_is_force_gated()
    print("PASS: no silent S3 restore path")
