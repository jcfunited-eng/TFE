"""Regression boundary for retired word-authored sensory producers."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = REPOSITORY_ROOT / "dsf_ai_service"


def _production_imports(module_name: str) -> tuple[Path, ...]:
    matches: list[Path] = []
    for path in SERVICE_ROOT.rglob("*.py"):
        if "/tests/" in path.as_posix() or path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = (node.module or "",)
            else:
                continue
            if any(
                value == module_name or value.endswith(f".{module_name}")
                for value in imported
            ):
                matches.append(path.relative_to(REPOSITORY_ROOT))
                break
    return tuple(sorted(matches))


def test_word_authored_sensory_corpus_and_parallel_engine_are_absent() -> None:
    assert not (SERVICE_ROOT / "sensory_corpus.py").exists()
    assert not (SERVICE_ROOT / "virtual_home.py").exists()
    compatibility_source = (
        SERVICE_ROOT / "gualaloom_engine.py"
    ).read_text(encoding="utf-8")
    assert "SENSORY_EXPERIENCES" not in compatibility_source
    assert "transduce_to_trit_state" not in compatibility_source
    assert "class GualaLoomEngine" not in compatibility_source
    assert _production_imports("sensory_corpus") == ()
    assert _production_imports("virtual_home") == ()
    assert _production_imports("gualaloom_engine") == (
        Path("dsf_ai_service/substrate/language_fact_strand.py"),
    )


def test_live_engine_does_not_mount_word_authored_sensory_bank() -> None:
    source = "\n".join(
        (
            (
                SERVICE_ROOT / "v4" / "guala_physical_runtime.py"
            ).read_text(encoding="utf-8"),
            (
                SERVICE_ROOT / "v4" / "guala_physical_runtime_core.py"
            ).read_text(encoding="utf-8"),
        )
    )
    tree = ast.parse(source)
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "SensoryBank" not in imported_names
    assert "SENSORY_DNA" not in imported_names
    assert "self.senses" not in source
    assert "_add_canonical_emulator_entries" not in source
