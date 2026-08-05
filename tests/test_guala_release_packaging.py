from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from dsf_ai_service.substrate.approved_curriculum_physical_surfaces import (
    _APPROVED_ALPHABET_ASSET_NAMES,
    _APPROVED_NUMBER_ASSET_NAMES,
)
from tools.package_guala_release import (
    CANONICAL_FILE_MODE,
    CANONICAL_ZIP_TIMESTAMP,
    GENERATED_RECEIPT,
    ReleasePackagingError,
    _canonical_json,
    _manifest_entries,
    _read_manifest,
    package_release,
    render_runtime_manifest,
    resolve_runtime_closure,
    verify_archive,
    verify_context,
)


ROOT = Path(__file__).resolve().parents[1]
NATIVE_CORE_SOURCES = {
    "native/guala_core/Cargo.lock",
    "native/guala_core/Cargo.toml",
    "native/guala_core/pyproject.toml",
    "native/guala_core/src/auditory.rs",
    "native/guala_core/src/auditory_incremental.rs",
    "native/guala_core/src/auditory_reachability.rs",
    "native/guala_core/src/canonical_basin.rs",
    "native/guala_core/src/canonical_causal_evidence.rs",
    "native/guala_core/src/canonical_l0_l4.rs",
    "native/guala_core/src/canonical_l0_l4_batch_api.rs",
    "native/guala_core/src/complete_neuron.rs",
    "native/guala_core/src/content_defined_chunker.rs",
    "native/guala_core/src/declared_geometric_anatomy.rs",
    "native/guala_core/src/developmental_electrical_anatomy.rs",
    "native/guala_core/src/elementary_charge_membrane.rs",
    "native/guala_core/src/elementary_charge_transfer.rs",
    "native/guala_core/src/embryonic_neuron_genesis_candidate.rs",
    "native/guala_core/src/exact_rational.rs",
    "native/guala_core/src/exact_time_grid_occurrence.rs",
    "native/guala_core/src/full_field_bank_final.rs",
    "native/guala_core/src/hippocampal_directory_cold_store.rs",
    "native/guala_core/src/hippocampal_reference_page.rs",
    "native/guala_core/src/hippocampal_sparse_path.rs",
    "native/guala_core/src/joint_field_l0_l4.rs",
    "native/guala_core/src/joint_source_episode.rs",
    "native/guala_core/src/joint_uf_neuron_boundary.rs",
    "native/guala_core/src/joint_uf_source_adapter.rs",
    "native/guala_core/src/joint_uf_v1_4.rs",
    "native/guala_core/src/joint_uf_v1_4_dynamic_fixture.rs",
    "native/guala_core/src/lattice_closed_membrane.rs",
    "native/guala_core/src/lib.rs",
    "native/guala_core/src/local_cupula_hair_bundle_geometry.rs",
    "native/guala_core/src/local_gating_spring_energy.rs",
    "native/guala_core/src/local_membrane_conductance_balance.rs",
    "native/guala_core/src/local_tip_link_extension.rs",
    "native/guala_core/src/materialized_fabric.rs",
    "native/guala_core/src/mounted_joint_fractal.rs",
    "native/guala_core/src/neuron_source_anchor.rs",
    "native/guala_core/src/optical_receptor_work.rs",
    "native/guala_core/src/ordered_gate_delivery_candidate.rs",
    "native/guala_core/src/organism.rs",
    "native/guala_core/src/organism_runtime.rs",
    "native/guala_core/src/physical_cognitive_capital.rs",
    "native/guala_core/src/physical_mosaic.rs",
    "native/guala_core/src/positional_krimelack_boundary.rs",
    "native/guala_core/src/reached_neuron_cohort.rs",
    "native/guala_core/src/reached_vestibular_bundle_path.rs",
    "native/guala_core/src/recovery_fluid_contact.rs",
    "native/guala_core/src/resident_cognitive_formation.rs",
    "native/guala_core/src/resident_cognitive_formation/real_body_migration_probe.rs",
    "native/guala_core/src/resident_cognitive_formation/reservoir_probe.rs",
    "native/guala_core/src/resident_d3_runtime.rs",
    "native/guala_core/src/resident_receptor_transition.rs",
    "native/guala_core/src/sha256.rs",
    "native/guala_core/src/sparse_electrical_contact.rs",
    "native/guala_core/src/vestibular_joint_source_builder.rs",
    "native/guala_core/src/vestibular_neuron_path.rs",
    "native/guala_core/src/virtual_body_yaw_motion.rs",
    "native/guala_core/src/virtual_material_neuron_genesis.rs",
    "native/guala_core/src/virtual_vestibular_canal.rs",
    "native/guala_core/tests/fixtures/body_manifest_v1.hex",
    "native/guala_core/tests/fixtures/body_state_v1.hex",
    "native/guala_core/tests/fixtures/body_state_v1_successor.hex",
    "native/guala_core/tests/fixtures/canonical_unicode_control_negative.hex",
    "native/guala_core/tests/fixtures/world_observation_v6.hex",
    "native/guala_core/tests/fixtures/world_observation_v6_successor.hex",
    "native/guala_core/tests/organism_codec.rs",
}
MANIFEST_PATH = ROOT / "deploy" / "guala_release_manifest.json"
DEPLOY = (ROOT / "tools" / "deploy_dsf_ai.sh").read_text(encoding="utf-8")
BRIDGE_DEPLOY = (
    ROOT / "tools" / "deploy_gualaloom_bridge.sh"
).read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "dsf_ai_service" / "Dockerfile").read_text(
    encoding="utf-8"
)
BUILDSPEC = (ROOT / "dsf_ai_service" / "buildspec.yml").read_text(
    encoding="utf-8"
)
WEB_DOCKERFILE = (ROOT / "web" / "Dockerfile").read_text(
    encoding="utf-8"
)
WEB_OPERATOR_SOURCES = (
    ROOT
    / "web"
    / "src"
    / "components"
    / "GualaOperatorListeningClient.tsx",
    ROOT / "web" / "src" / "lib" / "operator-observation-contract.ts",
    ROOT / "web" / "src" / "lib" / "operator-observation-view.ts",
    ROOT
    / "web"
    / "src"
    / "app"
    / "admin-console"
    / "guala-listening"
    / "page.tsx",
    ROOT
    / "web"
    / "src"
    / "app"
    / "api"
    / "admin"
    / "guala-listening"
    / "observation"
    / "route.ts",
)


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def _fixture_manifest() -> dict[str, object]:
    return {
        "schema": "guala.reviewed_release_manifest.v1",
        "release_name": "guala-production",
        "runtime_entrypoints": ["service/app.py"],
        "internal_import_roots": ["service"],
        "internal_import_aliases": {},
        "categories": [
            {
                "name": "build_control",
                "archive_prefix": "",
                "reason": "fixture build control",
                "files": ["Dockerfile", "release.json"],
            },
            {
                "name": "runtime_python",
                "archive_prefix": "runtime",
                "reason": "fixture runtime closure",
                "files": [
                    "service/__init__.py",
                    "service/app.py",
                    "service/hearing.py",
                ],
            },
            {
                "name": "migration_control",
                "archive_prefix": "runtime",
                "reason": "fixture one-way migration control",
                "files": [
                    "service/legacy.py",
                    "tools/migrate_guala_physical_state.py",
                ],
            },
            {
                "name": "static_publication",
                "archive_prefix": "runtime",
                "reason": "fixture static release",
                "files": ["service/static/gualaloom.html"],
            },
        ],
        "forbidden_source_patterns": [
            r"(^|/)tests?/",
            r"[.](wav|csv)$",
        ],
    }


def _fixture_repository(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "service" / "static").mkdir(parents=True)
    (repository / "service" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (repository / "service" / "app.py").write_text(
        "from service.hearing import hear\n",
        encoding="utf-8",
    )
    (repository / "service" / "hearing.py").write_text(
        "def hear():\n    return 'physical'\n",
        encoding="utf-8",
    )
    (repository / "service" / "legacy.py").write_text(
        "def read_legacy():\n    return 'historical'\n",
        encoding="utf-8",
    )
    (repository / "tools").mkdir()
    (
        repository / "tools" / "migrate_guala_physical_state.py"
    ).write_text(
        "from service.legacy import read_legacy\n",
        encoding="utf-8",
    )
    (repository / "service" / "static" / "gualaloom.html").write_text(
        "<!doctype html><title>Guala</title>\n",
        encoding="utf-8",
    )
    (repository / "Dockerfile").write_text(
        "FROM scratch\nCOPY runtime/ /app/\n",
        encoding="utf-8",
    )
    manifest_path = repository / "release.json"
    manifest_path.write_bytes(_canonical_json(_fixture_manifest()))
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Release Test")
    _git(repository, "config", "user.email", "release@example.invalid")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "reviewed release")
    return repository, manifest_path


def test_candidate_manifest_is_exact_current_runtime_import_closure() -> None:
    manifest, _ = _read_manifest(MANIFEST_PATH)
    _, by_category = _manifest_entries(manifest)
    resolved = resolve_runtime_closure(
        ROOT,
        manifest["runtime_entrypoints"],
        manifest["internal_import_roots"],
        manifest["internal_import_aliases"],
    )

    assert by_category["runtime_python"] == resolved
    expected_physical_surfaces = {
        f"guala_curriculum/cards/{name}"
        for name in (
            _APPROVED_ALPHABET_ASSET_NAMES
            + _APPROVED_NUMBER_ASSET_NAMES
        )
    }
    assert by_category["physical_curriculum_surfaces"] == expected_physical_surfaces
    for required in (
        "dsf_ai_service/native_production_app.py",
        "dsf_ai_service/candidate_release_rehearsal.py",
        "dsf_ai_service/cold_restore_probe.py",
        "dsf_ai_service/glew_runtime/native_resident_organism.py",
        "dsf_ai_service/substrate/native_organism_binary_store.py",
    ):
        assert required in resolved
    for retired_or_unconnected in (
        "dsf_ai_service/substrate/native_core.py",
        "dsf_ai_service/loom_model/physical_oscillators.py",
        "dsf_ai_service/loom_model/substrate_dna.py",
        "dsf_ai_service/sensory_krimelacks.py",
        "dsf_ai_service/substrate/krimelack.py",
        "dsf_ai_service/glew_runtime/native_materialized_fabric_import.py",
        "dsf_ai_service/substrate/authenticated_legacy_sensory_extractor.py",
        "dsf_ai_service/embodied_reading_http_contract.py",
        "dsf_ai_service/embodied_reading_operation.py",
        "dsf_ai_service/physical_surface_lesson_http_contract.py",
        "dsf_ai_service/substrate/ae_local_receptor.py",
        "dsf_ai_service/substrate/articulatory_consequence_closure.py",
        "dsf_ai_service/substrate/articulatory_exploration_selector.py",
        "dsf_ai_service/substrate/causal_inquiry.py",
        "dsf_ai_service/substrate/causal_inquiry_tutor_authority.py",
        "dsf_ai_service/substrate/causal_mosaic_tapestry.py",
        "dsf_ai_service/substrate/causal_recognition_attention.py",
        "dsf_ai_service/substrate/causal_thing_lived_context.py",
        "dsf_ai_service/substrate/causal_thing_mosaic.py",
        "dsf_ai_service/substrate/causal_thing_mosaic_persistence.py",
        "dsf_ai_service/substrate/causal_thing_reciprocal_mosaic.py",
        "dsf_ai_service/substrate/causal_thing_sensory_expansion.py",
        "dsf_ai_service/substrate/custodied_thing_encounter.py",
        "dsf_ai_service/substrate/custody_native_tutoring_action.py",
        "dsf_ai_service/substrate/custody_native_tutoring_curriculum.py",
        "dsf_ai_service/substrate/durable_sensed_consequence.py",
        "dsf_ai_service/substrate/embodied_glyph_tutoring.py",
        "dsf_ai_service/substrate/embodied_reading_lesson_controller.py",
        "dsf_ai_service/substrate/live_ae_neurochemical_flow.py",
        "dsf_ai_service/substrate/neurochemical_flow.py",
        "dsf_ai_service/substrate/organism_dream_wake_weave.py",
        "dsf_ai_service/substrate/organism_ordered_lived_experience.py",
        "dsf_ai_service/substrate/owner_scoped_persistence.py",
        "dsf_ai_service/substrate/whole_organism_episode.py",
        "dsf_ai_service/substrate/whole_organism_neurochemical_mount.py",
        "dsf_ai_service/substrate/whole_organism_neuron_population.py",
        "dsf_ai_service/substrate/whole_organism_observation_projection.py",
        "dsf_ai_service/substrate/whole_organism_recovery_state.py",
        "dsf_ai_service/substrate/whole_organism_reflection_monitor.py",
        "dsf_ai_service/substrate/whole_organism_structural_perturbation.py",
        "dsf_ai_service/substrate/whole_organism_thing_mosaic_learning.py",
        "dsf_ai_service/v4/gualaloom_v5_engine.py",
        "dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py",
        "dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py",
        "dsf_ai_service/loom_model/binding_atlas.py",
        "dsf_ai_service/loom_model/resonant_chi.py",
        "dsf_ai_service/substrate/hemisphere_cognition.py",
        "dsf_ai_service/substrate/retired_legacy_cognition.py",
        "dsf_ai_service/substrate/lived_conversation_learning.py",
        "dsf_ai_service/loom_model/embryo.py",
        "dsf_ai_service/substrate/spike_bus.py",
        "dsf_ai_service/substrate/causal_organism_growth.py",
        "dsf_ai_service/glew_runtime/language.py",
        "dsf_ai_service/glew_runtime/story_chemistry.py",
        "dsf_ai_service/glew_runtime/story_global_uf_basin.py",
        "dsf_ai_service/glew_runtime/story_native_replay.py",
        "dsf_ai_service/glew_runtime/typed_language_native_replay.py",
    ):
        assert retired_or_unconnected not in resolved


def test_native_core_manifest_is_exact_and_staged_crate_tests(
    tmp_path: Path,
) -> None:
    manifest, _ = _read_manifest(MANIFEST_PATH)
    _, by_category = _manifest_entries(manifest)

    assert by_category["native_core"] == NATIVE_CORE_SOURCES
    for retired_native_owner_path in (
        "native/guala_core/src/organism/generation_store.rs",
        "native/guala_core/src/organism/owner_boot.rs",
    ):
        assert retired_native_owner_path not in by_category["native_core"]
    organism_source = (
        ROOT / "native/guala_core/src/organism.rs"
    ).read_text(encoding="utf-8")
    assert "pub mod generation_store;" not in organism_source
    assert "pub mod owner_boot;" not in organism_source

    staged_crate = tmp_path / "reviewed-native" / "native" / "guala_core"
    for relative in sorted(NATIVE_CORE_SOURCES):
        source = ROOT / relative
        destination = staged_crate / Path(relative).relative_to(
            "native/guala_core"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    completed = subprocess.run(
        ["cargo", "test", "--locked"],
        cwd=staged_crate,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_retired_migration_control_is_absent_from_release() -> None:
    manifest, _ = _read_manifest(MANIFEST_PATH)
    _, by_category = _manifest_entries(manifest)
    runtime = resolve_runtime_closure(
        ROOT,
        manifest["runtime_entrypoints"],
        manifest["internal_import_roots"],
        manifest["internal_import_aliases"],
    )
    assert "migration_control" not in by_category
    assert "dsf_ai_service/cold_restore_probe.py" in runtime
    packaged = set().union(*by_category.values())
    for retired_reader in (
        "dsf_ai_service/loom_model/binding_atlas.py",
        "dsf_ai_service/loom_model/embryo.py",
        "dsf_ai_service/substrate/causal_organism_growth.py",
        "dsf_ai_service/substrate/retired_legacy_cognition.py",
        "dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py",
        "tools/guala_legacy_organism_graph_reader.py",
        "tools/migrate_guala_physical_state.py",
    ):
        assert retired_reader not in packaged
        assert retired_reader not in runtime
    assert "dsf_ai_service/substrate/spike_bus.py" not in runtime
    assert "dsf_ai_service/substrate/legacy_learned_state_gate.py" not in packaged


def test_runtime_manifest_refresh_is_deterministic_and_review_only() -> None:
    first = render_runtime_manifest(
        root=ROOT,
        manifest_path=MANIFEST_PATH,
    )
    second = render_runtime_manifest(
        root=ROOT,
        manifest_path=MANIFEST_PATH,
    )

    assert _canonical_json(first) == _canonical_json(second)
    assert _canonical_json(first) == MANIFEST_PATH.read_bytes()


def test_manifest_renderer_refreshes_runtime_and_migration_closures(
    tmp_path: Path,
) -> None:
    repository, manifest_path = _fixture_repository(tmp_path)
    stale = json.loads(manifest_path.read_text(encoding="utf-8"))
    for category in stale["categories"]:
        if category["name"] == "runtime_python":
            category["files"].remove("service/hearing.py")
        if category["name"] == "migration_control":
            category["files"].remove("service/legacy.py")
    manifest_path.write_bytes(_canonical_json(stale))

    rendered = render_runtime_manifest(
        root=repository,
        manifest_path=manifest_path,
    )
    _, by_category = _manifest_entries(rendered)

    assert by_category["runtime_python"] == {
        "service/__init__.py",
        "service/app.py",
        "service/hearing.py",
    }
    assert by_category["migration_control"] == {
        "service/legacy.py",
        "tools/migrate_guala_physical_state.py",
    }


def test_manifest_static_set_and_forbidden_release_classes_are_exact() -> None:
    manifest, _ = _read_manifest(MANIFEST_PATH)
    entries, by_category = _manifest_entries(manifest)

    assert by_category["static_publication"] == {
        "dsf_ai_service/static/Guala_Talking_Bust_No_Bow_Transparent.png",
        "dsf_ai_service/static/guala-brain-foundation-v1.png",
        "dsf_ai_service/static/gualaloom.html",
        "dsf_ai_service/static/gualaloom-rich-room-v3.png",
        "dsf_ai_service/static/loomscan.html",
        "dsf_ai_service/static/legal.html",
        "dsf_ai_service/static/style.css",
    }
    sources = {item["source_path"] for item in entries}
    forbidden_fragments = (
        "/tests/",
        "/docs/",
        "/backups/",
        "/fixtures/",
        "/models/",
        "/datasets/",
    )
    allowed_test_sources = {
        "native/guala_core/tests/organism_codec.rs",
        "native/guala_core/tests/fixtures/body_manifest_v1.hex",
        "native/guala_core/tests/fixtures/body_state_v1.hex",
        "native/guala_core/tests/fixtures/body_state_v1_successor.hex",
        "native/guala_core/tests/fixtures/canonical_unicode_control_negative.hex",
        "native/guala_core/tests/fixtures/world_observation_v6.hex",
        "native/guala_core/tests/fixtures/world_observation_v6_successor.hex",
    }
    assert {
        source for source in sources if "/tests/" in f"/{source}"
    } == allowed_test_sources
    expected_tutor_media = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "guala_curriculum" / "audio").glob("*.wav")
    } | {"guala_curriculum/card_experience_manifest-v1.json"}
    assert by_category["candidate_rehearsal_pressure"] == expected_tutor_media
    expected_song_media = {
        "guala_curriculum/songs/ATTRIBUTION.md",
        "guala_curriculum/songs/alphabet-song-cc-by-sa-3.0-v1.wav",
        "guala_curriculum/songs/count-down-ten-to-one-v1.wav",
        "guala_curriculum/songs/count-up-one-to-ten-v1.wav",
        "guala_curriculum/songs/song_experience_manifest-v1.json",
    }
    assert by_category["physical_curriculum_songs"] == expected_song_media
    allowed_wav_sources = {
        *(source for source in expected_tutor_media if source.endswith(".wav")),
        *(source for source in expected_song_media if source.endswith(".wav")),
    }
    assert not any(
        (
            source not in allowed_test_sources
            and fragment in f"/{source}"
        )
        or (
            source.endswith((".wav", ".mp3", ".csv"))
            and source not in allowed_wav_sources
        )
        for source in sources
        for fragment in forbidden_fragments
    )


def test_web_operator_sources_are_owned_by_the_separate_web_build() -> None:
    manifest, _ = _read_manifest(MANIFEST_PATH)
    entries, _ = _manifest_entries(manifest)
    release_sources = {item["source_path"] for item in entries}

    assert "COPY web/src ./src" in WEB_DOCKERFILE
    for source in WEB_OPERATOR_SOURCES:
        assert source.is_file()
        relative = source.relative_to(ROOT).as_posix()
        assert relative.startswith("web/src/")
        assert relative not in release_sources


def test_production_build_uses_only_verified_staged_context() -> None:
    assert "COPY runtime/ /app/" in DOCKERFILE
    assert "COPY dsf_ai_service/" not in DOCKERFILE
    assert "COPY uf_core/" not in DOCKERFILE
    assert "COPY ses_core/" not in DOCKERFILE
    assert "verify-context --context ." in BUILDSPEC
    assert (
        "COPY native/guala_core/tests/organism_codec.rs "
        "/build/guala_core/tests/organism_codec.rs"
        in DOCKERFILE
    )
    assert (
        "COPY native/guala_core/tests/fixtures/ "
        "/build/guala_core/tests/fixtures/"
        in DOCKERFILE
    )
    assert "RUN cd /build/guala_core && cargo test --locked" in DOCKERFILE
    assert "--skip organism::" not in DOCKERFILE
    assert "cargo test --locked" not in BUILDSPEC
    assert "docker build --file dsf_ai_service/Dockerfile" in BUILDSPEC
    assert "tools/package_guala_release.py package" in DEPLOY
    assert 'RELEASE_MANIFEST="deploy/guala_release_manifest.json"' in DEPLOY
    assert "git archive" not in DEPLOY
    assert "git archive" not in BRIDGE_DEPLOY
    assert "zip -r" not in DEPLOY


def test_backend_deploy_has_no_static_publication_authority() -> None:
    for forbidden in (
        "aws s3api list-objects-v2",
        "aws s3api head-object",
        "--checksum-algorithm SHA256",
        "--checksum-mode ENABLED",
        "ChecksumSHA256",
        "aws s3api delete-objects",
        "actual != expected",
        '"physical_curriculum_surfaces", "static_publication"',
        "aws cloudfront update-distribution",
        "aws cloudfront wait distribution-deployed",
        'config[\"DefaultRootObject\"] = \"gualaloom.html\"',
        'get(\"DefaultRootObject\") != \"gualaloom.html\"',
        '--paths "/*"',
    ):
        assert forbidden not in DEPLOY
    assert "aws s3 sync" not in DEPLOY
    assert '"cards/" + basename' not in DEPLOY


def test_deterministic_packager_records_commit_hashes_and_metadata(
    tmp_path: Path,
) -> None:
    repository, manifest = _fixture_repository(tmp_path)
    first_stage = tmp_path / "first-stage"
    first_zip = tmp_path / "first.zip"
    second_stage = tmp_path / "second-stage"
    second_zip = tmp_path / "second.zip"

    first = package_release(
        root=repository,
        manifest_path=manifest,
        stage=first_stage,
        zip_path=first_zip,
    )
    second = package_release(
        root=repository,
        manifest_path=manifest,
        stage=second_stage,
        zip_path=second_zip,
    )

    assert first_zip.read_bytes() == second_zip.read_bytes()
    assert first["archive_sha256"] == second["archive_sha256"]
    receipt = verify_context(first_stage)
    assert receipt["git_commit"] == subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert receipt["source_file_count"] == 8
    assert all(len(item["sha256"]) == 64 for item in receipt["files"])
    assert verify_archive(first_zip) == receipt
    with zipfile.ZipFile(first_zip) as archive:
        assert archive.comment == b""
        assert archive.namelist() == sorted(archive.namelist())
        assert GENERATED_RECEIPT in archive.namelist()
        for info in archive.infolist():
            assert info.date_time == CANONICAL_ZIP_TIMESTAMP
            assert info.extra == b""
            assert info.create_system == 3
            assert info.external_attr >> 16 == CANONICAL_FILE_MODE


def test_packager_refuses_dirty_and_untracked_source(tmp_path: Path) -> None:
    repository, manifest = _fixture_repository(tmp_path)
    (repository / "untracked.wav").write_bytes(b"not reviewed")

    with pytest.raises(
        ReleasePackagingError,
        match="dirty or has untracked",
    ):
        package_release(
            root=repository,
            manifest_path=manifest,
            stage=tmp_path / "stage",
            zip_path=tmp_path / "release.zip",
        )


def test_packager_refuses_forbidden_manifest_and_unreviewed_context_file(
    tmp_path: Path,
) -> None:
    repository, manifest_path = _fixture_repository(tmp_path)
    forbidden = repository / "labeled.wav"
    forbidden.write_bytes(b"labeled corpus must not ship")
    manifest = _fixture_manifest()
    build = next(
        item for item in manifest["categories"]
        if item["name"] == "build_control"
    )
    build["files"].append("labeled.wav")
    manifest_path.write_bytes(_canonical_json(manifest))
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "invalid forbidden release input")
    with pytest.raises(ReleasePackagingError, match="forbidden pattern"):
        package_release(
            root=repository,
            manifest_path=manifest_path,
            stage=tmp_path / "forbidden-stage",
            zip_path=tmp_path / "forbidden.zip",
        )

    forbidden.unlink()
    manifest_path.write_bytes(_canonical_json(_fixture_manifest()))
    _git(repository, "add", "-A")
    _git(repository, "commit", "-qm", "restore valid release")
    stage = tmp_path / "valid-stage"
    package_release(
        root=repository,
        manifest_path=manifest_path,
        stage=stage,
        zip_path=tmp_path / "valid.zip",
    )
    (stage / "unreviewed.py").write_text("pass\n", encoding="utf-8")
    with pytest.raises(ReleasePackagingError, match="unreviewed paths"):
        verify_context(stage)


def test_packager_refuses_manifest_drift_and_symlink(
    tmp_path: Path,
) -> None:
    repository, manifest_path = _fixture_repository(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime = next(
        item for item in manifest["categories"]
        if item["name"] == "runtime_python"
    )
    runtime["files"].remove("service/hearing.py")
    manifest_path.write_bytes(_canonical_json(manifest))
    _git(repository, "add", "release.json")
    _git(repository, "commit", "-qm", "invalid reviewed drift")

    with pytest.raises(ReleasePackagingError, match="runtime manifest drift"):
        package_release(
            root=repository,
            manifest_path=manifest_path,
            stage=tmp_path / "drift-stage",
            zip_path=tmp_path / "drift.zip",
        )

    os.symlink("Dockerfile", repository / "build-link")
    manifest = _fixture_manifest()
    build = next(
        item for item in manifest["categories"]
        if item["name"] == "build_control"
    )
    build["files"].append("build-link")
    manifest_path.write_bytes(_canonical_json(manifest))
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "invalid reviewed symlink")

    with pytest.raises(ReleasePackagingError, match="symlink is forbidden"):
        package_release(
            root=repository,
            manifest_path=manifest_path,
            stage=tmp_path / "link-stage",
            zip_path=tmp_path / "link.zip",
        )


def test_packager_refuses_duplicate_escape_and_noncanonical_metadata(
    tmp_path: Path,
) -> None:
    repository, manifest_path = _fixture_repository(tmp_path)
    manifest = _fixture_manifest()
    build = next(
        item for item in manifest["categories"]
        if item["name"] == "build_control"
    )
    build["files"].append("Dockerfile")
    manifest_path.write_bytes(_canonical_json(manifest))
    _git(repository, "add", "release.json")
    _git(repository, "commit", "-qm", "invalid duplicate")
    with pytest.raises(ReleasePackagingError, match="duplicate reviewed"):
        package_release(
            root=repository,
            manifest_path=manifest_path,
            stage=tmp_path / "duplicate-stage",
            zip_path=tmp_path / "duplicate.zip",
        )

    manifest = _fixture_manifest()
    build = next(
        item for item in manifest["categories"]
        if item["name"] == "build_control"
    )
    build["files"].append("../outside")
    manifest_path.write_bytes(_canonical_json(manifest))
    _git(repository, "add", "release.json")
    _git(repository, "commit", "-qm", "invalid path escape")
    with pytest.raises(ReleasePackagingError, match="canonical relative"):
        package_release(
            root=repository,
            manifest_path=manifest_path,
            stage=tmp_path / "escape-stage",
            zip_path=tmp_path / "escape.zip",
        )

    noncanonical = tmp_path / "noncanonical.zip"
    with zipfile.ZipFile(noncanonical, "w") as archive:
        info = zipfile.ZipInfo(
            GENERATED_RECEIPT,
            (2026, 7, 28, 0, 0, 0),
        )
        archive.writestr(info, b"{}")
    with pytest.raises(
        ReleasePackagingError,
        match="non-canonical archive metadata",
    ):
        verify_archive(noncanonical)

    duplicate_json = tmp_path / "duplicate.json"
    duplicate_json.write_text(
        '{"schema":"x","schema":"y"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ReleasePackagingError, match="duplicate JSON key"):
        _read_manifest(duplicate_json)
