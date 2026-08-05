"""Frozen walk-up for a cochlear relational-field familiarity law.

This is a read-only candidate-law probe, not a production recognizer.  It
uses a new corpus (`go`, `left`, `right`) and globally source-disjoint
speakers.  Five recordings per causal THING enter through authenticated W1
physical tutoring; two more per THING are held out until the law is frozen.

The law never compares PCM, firing IDs, segments, words, or speakers.  For
every ear, pressure/phase component, explicit D/M/R/U/C/P/B field, and
unordered cochlear-channel pair, it compares seven exact trajectory facts:
net displacement, excursion, total path, positive path, negative path, first
peak time, and first trough time.  These pairwise directions form a
cochlear relational field.  Canonical L6 selects relations recurrent across
independent experiences of one causally tutored THING.  Relations recurrent
under multiple divergent THINGs become quiescent.  Query applies canonical
L6 to each remaining exact relation population; zero locks is unknown and
multiple locks is ambiguous.

The quotient discards absolute magnitude and within-path samples after the
seven exact facts are derived.  Complete authenticated D/M/R/U/C/P/B
occurrences remain in the W1 receptor settlement and are named by every
experience receipt.  The quotient is therefore a declared diagnostic
projection, never a replacement for the full field.
"""

from __future__ import annotations

import hashlib
import io
import json
import wave
import zipfile
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaic,
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
)
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority as _physical_authority,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    CorpusItem,
    _select_corpus,
)
from tools.probe_auditory_thing_local_familiarity import (
    AUTHORITY_KEY,
    OBJECT_IDS,
    _custody,
    _execute,
    _world,
)
from tools.probe_vtvr_causal_thing_familiarity import (
    ARCHIVE_PATH,
    _archive_sha256,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)


SCHEMA = "guala.audit.auditory_thing_relational_field_law.v1"
WORDS = ("go", "left", "right")
TRAINING_SPEAKERS_PER_THING = 5
HELD_OUT_SPEAKERS_PER_THING = 2
FUNCTIONALS = (
    "net_displacement",
    "excursion",
    "total_path",
    "positive_path",
    "negative_path",
    "first_peak_time",
    "first_trough_time",
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _root(schema: str, values: object) -> str:
    return _digest({"schema": schema, "values": values})


def _direction(left: Fraction | int, right: Fraction | int) -> int:
    return (right > left) - (right < left)


def _pcm(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != 16_000
            or source.getcomptype() != "NONE"
        ):
            raise ValueError("relational-field corpus left PCM custody")
        result = source.readframes(source.getnframes())
    if not result or len(result) % 2:
        raise ValueError("relational-field PCM extent changed")
    return result


@dataclass(frozen=True, order=True, slots=True)
class RelationalFieldFact:
    ear_id: str
    component_kind: str
    field_name: str
    functional: str
    lower_channel: int
    upper_channel: int
    direction: int

    def record(self) -> list[object]:
        return [
            self.ear_id,
            self.component_kind,
            self.field_name,
            self.functional,
            self.lower_channel,
            self.upper_channel,
            self.direction,
        ]


def _trajectory_facts(
    values: tuple[tuple[int, Fraction], ...],
) -> dict[str, Fraction | int]:
    if len(values) < 2:
        raise ValueError("cochlear trajectory lacks two physical gates")
    ordered = tuple(sorted(values))
    samples = tuple(value for _index, value in ordered)
    deltas = tuple(
        current - prior
        for prior, current in zip(samples, samples[1:])
    )
    maximum = max(samples)
    minimum = min(samples)
    return {
        "net_displacement": samples[-1] - samples[0],
        "excursion": maximum - minimum,
        "total_path": sum((abs(value) for value in deltas), Fraction(0)),
        "positive_path": sum(
            (value for value in deltas if value > 0),
            Fraction(0),
        ),
        "negative_path": sum(
            (-value for value in deltas if value < 0),
            Fraction(0),
        ),
        "first_peak_time": next(
            index for index, value in ordered if value == maximum
        ),
        "first_trough_time": next(
            index for index, value in ordered if value == minimum
        ),
    }


def relational_field(
    settlement: W1BinauralReceptorSettlement,
) -> frozenset[RelationalFieldFact]:
    settlement.verify()
    result: set[RelationalFieldFact] = set()
    for ear in settlement.ears:
        by_channel = {
            channel: tuple(
                sorted(
                    (
                        occurrence
                        for occurrence in ear.experience.occurrences
                        if occurrence.receptor.cochlear_index == channel
                    ),
                    key=lambda value: (
                        value.source_index,
                        value.receptor.winding_direction,
                    ),
                )
            )
            for channel in range(16)
        }
        for component_kind in ("pressure", "phase"):
            for field_name in DSF_FIELD_ORDER:
                facts: dict[int, dict[str, Fraction | int]] = {}
                for channel, occurrences in by_channel.items():
                    values = tuple(
                        (
                            occurrence.source_index,
                            dict(
                                occurrence.pressure_fields
                                if component_kind == "pressure"
                                else occurrence.phase_fields
                            )[field_name],
                        )
                        for occurrence in occurrences
                    )
                    if len(values) >= 2:
                        facts[channel] = _trajectory_facts(values)
                for lower, upper in combinations(sorted(facts), 2):
                    for functional in FUNCTIONALS:
                        result.add(RelationalFieldFact(
                            ear_id=ear.ear_id,
                            component_kind=component_kind,
                            field_name=field_name,
                            functional=functional,
                            lower_channel=lower,
                            upper_channel=upper,
                            direction=_direction(
                                facts[lower][functional],
                                facts[upper][functional],
                            ),
                        ))
    if not result:
        raise ValueError("relational-field experience is empty")
    return frozenset(result)


def _corpus(
    archive: zipfile.ZipFile,
) -> dict[str, tuple[CorpusItem, ...]]:
    all_items = _select_corpus(archive)
    result = {
        word: tuple(
            value
            for value in all_items
            if value.oracle_command == word
        )[:TRAINING_SPEAKERS_PER_THING + HELD_OUT_SPEAKERS_PER_THING]
        for word in WORDS
    }
    if (
        any(
            len(values)
            != TRAINING_SPEAKERS_PER_THING
            + HELD_OUT_SPEAKERS_PER_THING
            for values in result.values()
        )
        or len({
            value.speaker_id
            for values in result.values()
            for value in values
        })
        != sum(len(values) for values in result.values())
    ):
        raise RuntimeError("relational-field corpus is not source-disjoint")
    return result


def _recurrent(
    populations: tuple[frozenset[RelationalFieldFact], ...],
) -> frozenset[RelationalFieldFact]:
    counts = Counter(
        relation
        for population in populations
        for relation in population
    )
    return frozenset(
        relation
        for relation, matching in counts.items()
        if canonical_l6_direction(
            dimensions=len(populations),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
    )


def _settle_query(
    *,
    population: frozenset[RelationalFieldFact],
    memories: dict[str, frozenset[RelationalFieldFact]],
) -> tuple[str, tuple[str, ...], list[dict[str, object]]]:
    relations = []
    locked = []
    for thing_id in sorted(memories):
        memory = memories[thing_id]
        matching = len(memory.intersection(population))
        direction = canonical_l6_direction(
            dimensions=len(memory),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        relations.append({
            "dimensions": direction.dimensions,
            "effective_dimensions": direction.effective_dimensions,
            "knee": direction.knee,
            "locked": direction.locked,
            "matching_non_null": direction.matching_non_null,
            "thing_id": thing_id,
        })
        if memory and direction.locked:
            locked.append(thing_id)
    state = (
        "resolved"
        if len(locked) == 1
        else "ambiguous"
        if locked
        else "unknown"
    )
    return state, tuple(locked), relations


def run_probe() -> dict[str, object]:
    archive_sha256 = _archive_sha256(ARCHIVE_PATH)
    if archive_sha256 != ARCHIVE_SHA256:
        raise RuntimeError("authenticated speech archive changed")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        corpus = _corpus(archive)
        pcm_by_member = {
            item.archive_member: _pcm(archive.read(item.archive_member))
            for values in corpus.values()
            for item in values
        }

    world = _world()
    physical = _physical_authority(world)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=EVIDENCE_KEY
    )
    partition_authority = CustodiedW1ContactThingEncounterAuthority(
        authority_key=AUTHORITY_KEY + b":relational-field",
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    thing_owner = CausalThingMosaicOwner(
        authority_key=AUTHORITY_KEY + b":relational-field",
        profile=CausalThingMosaicProfile.create(
            profile_id="auditory-relational-field-things-v1",
            max_mosaics=len(WORDS),
            max_partitions_per_mosaic=(
                TRAINING_SPEAKERS_PER_THING + 1
            ),
            max_roots_per_partition=256,
            max_routes=65_536,
            max_state_bytes=512 * 1024 * 1024,
        ),
        partition_authority=partition_authority,
    )
    training: dict[
        str,
        list[tuple[CorpusItem, frozenset[RelationalFieldFact]]],
    ] = {word: [] for word in WORDS}
    mosaics: dict[str, CausalThingMosaic] = {}
    action_ordinal = 0
    custody_ordinal = 0

    for thing_ordinal, (word, object_id) in enumerate(
        zip(WORDS, OBJECT_IDS, strict=True),
        start=1,
    ):
        approach_x = 1_000 * thing_ordinal
        if thing_ordinal > 1:
            for waypoint in (
                PositionMM(1_000, 2_000, 0),
                PositionMM(approach_x, 2_000, 0),
                PositionMM(approach_x, 1_000, 0),
            ):
                action_ordinal += 1
                _execute(
                    world,
                    MoveCommand(PoseMM(waypoint, 0)),
                    causal_ordinal=10_000 + action_ordinal,
                )
        action_ordinal += 1
        picked = _execute(
            world,
            PickCommand(object_id),
            causal_ordinal=10_000 + action_ordinal,
        )
        custody_ordinal += 1
        pick_custody = _custody(
            source_mount=physical.mount_action_outcome(picked),
            execution=picked,
            ordinal=10_000 + custody_ordinal,
        )
        prior = partition_authority.partition_from_custody(
            custody_authority=pick_custody,
            capability=pick_custody.issue_child(
                THING_MOSAIC_CONSUMER_ID
            ),
        )
        mosaic = thing_owner.admit(prior)

        for item in corpus[word][:TRAINING_SPEAKERS_PER_THING]:
            execution, mount = _external_mount(
                world,
                physical,
                pcm_by_member[item.archive_member],
            )
            custody_ordinal += 1
            vocal_custody: SettledExperienceCustodyAuthority = _custody(
                source_mount=mount,
                execution=execution,
                ordinal=10_000 + custody_ordinal,
            )
            prior = partition_authority.partition_from_custody(
                custody_authority=vocal_custody,
                capability=vocal_custody.issue_child(
                    THING_MOSAIC_CONSUMER_ID
                ),
                prior=prior,
            )
            mosaic = thing_owner.admit(prior)
            settlement = mount.binaural_receptor_settlement
            if (
                settlement.upstream_causal_settlement_receipt_sha256
                != prior.settlement_receipt_sha256
            ):
                raise ValueError(
                    "relational field left physical THING custody"
                )
            training[word].append((
                item,
                relational_field(settlement),
            ))
        mosaics[word] = mosaic

        if thing_ordinal < len(WORDS):
            action_ordinal += 1
            _execute(
                world,
                PlaceCommand(
                    object_id,
                    PositionMM(approach_x - 500, 1_000, 0),
                ),
                causal_ordinal=10_000 + action_ordinal,
            )

    recurrent_by_thing = {
        mosaics[word].thing_id: _recurrent(tuple(
            population
            for _item, population in training[word]
        ))
        for word in WORDS
    }
    shared = frozenset(
        relation
        for memories in recurrent_by_thing.values()
        for relation in memories
        if sum(
            relation in other
            for other in recurrent_by_thing.values()
        ) > 1
    )
    memories = {
        thing_id: recurrent.difference(shared)
        for thing_id, recurrent in recurrent_by_thing.items()
    }

    held_out = []
    correct = 0
    for word in WORDS:
        expected = mosaics[word].thing_id
        for item in corpus[word][TRAINING_SPEAKERS_PER_THING:]:
            _execution, mount = _external_mount(
                world,
                physical,
                pcm_by_member[item.archive_member],
            )
            population = relational_field(
                mount.binaural_receptor_settlement
            )
            state, locked, relations = _settle_query(
                population=population,
                memories=memories,
            )
            released = locked[0] if state == "resolved" else None
            passed = released == expected
            correct += int(passed)
            held_out.append({
                "archive_member": item.archive_member,
                "expected_thing_id": expected,
                "locked_thing_ids": list(locked),
                "oracle_speaker": item.speaker_id,
                "oracle_word": word,
                "passed": passed,
                "relation_population_count": len(population),
                "relation_population_root_sha256": _root(
                    "guala.audit.relational_field_population.v1",
                    [value.record() for value in sorted(population)],
                ),
                "relations": relations,
                "released_thing_id": released,
                "state": state,
            })

    memory_records = [
        {
            "fissioned_relation_count": (
                len(recurrent_by_thing[thing_id]) - len(memory)
            ),
            "memory_relation_count": len(memory),
            "memory_relation_root_sha256": _root(
                "guala.audit.relational_field_memory.v1",
                [value.record() for value in sorted(memory)],
            ),
            "recurrent_relation_count": len(
                recurrent_by_thing[thing_id]
            ),
            "thing_id": thing_id,
        }
        for thing_id, memory in sorted(memories.items())
    ]
    report = {
        "archive_sha256": archive_sha256,
        "claim_allowed": correct == len(held_out),
        "correct": correct,
        "declared_quotient_loss": (
            "absolute magnitude and within-path samples after exact "
            "trajectory facts are derived"
        ),
        "field_order": list(DSF_FIELD_ORDER),
        "functionals": list(FUNCTIONALS),
        "held_out": held_out,
        "held_out_count": len(held_out),
        "held_out_speakers_per_thing": HELD_OUT_SPEAKERS_PER_THING,
        "learning_boundary_received_speaker_ids": False,
        "learning_boundary_received_words": False,
        "memory_records": memory_records,
        "oracle_thing_map": {
            mosaics[word].thing_id: word for word in WORDS
        },
        "physical_custody_received_by_law": True,
        "raw_pcm_retained_bytes": 0,
        "recognition_governance": (
            "canonical L6 over exact recurrent and causally fissioned "
            "cochlear relational-field facts"
        ),
        "schema": SCHEMA,
        "shared_quiescent_relation_count": len(shared),
        "source_disjoint_speaker_count": len({
            item.speaker_id
            for values in corpus.values()
            for item in values
        }),
        "training_records": [
            {
                "archive_member_for_oracle_audit": item.archive_member,
                "oracle_speaker_for_audit": item.speaker_id,
                "oracle_word_for_audit": word,
                "relation_population_count": len(population),
                "relation_population_root_sha256": _root(
                    "guala.audit.relational_field_population.v1",
                    [value.record() for value in sorted(population)],
                ),
                "thing_id": mosaics[word].thing_id,
            }
            for word in WORDS
            for item, population in training[word]
        ],
        "training_speakers_per_thing": TRAINING_SPEAKERS_PER_THING,
        "words_used_by_law": False,
    }
    return report | {"authority_receipt_sha256": _digest(report)}


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
