"""Deterministic multiword continuation from ordered BindingWindows.

This module composes no language from labels, counts, scores, thresholds, or
ranked candidates.  It follows only word order that was actually recorded in
cited multimodal BindingWindows and delegates every recognition decision to
``LanguageFactMemory``'s full-field, bidirectional L6 reciprocity boundary.

At each step all still-possible window paths must agree on exactly one
structural successor class.  Repetition supplies provenance, not voting
weight.  No successor, an unrecognized successor, a mixture of terminal and
continuing paths, or more than one distinct successor class stops the walk
without manufacturing a token.

The live engine is intentionally not wired here.  Integration must construct
``OrderedBindingWindow`` values from closed, persisted BindingWindows; this
module refuses window citations that are not explicitly emulated or observed
multimodal language experiences.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from dsf_ai_service.substrate.language_fact_strand import (
    BindingWindowCitation,
    FactRecallResult,
    LanguageFactMemory,
    LanguageFactStrand,
    RecallReason,
)


@dataclass(frozen=True)
class WindowTokenOccurrence:
    """One exact language entry at one exact position in a cited window."""

    fact: LanguageFactStrand
    window_id: str
    entry_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.fact, LanguageFactStrand):
            raise TypeError("window token fact must be a LanguageFactStrand")
        if not isinstance(self.window_id, str) or not self.window_id:
            raise ValueError("window token requires a window_id")
        if isinstance(self.entry_index, bool) or not isinstance(self.entry_index, int):
            raise ValueError("window token entry_index must be an integer")
        if self.entry_index < 0:
            raise ValueError("window token entry_index cannot be negative")
        if len(self._matching_citations()) != 1:
            raise ValueError(
                "window token must cite exactly one matching multimodal BindingWindow"
            )

    def _matching_citations(self) -> tuple[BindingWindowCitation, ...]:
        return tuple(
            citation
            for citation in self.fact.provenance.windows
            if citation.window_id == self.window_id
            and citation.is_multimodal_language_experience
        )

    @property
    def citation(self) -> BindingWindowCitation:
        return self._matching_citations()[0]


@dataclass(frozen=True)
class OrderedBindingWindow:
    """The language entries of one closed window in original entry order."""

    window_id: str
    experience_origin: str
    tokens: tuple[WindowTokenOccurrence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.window_id, str) or not self.window_id:
            raise ValueError("ordered BindingWindow requires a window_id")
        if self.experience_origin not in {"emulated", "observed"}:
            raise ValueError("ordered BindingWindow origin must be emulated or observed")
        if not isinstance(self.tokens, tuple):
            raise ValueError("ordered BindingWindow tokens must be an immutable tuple")

        previous_index = -1
        for token in self.tokens:
            if not isinstance(token, WindowTokenOccurrence):
                raise TypeError("ordered BindingWindow contains a non-token value")
            if token.window_id != self.window_id:
                raise ValueError("token window_id does not match its ordered BindingWindow")
            if token.citation.experience_origin != self.experience_origin:
                raise ValueError("token experience origin does not match its BindingWindow")
            if token.entry_index <= previous_index:
                raise ValueError(
                    "BindingWindow token entry indexes must be unique and strictly increasing"
                )
            previous_index = token.entry_index


@dataclass(frozen=True)
class TokenEntryProvenance:
    """Exact source carried by one emitted token."""

    window_id: str
    entry_index: int
    experience_origin: str
    source_tag: str
    trace_id: str
    source_strand_id: str
    modalities: tuple[str, ...]

    @classmethod
    def from_occurrence(cls, occurrence: WindowTokenOccurrence) -> "TokenEntryProvenance":
        citation = occurrence.citation
        return cls(
            window_id=occurrence.window_id,
            entry_index=occurrence.entry_index,
            experience_origin=citation.experience_origin,
            source_tag=occurrence.fact.provenance.source_tag,
            trace_id=occurrence.fact.provenance.trace_id,
            source_strand_id=occurrence.fact.strand_id,
            modalities=citation.modalities,
        )


@dataclass(frozen=True)
class ComposedToken:
    """One emitted structural class plus every window entry that supported it."""

    recognized_strands: tuple[LanguageFactStrand, ...]
    entry_provenance: tuple[TokenEntryProvenance, ...]

    def __post_init__(self) -> None:
        if not self.recognized_strands:
            raise ValueError("composed token requires a recognized structural class")
        structural_classes = {
            strand.structural_fingerprint for strand in self.recognized_strands
        }
        if len(structural_classes) != 1:
            raise ValueError("composed token cannot contain multiple structural classes")
        if not self.entry_provenance:
            raise ValueError("composed token requires exact window-entry provenance")

    @property
    def language_form(self) -> str:
        forms = {strand.language_form for strand in self.recognized_strands}
        if len(forms) != 1:
            raise RuntimeError("one structural class carried conflicting language forms")
        return next(iter(forms))

    @property
    def structural_fingerprint(self) -> str:
        return self.recognized_strands[0].structural_fingerprint


class ContinuationStopReason(str, Enum):
    EMPTY_QUERY = "empty_query"
    INPUT_UNKNOWN = "input_unknown"
    NO_CITED_OCCURRENCE = "no_cited_occurrence"
    NO_SUCCESSOR = "no_successor"
    MIXED_TERMINAL_AND_SUCCESSOR = "mixed_terminal_and_successor"
    SUCCESSOR_UNKNOWN = "successor_unknown"
    AMBIGUOUS_SUCCESSOR_CLASSES = "ambiguous_successor_classes"


@dataclass(frozen=True)
class ContinuationResult:
    emitted_tokens: tuple[ComposedToken, ...]
    stop_reason: ContinuationStopReason
    recall_reason: RecallReason | None = None

    @property
    def language_forms(self) -> tuple[str, ...]:
        return tuple(token.language_form for token in self.emitted_tokens)


class DeterministicWindowComposer:
    """Walks finite cited window order while structural successors stay unique."""

    def __init__(
        self,
        memory: LanguageFactMemory,
        windows: Iterable[OrderedBindingWindow],
    ) -> None:
        if not isinstance(memory, LanguageFactMemory):
            raise TypeError("composer memory must be LanguageFactMemory")
        self._memory = memory
        self._windows = tuple(windows)

        window_ids: set[str] = set()
        successor_by_position: dict[tuple[str, int], WindowTokenOccurrence | None] = {}
        window_class_sequences: list[
            tuple[OrderedBindingWindow, tuple[str, ...]]
        ] = []

        for window in self._windows:
            if not isinstance(window, OrderedBindingWindow):
                raise TypeError("composer windows must be OrderedBindingWindow values")
            if window.window_id in window_ids:
                raise ValueError("composer cannot accept a duplicate BindingWindow ID")
            window_ids.add(window.window_id)
            window_class_sequences.append(
                (
                    window,
                    tuple(
                        token.fact.structural_fingerprint for token in window.tokens
                    ),
                )
            )

            for position, occurrence in enumerate(window.tokens):
                successor = (
                    window.tokens[position + 1]
                    if position + 1 < len(window.tokens)
                    else None
                )
                successor_by_position[(window.window_id, occurrence.entry_index)] = successor

        self._successor_by_position = successor_by_position
        self._window_class_sequences = tuple(window_class_sequences)

    @staticmethod
    def _recognized_class(result: FactRecallResult) -> str:
        classes = {
            strand.structural_fingerprint for strand in result.matched_strands
        }
        if not result.recognized or len(classes) != 1:
            raise ValueError("recall result does not contain one recognized class")
        return next(iter(classes))

    def _longest_suffix_occurrences(
        self,
        recognized_query_classes: tuple[str, ...],
    ) -> tuple[WindowTokenOccurrence, ...]:
        """Return every path matching the longest exact structural suffix.

        Suffix length is a structural relation, not a score.  The first
        non-empty suffix class encountered from longest to shortest is the
        only active context, and every occurrence at that same length remains
        active for the unique-successor law.
        """

        for suffix_start in range(len(recognized_query_classes)):
            suffix = recognized_query_classes[suffix_start:]
            suffix_length = len(suffix)
            matches: list[WindowTokenOccurrence] = []
            for window, window_classes in self._window_class_sequences:
                if len(window.tokens) < suffix_length:
                    continue
                for end_position in range(suffix_length - 1, len(window.tokens)):
                    start_position = end_position - suffix_length + 1
                    if window_classes[start_position:end_position + 1] == suffix:
                        matches.append(window.tokens[end_position])
            if matches:
                return tuple(matches)
        return ()

    def continue_from(self, query: LanguageFactStrand) -> ContinuationResult:
        """Backward-compatible one-token continuation."""

        return self.continue_from_sequence((query,))

    def continue_from_sequence(
        self,
        query_sequence: tuple[LanguageFactStrand, ...],
    ) -> ContinuationResult:
        """Emit the finite agreed continuation after a structural sequence.

        No length cap exists.  Termination follows from strictly increasing
        entry positions in finite immutable windows, or from an honest stop at
        the first non-unique successor boundary.
        """

        if not isinstance(query_sequence, tuple):
            raise TypeError("query_sequence must be an immutable tuple")
        if not query_sequence:
            return ContinuationResult(
                emitted_tokens=(),
                stop_reason=ContinuationStopReason.EMPTY_QUERY,
            )

        recognized_query_classes: list[str] = []
        for query in query_sequence:
            if not isinstance(query, LanguageFactStrand):
                raise TypeError("every query token must be a LanguageFactStrand")
            input_result = self._memory.recall(query)
            if not input_result.recognized:
                return ContinuationResult(
                    emitted_tokens=(),
                    stop_reason=ContinuationStopReason.INPUT_UNKNOWN,
                    recall_reason=input_result.reason,
                )
            recognized_query_classes.append(self._recognized_class(input_result))

        active_occurrences = self._longest_suffix_occurrences(
            tuple(recognized_query_classes)
        )
        if not active_occurrences:
            return ContinuationResult(
                emitted_tokens=(),
                stop_reason=ContinuationStopReason.NO_CITED_OCCURRENCE,
            )

        emitted: list[ComposedToken] = []
        while True:
            successors: list[WindowTokenOccurrence] = []
            terminal_paths = 0
            for occurrence in active_occurrences:
                successor = self._successor_by_position[
                    (occurrence.window_id, occurrence.entry_index)
                ]
                if successor is None:
                    terminal_paths += 1
                else:
                    successors.append(successor)

            if not successors:
                return ContinuationResult(
                    emitted_tokens=tuple(emitted),
                    stop_reason=ContinuationStopReason.NO_SUCCESSOR,
                )
            if terminal_paths:
                return ContinuationResult(
                    emitted_tokens=tuple(emitted),
                    stop_reason=ContinuationStopReason.MIXED_TERMINAL_AND_SUCCESSOR,
                )

            recognized: list[
                tuple[WindowTokenOccurrence, FactRecallResult, str]
            ] = []
            for successor in successors:
                result = self._memory.recall(successor.fact)
                if not result.recognized:
                    return ContinuationResult(
                        emitted_tokens=tuple(emitted),
                        stop_reason=ContinuationStopReason.SUCCESSOR_UNKNOWN,
                        recall_reason=result.reason,
                    )
                recognized.append(
                    (successor, result, self._recognized_class(result))
                )

            successor_classes = {item[2] for item in recognized}
            if len(successor_classes) != 1:
                return ContinuationResult(
                    emitted_tokens=tuple(emitted),
                    stop_reason=ContinuationStopReason.AMBIGUOUS_SUCCESSOR_CLASSES,
                )

            recognized_strands: dict[str, LanguageFactStrand] = {}
            provenances: dict[tuple[str, int], TokenEntryProvenance] = {}
            for occurrence, result, _structural_class in recognized:
                for strand in result.matched_strands:
                    recognized_strands[strand.strand_id] = strand
                key = (occurrence.window_id, occurrence.entry_index)
                provenances[key] = TokenEntryProvenance.from_occurrence(occurrence)

            emitted.append(
                ComposedToken(
                    recognized_strands=tuple(
                        recognized_strands[key] for key in sorted(recognized_strands)
                    ),
                    entry_provenance=tuple(
                        provenances[key] for key in sorted(provenances)
                    ),
                )
            )
            active_occurrences = tuple(item[0] for item in recognized)
