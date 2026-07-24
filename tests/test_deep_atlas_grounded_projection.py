"""Exact deep-atlas speech projection and cache-boundary proofs."""

from dsf_ai_service.substrate.deep_atlas import _CoOccurrenceMap
from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala,
    LanguageKrimelack,
)


class _CountingDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_calls = 0

    def items(self):
        self.items_calls += 1
        return super().items()


def _install_speakable_word(guala, section, word):
    mode = len(guala.sections[section].modes)
    guala.sections[section].modes.append((0, 0, word))
    guala._word_to_emission_sections.setdefault(
        word.lower(), []).append((section, mode, word))
    guala._grounded_emission_motifs = {}
    return mode


def _legacy_grounded_scan(guala, seed_word):
    """The pre-correction loop, retained only as an equivalence oracle."""
    transducer = LanguageKrimelack()
    transducer.transduce(seed_word)
    exclude = {seed_word.lower()}
    seen = set()
    output = []
    for entry in guala.deep_atlas.entries.get(transducer.winding, []):
        strength = entry.get("strength", 0.0)
        if strength <= 0.0:
            continue
        if entry.get("source_path") == "reorganize_hypothesis":
            continue
        for section, motif_weights in entry.get(
                "co_occurrence", {}).items():
            section_object = guala.sections.get(section)
            if section_object is None:
                continue
            for motif_key, weight in motif_weights.items():
                motif = int(motif_key)
                if motif >= len(section_object.modes):
                    continue
                word = section_object.modes[motif][2]
                if not word:
                    continue
                word_lower = word.lower()
                if word_lower in exclude or word_lower in seen:
                    continue
                if word_lower not in guala._word_to_emission_sections:
                    continue
                seen.add(word_lower)
                output.append(
                    (word, weight * strength, section, motif))
    return output


def test_projection_is_exact_and_shared_table_scans_once(monkeypatch):
    monkeypatch.setenv("REQUIRE_GROUNDED_SPEECH", "1")
    guala = Guala()
    try:
        section = "subject"
        seed = "hello"
        _install_speakable_word(guala, section, seed)
        beta = _install_speakable_word(guala, section, "beta")
        alpha = _install_speakable_word(guala, section, "alpha")

        raw = _CountingDict()
        raw["999999"] = 0.99
        raw[str(beta)] = 0.40
        raw[str(alpha)] = 0.30
        registry = {"shared-table": raw}
        first = _CoOccurrenceMap(
            registry, references={section: "shared-table"})
        second = _CoOccurrenceMap(
            registry, references={section: "shared-table"})

        transducer = LanguageKrimelack()
        transducer.transduce(seed)
        guala.deep_atlas.entries[transducer.winding] = [
            {
                "strength": 0.5,
                "source_path": "survival",
                "co_occurrence": first,
            },
            {
                "strength": 0.9,
                "source_path": "survival",
                "co_occurrence": second,
            },
        ]

        expected = _legacy_grounded_scan(guala, seed)
        raw.items_calls = 0
        actual = guala._deep_atlas_neighbor_candidates(seed)

        assert actual == expected
        assert [item[0] for item in actual] == ["beta", "alpha"]
        assert raw.items_calls == 1
    finally:
        guala.shutdown()


def test_copy_on_write_table_is_never_served_from_stale_projection(
        monkeypatch):
    monkeypatch.setenv("REQUIRE_GROUNDED_SPEECH", "1")
    guala = Guala()
    try:
        section = "subject"
        alpha = _install_speakable_word(guala, section, "alpha")
        beta = _install_speakable_word(guala, section, "beta")
        raw = _CountingDict({str(alpha): 0.25})
        co_occurrence = _CoOccurrenceMap(
            {"shared-table": raw},
            references={section: "shared-table"},
        )

        assert guala._grounded_deep_atlas_items(
            co_occurrence, section) == ((alpha, 0.25),)
        assert raw.items_calls == 1

        co_occurrence[section][str(beta)] = 0.75
        assert guala._grounded_deep_atlas_items(
            co_occurrence, section) == (
                (alpha, 0.25),
                (beta, 0.75),
            )
        # The second raw iteration is the copy-on-write detach itself.  The
        # subsequent projection reads the new owned dictionary, not the
        # cached immutable projection.
        assert raw.items_calls == 2
    finally:
        guala.shutdown()


def test_ungrounded_motif_remains_absent_from_projection(monkeypatch):
    monkeypatch.setenv("REQUIRE_GROUNDED_SPEECH", "1")
    guala = Guala()
    try:
        section = "subject"
        grounded = _install_speakable_word(guala, section, "grounded")
        ungrounded = len(guala.sections[section].modes)
        guala.sections[section].modes.append((0, 0, "ungrounded"))
        co_occurrence = _CoOccurrenceMap(
            {},
            values={
                section: {
                    str(ungrounded): 0.90,
                    str(grounded): 0.10,
                }
            },
        )

        assert guala._grounded_deep_atlas_items(
            co_occurrence, section) == ((grounded, 0.10),)
    finally:
        guala.shutdown()


def test_global_word_authority_allows_same_word_in_another_section(
        monkeypatch):
    """Match the established gate: word authority is global, not local."""
    monkeypatch.setenv("REQUIRE_GROUNDED_SPEECH", "1")
    guala = Guala()
    try:
        authorized_mode = _install_speakable_word(
            guala, "object", "sharedword")
        assert authorized_mode >= 0

        subject_mode = len(guala.sections["subject"].modes)
        guala.sections["subject"].modes.append((0, 0, "sharedword"))
        co_occurrence = _CoOccurrenceMap(
            {},
            values={
                "subject": {
                    str(subject_mode): 0.60,
                }
            },
        )

        guala._refresh_grounded_emission_motif_index()
        assert guala._grounded_deep_atlas_items(
            co_occurrence, "subject") == ((subject_mode, 0.60),)
    finally:
        guala.shutdown()
