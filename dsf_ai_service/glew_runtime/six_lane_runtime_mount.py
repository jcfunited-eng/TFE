"""Mounted six-lane runtime -- Stage 1 (foundational authorities) plus Stage 3
(field topology, typed-language kernel binding, sensor states).

This module begins the production builder required by
``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
section 9.2, "Mounted six-lane runtime": *"Build and persist one exact
authority set for: story chemistry runtime, story native-replay profile,
field topology, causal grid, support domain, resonance graph and operator,
pre-window state, sensor states, typed-language kernel binding and state,
field/basin profile, precision authority, expression mode bank, L5
applicability profile ... Production must load it from one authenticated
profile/checkpoint and verify every receipt before a turn is admitted."*

Prior investigation found that of the thirteen authorities named above,
eleven have no production construction function anywhere in the repository
-- only one comprehensive test fixture builds all of them
(``tests/glew_runtime/test_story_global_uf_basin.py::_mounted_six_lane_preparation``,
itself layered on
``tests/glew_runtime/test_story_native_replay.py::_mounted_five_sense_runtime``).

This file is Stage 1 of closing that gap: it promotes the four
FOUNDATIONAL, dependency-light authorities -- the ones every later authority
in the list depends on, directly or through the topology they are built
over -- into real, importable, individually testable ``mount_*`` functions:

* :func:`mount_precision_schedule_authority` -- ``PrecisionScheduleAuthority``
  (``expressions.py``)
* :func:`mount_causal_grid` -- ``CausalGrid`` (``operators.py``)
* :func:`mount_support_domain` -- ``MountedSupportDomain`` (``operators.py``)
* :func:`mount_resonance_graph_and_operator` -- ``MountedResonanceGraph`` and
  ``ResonanceOperatorAuthority`` (``operators.py``)

Stage 3 (appended to this same file, continuing Stage 1's "chain the
registry" pattern rather than a new module) promotes three more of the
remaining authorities, each genuinely derived from an already-mounted
story-chemistry manifest or an explicit caller input, never a hardcoded
fixed shape:

* :func:`mount_field_topology` -- ``MountedFieldTopology`` (``field.py``),
  built over every port a real mounted ``SignedStoryChemistryManifest``
  actually authenticates.
* :func:`mount_typed_language_kernel_binding` --
  ``MountedTypedLanguageKernelBinding`` (``language.py``).
* :func:`mount_story_sensor_states` -- a tuple of
  ``MountedStorySensorState`` (``story_native_replay.py``), one genesis
  state per already-mounted ``StorySensorPortAuthority``.

Stage 4 (appended to this same file, continuing the same "chain the
registry" pattern) closes the remaining gap by promoting the last four
named authorities plus one top-level production orchestrator:

* :func:`mount_expression_mode_bank` -- a thin, registry-chaining wrapper
  around ``expression_modes.py``'s own already-real genesis constructor
  ``create_empty_expression_mode_bank``. No new mode-bank physics is
  introduced; this only extends the registry with the bank's own receipt so
  later authorities that reference it (for example the pre-window state
  below) can resolve it as already mounted.
* :func:`mount_pre_window_state` -- ``MountedPreWindowState``
  (``global_uf.py``). The exact zero-amplitude genesis field state it binds
  to is likewise the only physically coherent genesis choice (mirroring
  :func:`mount_story_sensor_states`'s own documented "no observations yet"
  reasoning): a system truly at rest before its first causal sample has no
  amplitude to report at any fiber coordinate.
* :func:`mount_l5_governance_profile` -- ``MountedL5GovernanceProfile``
  (``closed_experience.py``). Defaults every governed fact at every mounted
  port to ``ApplicabilityState.REQUIRED`` -- the *only* precedent recorded
  anywhere in this repository (every real call site, and the ratified
  ``GLEW_LANGUAGE_WEAVE_PROFILE_v1.json``'s own ``l5_applicability`` block).
  A ``NOT_APPLICABLE`` rule remains an explicit, open, unratified gap this
  function does not invent or resolve.
* :func:`mount_story_global_uf_basin_profile` -- ``MountedStoryGlobalUFBasinProfile``
  (``story_global_uf_basin.py``).
* :func:`mount_six_lane_runtime` -- the top-level production orchestrator:
  mounts all thirteen authorities named in section 9.2 from caller-supplied
  raw inputs (manifest bytes, identifiers, causal samples, ...), chaining one
  :class:`ReceiptRegistry` through every one of them in the real dependency
  order the governing test fixture
  (``tests/glew_runtime/test_story_global_uf_basin.py::_mounted_six_lane_preparation``)
  proves works, and returns one frozen :class:`MountedSixLaneRuntime`
  bundling every authority plus the final registry.

None of these seven authorities selects, scores, weights, or infers a
value. Every function below only receipts and verifies caller-supplied,
already-decided inputs (mirroring exactly what ``PrecisionScheduleAuthority``,
``CausalGrid``, ``MountedSupportDomain``, ``MountedResonanceGraph``,
``ResonanceOperatorAuthority``, ``MountedFieldTopology``,
``MountedTypedLanguageKernelBinding``, and ``MountedStorySensorState``
themselves already enforce in ``expressions.py`` / ``operators.py`` /
``field.py`` / ``language.py`` / ``story_native_replay.py``). No forbidden
mechanism from section 6 of the governing spec is introduced.

Genuine physical/computational constraint vs. arbitrary test-fixture choice
-----------------------------------------------------------------------------
Investigated directly against ``expressions.py`` and ``expression_modes.py``
(not assumed from the test's literal values):

* ``PrecisionScheduleAuthority.maximum_precision_bits`` is a genuine
  computational-cost gate: ``expression_modes.py`` lines 423-424 and
  772-773, and ``expressions.py`` lines 1007-1015, all compare an actually
  *required* precision (computed from real exact-rational bit lengths via
  ``_next_power_of_two``, never a fixed constant) against this ceiling, and
  return ``UNKNOWN`` rather than a certified result once the requirement
  exceeds it. Raising the ceiling always costs more CPU/memory per certified
  Arb evaluation (arbitrary-precision ball arithmetic does not scale for
  free); lowering it trades certainty for latency. That trade-off is real.
  The specific number, however -- the test fixture's ``2048`` -- is NOT a
  physical constant: it was never derived from the topology dimension, the
  number of gates, or any field property, and the test's own field values
  (small fixed fractions like ``Fraction(1, 5)``) need only tens of bits, so
  ``2048`` there is simply "far more headroom than this tiny fixture could
  ever need." This module therefore does **not** default this value; see
  :func:`mount_precision_schedule_authority`. It is analogous to, and should
  be ratified alongside, the still-open conversational latency SLO in
  section 16.7 of the governing spec -- a product/ops resource budget, not
  cognition physics.
* ``CausalGrid.timestamps`` requiring *at least two* strictly increasing
  instants is a genuine, spec-grounded constraint, not a test convenience:
  section 9.1 states plainly, "A complete causal window needs at least two
  evolved frames because frozen L0-L4 evaluates change." ``CausalGrid``
  itself only enforces "nonempty and strictly increasing" (``operators.py``
  line 74 accepts a single timestamp); this module enforces the stricter,
  spec-cited two-frame floor at the mount boundary. The exact *count* beyond
  two, and the exact ``positive_weights`` quadrature scheme (the ratified
  profile and this codebase are silent on whether weights should be uniform,
  as every current test fixture assumes, or derived from real inter-sample
  time deltas), are NOT resolved here -- both remain caller-supplied and are
  flagged as open in :func:`mount_causal_grid`.
* ``MountedSupportDomain.required_port_keys`` defaulting to *every* port
  fiber in the mounted topology is grounded directly in section 9.4 of the
  governing spec ("The full emulator should normally provide all sensory
  states") and in ``GLEW_LANGUAGE_WEAVE_PROFILE_v1.json``'s own
  ``l5_applicability`` block, which confirms every known call site today
  sets every port/fact to ``REQUIRED`` and that no ``NOT_APPLICABLE`` rule is
  ratified yet. This default is therefore the documented current baseline,
  not an invented one -- but it is still only a default; a future L5-driven
  narrowing is an explicit, separate, not-yet-ratified decision, and this
  module accepts an explicit override rather than pretending to resolve it.
* ``MountedResonanceGraph.required_edges`` (which port pairs must show
  confirmed cross-resonance) and ``ResonanceOperatorAuthority.precision_bits``
  (the fixed one-shot Arb precision for the gamma-squared inner product) have
  **no ratified rule or physical derivation anywhere in this repository**.
  Every existing test builds a "chain" graph (consecutive ports in whatever
  order they happen to be enumerated) purely for enumeration convenience --
  that pairing has no cited physical or architectural meaning. This module
  therefore requires both as explicit, mandatory caller inputs with no
  computed default; see :func:`mount_resonance_graph_and_operator` for the
  cross-validation it does perform (every named edge must reference a port
  key that is genuinely present in the given topology).

Composability
-------------
Each ``mount_*`` function here takes the growing :class:`ReceiptRegistry`
from every previously mounted authority and returns a new registry with its
own receipt merged in (see :func:`extend_receipt_registry`), so a later stage
can chain calls across this file exactly as the test fixtures already do,
without re-deriving that merge logic itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .closed_experience import (
    L5ApplicabilityRule,
    MountedL5GovernanceProfile,
    l5_governance_profile_receipt_payload,
)
from .commit import ApplicabilityState, GovernedFact
from .expression_modes import ExpressionModeBank, create_empty_expression_mode_bank
from .expressions import (
    PrecisionScheduleAuthority,
    precision_schedule_authority_receipt_payload,
)
from .field import (
    ExactComplex,
    ExactFieldState,
    HamiltonianEntry,
    LocalRate,
    MountedFieldTopology,
    PortFiber,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
)
from .global_uf import MountedPreWindowState, pre_window_state_receipt_payload
from .l6 import L6Lane
from .language import (
    MountedTypedLanguageKernelBinding,
    typed_interface_receipt_payload,
    typed_language_kernel_binding_receipt_payload,
    typed_phase_calibration_receipt_payload,
)
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
)
from .operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    PortKey,
    RequiredEdge,
    ResonanceOperatorAuthority,
    causal_grid_receipt_payload,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
    support_domain_receipt_payload,
)
from .story_chemistry import (
    SignedStoryChemistryManifest,
    StoryChemistryRuntime,
    StoryChemistryStatus,
    mount_story_chemistry,
)
from .story_global_uf_basin import (
    MountedStoryGlobalUFBasinProfile,
    story_global_uf_basin_profile_receipt_payload,
)
from .story_native_replay import (
    MountedStoryNativeReplayProfile,
    MountedStorySensorState,
    StorySensorPortAuthority,
    story_native_replay_profile_receipt_payload,
    story_replay_chemistry_state_receipt_payload,
    story_sensor_state_receipt_payload,
)


def extend_receipt_registry(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    """Return a new registry containing ``registry``'s records plus ``payloads``.

    This is the same append-only merge every existing test fixture's private
    ``_extend``/``_extend_registry``/``_extend_records`` helper already
    performs (for example
    ``tests/glew_runtime/test_story_global_uf_basin.py::_extend``,
    ``closed_experience.py``'s ``_extend_registry``,
    ``story_native_replay.py``'s ``_extend_records``): a digest that is
    already mounted with identical bytes is a no-op; a digest that would
    collide with *different* bytes fails closed instead of silently
    overwriting a mounted receipt. It never removes or replaces an existing
    record, and it preserves ``registry.profile_binding_sha256`` exactly, so
    every authority mounted against the merged result still resolves the same
    profile binding.
    """

    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("a mounted immutable receipt registry is required")
    merged: dict[str, bytes] = {record.digest: record.payload for record in registry.records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("mounted receipt payload must be nonempty exact bytes")
        digest = receipt_sha256(payload)
        existing = merged.get(digest)
        if existing is not None and existing != payload:
            raise ReceiptError(
                "mounted receipt digest collides with different payload bytes"
            )
        merged[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(digest, merged[digest]) for digest in sorted(merged)),
    )


def mount_precision_schedule_authority(
    *,
    authority_id: str,
    maximum_precision_bits: int,
    receipt_registry: ReceiptRegistry,
) -> tuple[PrecisionScheduleAuthority, ReceiptRegistry]:
    """Mount and verify one :class:`PrecisionScheduleAuthority`.

    ``maximum_precision_bits`` is a real computational-cost ceiling (see the
    module docstring), but its exact value is an operational/product policy
    decision, not a physical constant -- this function therefore has no
    default and will not silently adopt the test fixture's ``2048``. The
    caller (an operator, a later mounted-runtime profile, or an explicit
    ratified constant once one exists) must decide it explicitly.

    Returns the constructed, self-verified authority together with
    ``receipt_registry`` extended by its own receipt payload.
    """

    payload = precision_schedule_authority_receipt_payload(
        authority_id=authority_id,
        maximum_precision_bits=maximum_precision_bits,
    )
    registry = extend_receipt_registry(receipt_registry, payload)
    authority = PrecisionScheduleAuthority(
        authority_id=authority_id,
        maximum_precision_bits=maximum_precision_bits,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    authority.verify(registry)
    return authority, registry


_MINIMUM_CAUSAL_FRAMES = 2
"""Section 9.1: "A complete causal window needs at least two evolved frames
because frozen L0-L4 evaluates change." This is cited spec text, not a guess.
"""


def mount_causal_grid(
    *,
    grid_id: str,
    timestamps: Sequence[Fraction],
    positive_weights: Sequence[Fraction],
    receipt_registry: ReceiptRegistry,
) -> tuple[CausalGrid, ReceiptRegistry]:
    """Mount and verify one common :class:`CausalGrid`.

    ``timestamps``/``positive_weights`` must be the real, already-decided
    sample instants and quadrature weights of one actual causal window (for
    example, the source times a live boundary owner actually observed, and
    the same instants a typed-language event's ``valid_sample_times`` must
    equal for the two lanes to share one grid) -- never invented literals.

    This function enforces one additional, spec-cited invariant beyond
    ``CausalGrid.__post_init__`` itself (which only requires a nonempty,
    strictly increasing series): at least two timestamps, per section 9.1
    (see :data:`_MINIMUM_CAUSAL_FRAMES`). ``CausalGrid`` alone would accept a
    single instant; a real causal *window* cannot show change over one
    instant, so a length-1 grid is rejected here rather than downstream.

    The quadrature weighting scheme itself (uniform, as every current test
    fixture assumes, versus one derived from real inter-sample time deltas)
    is not ratified anywhere in this repository and is left to the caller;
    this function does not invent one.
    """

    ordered_timestamps = tuple(timestamps)
    ordered_weights = tuple(positive_weights)
    if len(ordered_timestamps) < _MINIMUM_CAUSAL_FRAMES:
        raise ReceiptError(
            "a mounted causal grid requires at least two strictly increasing "
            "timestamps -- frozen L0-L4 evaluates change across at least two "
            "evolved frames (governing spec section 9.1), never one instant"
        )
    payload = causal_grid_receipt_payload(grid_id, ordered_timestamps, ordered_weights)
    registry = extend_receipt_registry(receipt_registry, payload)
    grid = CausalGrid(
        grid_id=grid_id,
        timestamps=ordered_timestamps,
        positive_weights=ordered_weights,
        grid_receipt_sha256=receipt_sha256(payload),
    )
    grid.verify(registry)
    return grid, registry


def mount_support_domain(
    *,
    domain_id: str,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
    required_port_keys: Sequence[PortKey] | None = None,
) -> tuple[MountedSupportDomain, ReceiptRegistry]:
    """Mount and verify one :class:`MountedSupportDomain` over ``topology``.

    ``required_port_keys`` defaults to *every* port fiber genuinely present
    in the already-mounted ``topology`` -- grounded in section 9.4 of the
    governing spec ("The full emulator should normally provide all sensory
    states") and in the ratified language-weave profile's own
    ``l5_applicability`` block, which records that every known call site
    today requires every port and that no ``NOT_APPLICABLE`` rule is ratified
    yet. This is the documented current baseline, not an invented shortcut;
    a caller may still pass an explicit, narrower ``required_port_keys`` once
    a future L5-applicability ratification actually excuses a specific port,
    but this function will not guess that exclusion itself.

    Every explicitly supplied key (default or override) is cross-checked
    against ``topology.ordered_port_fibers`` and rejected if it names a port
    the topology does not actually mount -- ``MountedSupportDomain`` itself
    has no notion of a topology and cannot perform this check.
    """

    topology.verify(receipt_registry)
    topology_keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    keys = topology_keys if required_port_keys is None else tuple(required_port_keys)
    unknown = tuple(key for key in keys if key not in set(topology_keys))
    if unknown:
        raise ReceiptError(
            f"support domain names a port key absent from the mounted topology: {unknown!r}"
        )
    payload = support_domain_receipt_payload(domain_id, keys)
    registry = extend_receipt_registry(receipt_registry, payload)
    domain = MountedSupportDomain(
        domain_id=domain_id,
        required_port_keys=keys,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    domain.verify(registry)
    return domain, registry


def mount_resonance_graph_and_operator(
    *,
    graph_id: str,
    required_edges: Sequence[RequiredEdge],
    operator_id: str,
    precision_bits: int,
    receipt_registry: ReceiptRegistry,
    topology: MountedFieldTopology | None = None,
) -> tuple[MountedResonanceGraph, ResonanceOperatorAuthority, ReceiptRegistry]:
    """Mount and verify one :class:`MountedResonanceGraph` plus its
    :class:`ResonanceOperatorAuthority`.

    Neither ``required_edges`` (which port pairs must show confirmed
    cross-resonance) nor ``precision_bits`` (the fixed one-shot Arb working
    precision for the gamma-squared inner product) has a ratified rule or
    physical derivation anywhere in this repository today -- every existing
    test builds an arbitrary "chain" over whatever order its ports happen to
    be enumerated in, which is an enumeration convenience, not a cited
    architectural requirement. Both are therefore mandatory, explicit caller
    inputs with no computed default; see the module docstring.

    When ``topology`` is supplied, every edge's two port keys are
    cross-checked against ``topology.ordered_port_fibers`` and rejected if
    either key names a port the topology does not actually mount --
    ``MountedResonanceGraph`` itself has no notion of a topology and cannot
    perform this check. ``topology`` is optional because a resonance graph
    and operator may legitimately be mounted once and reused across more
    than one topology revision (mirroring
    ``tests/glew_runtime/test_story_global_uf_basin.py``'s own
    ``_mounted_six_lane_preparation``, which reuses the five-sense
    ``resonance_operator`` unchanged while mounting a new six-lane
    ``MountedResonanceGraph``); callers that do have a concrete topology in
    hand should still pass it for the extra safety check.
    """

    edges = tuple(required_edges)
    if topology is not None:
        topology.verify(receipt_registry)
        topology_keys = {fiber.key for fiber in topology.ordered_port_fibers}
        unknown = tuple(
            key
            for edge in edges
            for key in (edge.left_port_key, edge.right_port_key)
            if key not in topology_keys
        )
        if unknown:
            raise ReceiptError(
                "resonance graph names a port key absent from the mounted "
                f"topology: {unknown!r}"
            )
    graph_payload = resonance_graph_receipt_payload(graph_id, edges)
    operator_payload = resonance_operator_receipt_payload(operator_id, precision_bits)
    registry = extend_receipt_registry(receipt_registry, graph_payload, operator_payload)
    graph = MountedResonanceGraph(
        graph_id=graph_id,
        required_edges=edges,
        authority_receipt_sha256=receipt_sha256(graph_payload),
    )
    operator = ResonanceOperatorAuthority(
        operator_id=operator_id,
        precision_bits=precision_bits,
        authority_receipt_sha256=receipt_sha256(operator_payload),
    )
    graph.verify(registry)
    operator.verify(registry)
    return graph, operator, registry


def mount_field_topology(
    *,
    topology_id: str,
    manifest: SignedStoryChemistryManifest,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedFieldTopology, ReceiptRegistry]:
    """Mount and verify one :class:`MountedFieldTopology` over ``manifest``.

    Unlike ``genesis.py``'s empty/dimension-0 topology, this mounts one real
    fiber for every port ``manifest`` (an already-mounted
    :class:`SignedStoryChemistryManifest`, e.g. from
    ``story_chemistry.mount_story_chemistry`` /
    ``mount_packaged_production_story_chemistry``) actually authenticates --
    the manifest's own port count and lane/port ids, never a hardcoded five-
    or six-port shape. ``story_chemistry._load_manifest`` already requires
    ``manifest.ports`` to be unique and canonically ordered by ``port_id``,
    so the fibers built here inherit that same canonical order rather than
    this function re-deriving or second-guessing it.

    Each port's ``kernel_binding`` is independently re-verified against
    ``receipt_registry`` (not merely trusted off the manifest object) before
    its ``lane_id``/``port_id`` are read into a fiber. The caller must
    already have folded the manifest's authenticated static receipts (for
    example a mounted ``StoryChemistryRuntime.receipt_registry.records``, as
    every existing test fixture already does) into ``receipt_registry``
    before calling this function -- exactly as :func:`mount_support_domain`
    requires an already-verifiable ``topology`` rather than re-deriving its
    authority from scratch.
    """

    if not isinstance(manifest, SignedStoryChemistryManifest):
        raise ReceiptError(
            "field topology requires an authenticated story chemistry manifest"
        )
    if not manifest.ports:
        raise ReceiptError(
            "field topology requires at least one mounted story chemistry port"
        )
    fibers: list[PortFiber] = []
    for port in manifest.ports:
        port.kernel_binding.verify(receipt_registry)
        if port.kernel_binding.port_id != port.port_id:
            raise ReceiptError(
                "story chemistry port id disagrees with its own kernel binding"
            )
        fibers.append(PortFiber(port.kernel_binding.lane_id, port.port_id))
    ordered_fibers = tuple(fibers)
    payload = field_topology_receipt_payload(topology_id, ordered_fibers)
    registry = extend_receipt_registry(receipt_registry, payload)
    topology = MountedFieldTopology(
        topology_id=topology_id,
        ordered_port_fibers=ordered_fibers,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    topology.verify(registry)
    return topology, registry


def mount_typed_language_kernel_binding(
    *,
    adapter_id: str,
    interface_id: str,
    phase_calibration_id: str,
    phase_kappa: Fraction,
    derivation_payload: bytes,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedTypedLanguageKernelBinding, ReceiptRegistry]:
    """Mount and verify one :class:`MountedTypedLanguageKernelBinding`.

    ``build_typed_language_frozen_kernel_input`` (``language.py`` line 721)
    is already a real production function, but it *consumes* an
    already-mounted binding; it never constructs one. This function supplies
    that missing piece: it builds and receipts the binding itself plus its
    two referenced sub-authorities (the typed artificial interface and the
    phase calibration) from the caller's own already-decided values, using
    the existing, already-tested ``typed_interface_receipt_payload`` /
    ``typed_phase_calibration_receipt_payload`` /
    ``typed_language_kernel_binding_receipt_payload`` functions unmodified.

    Neither ``typed_interface_receipt_payload`` nor
    ``typed_phase_calibration_receipt_payload`` validates its own inputs
    (unlike the analogous story-chemistry receipt builders, which call
    ``require_identifier``/``require_fraction`` internally) -- this function
    adds those checks explicitly so a malformed caller input fails closed
    with ``ReceiptError`` here rather than raising a bare, undocumented
    exception inside those helpers.

    ``derivation_payload`` is caller-supplied, opaque, canonical receipt
    bytes: there is no ratified derivation schema for the typed-language
    kernel map anywhere in this repository (mirroring how
    ``story_chemistry.py``'s own per-port kernel-binding derivations are
    likewise caller-decided free-form receipts, not a fixed shape this
    module invents).
    """

    require_identifier(adapter_id, "typed-language kernel adapter id")
    require_identifier(interface_id, "typed-language kernel interface id")
    require_identifier(
        phase_calibration_id, "typed-language phase calibration id"
    )
    require_fraction(phase_kappa, "typed-language phase kappa")
    if not isinstance(derivation_payload, bytes) or not derivation_payload:
        raise ReceiptError(
            "typed-language kernel derivation payload must be nonempty exact bytes"
        )

    interface_payload = typed_interface_receipt_payload(interface_id)
    phase_payload = typed_phase_calibration_receipt_payload(
        phase_calibration_id, phase_kappa
    )
    registry = extend_receipt_registry(
        receipt_registry, interface_payload, phase_payload, derivation_payload
    )
    interface_receipt_sha256 = receipt_sha256(interface_payload)
    phase_calibration_receipt_sha256 = receipt_sha256(phase_payload)
    derivation_receipt_sha256 = receipt_sha256(derivation_payload)
    binding_payload = typed_language_kernel_binding_receipt_payload(
        adapter_id=adapter_id,
        interface_id=interface_id,
        interface_receipt_sha256=interface_receipt_sha256,
        phase_calibration_receipt_sha256=phase_calibration_receipt_sha256,
        derivation_receipt_sha256=derivation_receipt_sha256,
    )
    registry = extend_receipt_registry(registry, binding_payload)
    binding = MountedTypedLanguageKernelBinding(
        adapter_id=adapter_id,
        interface_id=interface_id,
        interface_receipt_sha256=interface_receipt_sha256,
        phase_calibration_receipt_sha256=phase_calibration_receipt_sha256,
        derivation_receipt_sha256=derivation_receipt_sha256,
        authority_receipt_sha256=receipt_sha256(binding_payload),
    )
    binding.verify(registry)
    return binding, registry


def mount_story_sensor_states(
    *,
    manifest: SignedStoryChemistryManifest,
    ports: Sequence[StorySensorPortAuthority],
    receipt_registry: ReceiptRegistry,
) -> tuple[tuple[MountedStorySensorState, ...], ReceiptRegistry]:
    """Mount and verify one genesis :class:`MountedStorySensorState` for
    every one of ``ports``.

    ``execute_story_native_replay`` (``story_native_replay.py`` line 1217)
    is already a real production function, but it only *evolves* sensor
    state forward from one already-mounted starting tuple; it never
    constructs that starting tuple. This function supplies that missing
    initial-mount piece.

    ``MountedStorySensorState.verify`` (``story_native_replay.py`` line 628)
    itself requires binding to a :class:`StorySensorPortAuthority`, not
    directly to a story-chemistry manifest port: ``StorySensorPortAuthority``
    encodes an entirely separate native-replay physical response law
    (response growth/decay, phase kappa, raw-code bounds, ...) that has no
    corresponding field anywhere in ``SignedStoryChemistryManifest``'s
    receptor-kinetics ports and so cannot be derived from ``manifest`` alone.
    This module has no production ``mount_story_sensor_port_authority``
    -equivalent constructor for that prerequisite authority -- the same
    class of gap this whole stage exists to close, but naming and closing it
    is explicitly out of this stage's three-authority scope. Callers must
    therefore supply already independently ``.verify()``-able
    ``StorySensorPortAuthority`` values here, one per manifest port whose
    replay state is being mounted (see ``tests/glew_runtime/
    test_story_native_replay.py``'s own ``_sensor_port`` helper for how one
    is built today, absent a promoted production constructor).

    ``last_source_index=-1``, ``retained_signal=Fraction(0)``, and
    ``phase_turns=Fraction(0)`` are the only physically coherent genesis
    values for a state with no observations yet -- ``-1`` is the same "no
    samples observed" sentinel ``MountedStorySensorState.__post_init__``
    itself already floors at, and a system truly at rest before its first
    causal sample has no accumulated native response or phase to report.
    They are hardcoded rather than exposed as caller inputs because there is
    no other physically meaningful genesis choice, mirroring how this file
    already hardcodes the spec-cited ``_MINIMUM_CAUSAL_FRAMES`` floor rather
    than exposing it as a parameter. ``last_timestamp`` is not invented
    either: it is read directly from ``manifest``'s own already-authenticated
    ``initial_state.source_time`` for the matching story port -- the same
    real chemistry genesis instant ``story_replay_chemistry_state_receipt_payload``
    and ``_verify_pre_window`` already require sensor state to start at.
    """

    if not isinstance(manifest, SignedStoryChemistryManifest):
        raise ReceiptError(
            "story sensor states require an authenticated story chemistry manifest"
        )
    ordered_ports = tuple(ports)
    if not ordered_ports:
        raise ReceiptError(
            "story sensor states require at least one mounted sensor port"
        )
    if not all(
        isinstance(port, StorySensorPortAuthority) for port in ordered_ports
    ):
        raise ReceiptError(
            "story sensor states require typed StorySensorPortAuthority ports"
        )
    field_port_ids = tuple(port.field_port_id for port in ordered_ports)
    if len(set(field_port_ids)) != len(field_port_ids):
        raise ReceiptError("story sensor states cannot repeat a field port id")

    registry = receipt_registry
    states: list[MountedStorySensorState] = []
    payloads: list[bytes] = []
    for port in ordered_ports:
        port.verify(registry)
        chemistry_port = manifest.port(port.story_port_id)
        chemistry_port.initial_state.verify(registry)
        genesis_time = chemistry_port.initial_state.source_time
        payload = story_sensor_state_receipt_payload(
            field_port_id=port.field_port_id,
            source_epoch=port.source_epoch,
            last_source_index=-1,
            last_timestamp=genesis_time,
            retained_signal=Fraction(0),
            phase_turns=Fraction(0),
            port_authority_receipt_sha256=port.authority_receipt_sha256,
        )
        states.append(
            MountedStorySensorState(
                field_port_id=port.field_port_id,
                source_epoch=port.source_epoch,
                last_source_index=-1,
                last_timestamp=genesis_time,
                retained_signal=Fraction(0),
                phase_turns=Fraction(0),
                port_authority_receipt_sha256=port.authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
        payloads.append(payload)
    registry = extend_receipt_registry(registry, *payloads)
    ordered_states = tuple(states)
    for port, state in zip(ordered_ports, ordered_states, strict=True):
        state.verify(port=port, receipt_registry=registry)
    return ordered_states, registry


def mount_expression_mode_bank(
    *,
    topology: MountedFieldTopology,
    precision_authority: PrecisionScheduleAuthority,
    receipt_registry: ReceiptRegistry,
) -> tuple[ExpressionModeBank, ReceiptRegistry]:
    """Mount one genesis :class:`ExpressionModeBank` (empty, rank zero).

    ``create_empty_expression_mode_bank`` (``expression_modes.py`` line 500)
    is already the real, tested genesis constructor -- it independently
    re-verifies ``topology`` and ``precision_authority`` and rejects an
    unavailable (dimension-zero) topology. No new mode-bank physics is
    introduced here; this function only performs the same chained-registry
    "mount and extend" bookkeeping every other function in this file already
    performs, so a bank built this way composes with the rest of the chain:
    ``ExpressionModeBank.verify`` itself never requires the bank's own top-
    level receipt to already be mounted (it only re-derives and compares
    canonical bytes held on the object), but :class:`MountedPreWindowState`
    below *does* require its ``mode_state_receipt_sha256`` to already resolve
    in the registry -- exactly the gap this wrapper closes.
    """

    bank = create_empty_expression_mode_bank(
        topology=topology,
        precision_authority=precision_authority,
        receipt_registry=receipt_registry,
    )
    registry = extend_receipt_registry(receipt_registry, bank.receipt_payload)
    bank.verify(topology=topology, receipt_registry=registry)
    return bank, registry


def mount_pre_window_state(
    *,
    state_id: str,
    chemistry_state_receipt_sha256: str,
    field_state: ExactFieldState,
    mode_bank: ExpressionModeBank,
    memory_state_receipt_sha256: str,
    l6_state_receipt_sha256: str,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedPreWindowState, ReceiptRegistry]:
    """Mount and verify one :class:`MountedPreWindowState`.

    ``field_state`` and ``mode_bank`` are typed, already-mounted authorities:
    this function independently re-verifies both against ``topology`` (never
    merely trusting a caller-supplied receipt digest string for them), then
    reads their own canonical receipt digests into the pre-window payload --
    mirroring exactly how :func:`mount_support_domain` re-verifies an
    already-mounted ``topology`` rather than re-deriving its authority.

    ``chemistry_state_receipt_sha256``, ``memory_state_receipt_sha256``, and
    ``l6_state_receipt_sha256`` remain opaque, already-mounted receipt
    digests supplied by the caller: this codebase has a real, existing
    derivation for the first
    (``story_native_replay.story_replay_chemistry_state_receipt_payload``),
    but none yet for the latter two (no production "memory state" or "L6
    state" genesis authority exists anywhere in this repository, the same
    class of gap already documented for ``StorySensorPortAuthority`` in
    :func:`mount_story_sensor_states`). This function does not invent one; it
    only requires each digest to already resolve in ``receipt_registry``,
    exactly like ``MountedPreWindowState.verify`` itself does.
    """

    topology.verify(receipt_registry)
    if not isinstance(field_state, ExactFieldState):
        raise ReceiptError("pre-window state requires a mounted exact field state")
    field_state.verify(receipt_registry)
    if field_state.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
        raise ReceiptError("pre-window field state belongs to another topology")
    if not isinstance(mode_bank, ExpressionModeBank):
        raise ReceiptError("pre-window state requires a mounted expression mode bank")
    mode_bank.verify(topology=topology, receipt_registry=receipt_registry)
    for digest, field_name in (
        (chemistry_state_receipt_sha256, "pre-window chemistry state receipt"),
        (memory_state_receipt_sha256, "pre-window memory state receipt"),
        (l6_state_receipt_sha256, "pre-window L6 state receipt"),
    ):
        receipt_registry.resolve(digest, field_name)
    payload = pre_window_state_receipt_payload(
        state_id=state_id,
        chemistry_state_receipt_sha256=chemistry_state_receipt_sha256,
        field_state_receipt_sha256=field_state.authority_receipt_sha256,
        mode_state_receipt_sha256=mode_bank.receipt_sha256,
        memory_state_receipt_sha256=memory_state_receipt_sha256,
        l6_state_receipt_sha256=l6_state_receipt_sha256,
    )
    registry = extend_receipt_registry(receipt_registry, payload)
    state = MountedPreWindowState(
        state_id=state_id,
        chemistry_state_receipt_sha256=chemistry_state_receipt_sha256,
        field_state_receipt_sha256=field_state.authority_receipt_sha256,
        mode_state_receipt_sha256=mode_bank.receipt_sha256,
        memory_state_receipt_sha256=memory_state_receipt_sha256,
        l6_state_receipt_sha256=l6_state_receipt_sha256,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    state.verify(registry)
    return state, registry


def mount_l5_governance_profile(
    *,
    profile_id: str,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedL5GovernanceProfile, ReceiptRegistry]:
    """Mount and verify one :class:`MountedL5GovernanceProfile`.

    ``MountedL5GovernanceProfile.verify`` itself requires ``rules`` to name
    *exactly* ``(fiber.lane_id, fiber.port_id, fact)`` for every fiber in
    ``topology.ordered_port_fibers`` and every ``GovernedFact`` -- so every
    port and fact is always governed by some rule; the open question is only
    which ``ApplicabilityState`` each one carries. This function always
    builds ``ApplicabilityState.REQUIRED`` rules: it is the *only* rule this
    repository has any real precedent for -- every existing call site (see
    ``tests/glew_runtime/test_story_global_uf_basin.py``'s own
    ``_mounted_six_lane_preparation``) sets every port/fact to ``REQUIRED``,
    and the ratified ``GLEW_LANGUAGE_WEAVE_PROFILE_v1.json``'s own
    ``l5_applicability`` block records that no ``NOT_APPLICABLE`` rule is
    ratified yet. This function therefore does not expose any override for
    the rule states themselves -- unlike, say, :func:`mount_support_domain`'s
    ``required_port_keys`` override -- because doing so would hand the
    caller a lever for an explicitly open, unratified decision (when a port
    is genuinely inapplicable) that is not this function's, or this stage's,
    to resolve.
    """

    topology.verify(receipt_registry)
    rules = tuple(
        L5ApplicabilityRule(fiber.lane_id, fiber.port_id, fact, ApplicabilityState.REQUIRED)
        for fiber in topology.ordered_port_fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    payload = l5_governance_profile_receipt_payload(
        profile_id=profile_id,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        rules=rules,
    )
    registry = extend_receipt_registry(receipt_registry, payload)
    profile = MountedL5GovernanceProfile(
        profile_id=profile_id,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        rules=rules,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    profile.verify(topology, registry)
    return profile, registry


def mount_story_global_uf_basin_profile(
    *,
    profile_id: str,
    story_profile: MountedStoryNativeReplayProfile,
    physical_profile_payload: bytes,
    initial_field_state: ExactFieldState,
    hbar: Fraction,
    hamiltonian: Sequence[HamiltonianEntry],
    local_rates: Sequence[LocalRate],
    source_time_unit: str,
    max_connected_component_dimension: int,
    field_precision_bits: int,
    precision_authority: PrecisionScheduleAuthority,
    mode_bank: ExpressionModeBank,
    l5_governance: MountedL5GovernanceProfile,
    pre_window_state: MountedPreWindowState,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedStoryGlobalUFBasinProfile, ReceiptRegistry]:
    """Mount and verify one :class:`MountedStoryGlobalUFBasinProfile`.

    ``physical_profile_payload`` remains caller-supplied, opaque, canonical
    receipt bytes -- there is no ratified derivation for the six-lane
    physical evolution profile anywhere in this repository (mirroring
    ``mount_typed_language_kernel_binding``'s own ``derivation_payload``).

    Every other argument is an already-mounted, independently-typed
    authority (``story_profile``, ``initial_field_state``, ``precision_authority``,
    ``mode_bank``, ``l5_governance``); this function performs no selection or
    invented physics of its own. ``MountedStoryGlobalUFBasinProfile.verify``
    itself enforces the real structural invariants this profile exists to
    certify: that ``topology`` preserves every one of ``story_profile``'s
    story ports and carries exactly all six native lanes (governing spec's
    six-lane requirement), that ``initial_field_state`` precedes
    ``story_profile.grid``'s first sample and is the same field state
    ``pre_window_state`` names, and that ``mode_bank`` is the same bank
    ``pre_window_state`` names.
    """

    if not isinstance(physical_profile_payload, bytes) or not physical_profile_payload:
        raise ReceiptError(
            "story Global-UF basin profile requires a nonempty exact physical profile payload"
        )
    registry = extend_receipt_registry(receipt_registry, physical_profile_payload)
    physical_profile_receipt_sha256 = receipt_sha256(physical_profile_payload)
    hamiltonian_tuple = tuple(hamiltonian)
    local_rates_tuple = tuple(local_rates)
    payload = story_global_uf_basin_profile_receipt_payload(
        profile_id=profile_id,
        story_replay_profile_receipt_sha256=story_profile.authority_receipt_sha256,
        physical_profile_receipt_sha256=physical_profile_receipt_sha256,
        initial_field_state_receipt_sha256=initial_field_state.authority_receipt_sha256,
        hbar=hbar,
        hamiltonian=hamiltonian_tuple,
        local_rates=local_rates_tuple,
        source_time_unit=source_time_unit,
        max_connected_component_dimension=max_connected_component_dimension,
        field_precision_bits=field_precision_bits,
        precision_authority_receipt_sha256=precision_authority.authority_receipt_sha256,
        mode_bank_receipt_sha256=mode_bank.receipt_sha256,
        l5_governance_receipt_sha256=l5_governance.authority_receipt_sha256,
    )
    registry = extend_receipt_registry(registry, payload)
    profile = MountedStoryGlobalUFBasinProfile(
        profile_id=profile_id,
        story_replay_profile_receipt_sha256=story_profile.authority_receipt_sha256,
        physical_profile_receipt_sha256=physical_profile_receipt_sha256,
        initial_field_state=initial_field_state,
        hbar=hbar,
        hamiltonian=hamiltonian_tuple,
        local_rates=local_rates_tuple,
        source_time_unit=source_time_unit,
        max_connected_component_dimension=max_connected_component_dimension,
        field_precision_bits=field_precision_bits,
        precision_authority=precision_authority,
        mode_bank=mode_bank,
        l5_governance=l5_governance,
        authority_receipt_sha256=receipt_sha256(payload),
        authority_receipt_payload=payload,
    )
    profile.verify(
        story_profile=story_profile,
        pre_window_state=pre_window_state,
        topology=topology,
        receipt_registry=registry,
    )
    return profile, registry


def _reroot_registry(
    *,
    profile_payload: bytes,
    prior_registry: ReceiptRegistry,
    extra_payloads: Sequence[bytes] = (),
) -> ReceiptRegistry:
    """Return a new registry rooted at ``profile_payload``, carrying forward
    every receipt already mounted in ``prior_registry`` (plus ``extra_payloads``).

    ``extend_receipt_registry`` always preserves ``registry.profile_binding_sha256``
    unchanged -- correct for every other authority in this file, none of
    which cares what the registry's root profile is, only that its own
    receipt resolves. ``MountedStoryNativeReplayProfile.verify`` is the one
    exception: it requires the *registry itself* to be rooted at its own
    receipt (``receipt_registry.profile_binding_sha256 != self.authority_receipt_sha256``
    fails closed), exactly as ``tests/glew_runtime/test_story_native_replay.py::
    _mounted_five_sense_runtime`` builds its returned registry via
    ``ReceiptRegistry.from_payloads(profile_payload=<the native-replay
    profile's own payload>, ...)`` rather than extending some other root.
    This helper performs that one re-rooting, once, so every later mount in
    :func:`mount_six_lane_runtime` can keep using the ordinary
    ``extend_receipt_registry`` chain afterward.
    """

    merged: dict[str, bytes] = {record.digest: record.payload for record in prior_registry.records}
    for payload in extra_payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("re-rooted registry receipt payload must be nonempty exact bytes")
        digest = receipt_sha256(payload)
        existing = merged.get(digest)
        if existing is not None and existing != payload:
            raise ReceiptError(
                "re-rooted registry receipt digest collides with different payload bytes"
            )
        merged[digest] = payload
    root_digest = receipt_sha256(profile_payload)
    return ReceiptRegistry.from_payloads(
        profile_payload=profile_payload,
        receipt_payloads=tuple(
            merged[digest] for digest in sorted(merged) if digest != root_digest
        ),
    )


def _mount_six_lane_topology(
    *,
    topology_id: str,
    five_sense_topology: MountedFieldTopology,
    language_port_id: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedFieldTopology, ReceiptRegistry]:
    """Mount the six-lane topology: every already-mounted five-sense fiber
    plus one language fiber.

    ``mount_field_topology`` derives fibers strictly from a story-chemistry
    manifest's ports and so has no way to add a sixth, non-chemistry lane.
    This composes an already-mounted five-sense topology with one caller-
    named language port_id, mirroring exactly how ``tests/glew_runtime/
    test_story_global_uf_basin.py::_mounted_six_lane_preparation`` builds its
    own six-lane fiber tuple (the language fiber first, then every already-
    mounted five-sense fiber, unchanged and in the same order).
    """

    five_sense_topology.verify(receipt_registry)
    fibers = (
        PortFiber(L6Lane.LANGUAGE.value, language_port_id),
        *five_sense_topology.ordered_port_fibers,
    )
    payload = field_topology_receipt_payload(topology_id, fibers)
    registry = extend_receipt_registry(receipt_registry, payload)
    topology = MountedFieldTopology(topology_id, fibers, receipt_sha256(payload))
    topology.verify(registry)
    return topology, registry


@dataclass(frozen=True, slots=True)
class MountedSixLaneRuntime:
    """One frozen, fully cross-verified authority set for the mounted
    six-lane runtime (governing spec section 9.2): every one of the thirteen
    named authorities, chained through one continuously-extended
    :class:`ReceiptRegistry`.
    """

    story_chemistry_runtime: StoryChemistryRuntime
    story_native_replay_profile: MountedStoryNativeReplayProfile
    field_topology: MountedFieldTopology
    causal_grid: CausalGrid
    support_domain: MountedSupportDomain
    resonance_graph: MountedResonanceGraph
    resonance_operator: ResonanceOperatorAuthority
    sensor_states: tuple[MountedStorySensorState, ...]
    typed_language_kernel_binding: MountedTypedLanguageKernelBinding
    precision_authority: PrecisionScheduleAuthority
    expression_mode_bank: ExpressionModeBank
    pre_window_state: MountedPreWindowState
    l5_governance_profile: MountedL5GovernanceProfile
    story_global_uf_basin_profile: MountedStoryGlobalUFBasinProfile
    receipt_registry: ReceiptRegistry


def mount_six_lane_runtime(
    *,
    # -- 1. story chemistry (the five real, authenticated senses) --
    story_chemistry_profile_bytes: bytes,
    story_chemistry_authentication_key: bytes,
    story_chemistry_expected_key_id: str,
    sensor_ports: Sequence[StorySensorPortAuthority],
    sensor_port_receipt_payloads: Sequence[bytes],
    # -- five-sense field topology --
    five_sense_topology_id: str,
    # -- shared causal grid (the one causal window every lane, and the story
    #    native-replay profile below, must agree on) --
    causal_grid_id: str,
    causal_timestamps: Sequence[Fraction],
    causal_positive_weights: Sequence[Fraction],
    # -- five-sense support domain + resonance graph, needed only to
    #    assemble the story native-replay profile below --
    five_sense_support_domain_id: str,
    five_sense_resonance_graph_id: str,
    five_sense_resonance_required_edges: Sequence[RequiredEdge],
    # -- shared resonance operator (reused unchanged across the five-sense
    #    and six-lane resonance graphs: same operator_id/precision_bits) --
    resonance_operator_id: str,
    resonance_precision_bits: int,
    # -- story native-replay profile (item 2 of 13) --
    story_replay_profile_id: str,
    story_replay_provider_id: str,
    story_replay_kernel_adapter_id: str,
    story_replay_kernel_adapter_profile_payload: bytes,
    # -- typed-language kernel binding --
    typed_language_adapter_id: str,
    typed_language_interface_id: str,
    typed_language_phase_calibration_id: str,
    typed_language_phase_kappa: Fraction,
    typed_language_derivation_payload: bytes,
    language_port_id: str,
    # -- six-lane field topology, support domain, resonance graph --
    six_lane_topology_id: str,
    six_lane_support_domain_id: str,
    six_lane_resonance_graph_id: str,
    six_lane_resonance_required_edges: Sequence[RequiredEdge],
    # -- expression precision authority + genesis expression mode bank --
    expression_precision_authority_id: str,
    expression_maximum_precision_bits: int,
    # -- pre-window state --
    pre_window_state_id: str,
    pre_window_memory_state_payload: bytes,
    pre_window_l6_state_payload: bytes,
    # -- L5 applicability profile --
    l5_governance_profile_id: str,
    # -- field/basin profile --
    basin_profile_id: str,
    basin_physical_profile_payload: bytes,
    basin_hbar: Fraction,
    basin_source_time_unit: str,
    basin_max_connected_component_dimension: int,
    basin_field_precision_bits: int,
    basin_hamiltonian: Sequence[HamiltonianEntry] = (),
    basin_local_rates: Sequence[LocalRate] = (),
    five_sense_support_required_port_keys: Sequence[PortKey] | None = None,
    six_lane_support_required_port_keys: Sequence[PortKey] | None = None,
) -> MountedSixLaneRuntime:
    """Mount and cross-verify one complete six-lane runtime authority set.

    This is the single production owner governing spec section 9.2 calls
    for: it builds all thirteen named authorities -- story chemistry
    runtime, story native-replay profile, field topology, causal grid,
    support domain, resonance graph and operator, sensor states, typed-
    language kernel binding, precision authority, expression mode bank,
    pre-window state, L5 applicability profile, and field/basin profile --
    from caller-supplied raw inputs, chaining one :class:`ReceiptRegistry`
    through every one of them in the real dependency order
    ``tests/glew_runtime/test_story_global_uf_basin.py::
    _mounted_six_lane_preparation`` proves works: chemistry -> five-sense
    topology -> causal grid -> five-sense support domain -> five-sense
    resonance graph/operator -> sensor states -> story native-replay profile
    -> typed-language kernel binding -> six-lane topology -> six-lane
    support domain -> six-lane resonance graph -> precision authority ->
    expression mode bank -> pre-window state -> L5 governance profile ->
    field/basin profile.

    ``MountedStoryNativeReplayProfile.verify`` requires the registry itself
    to be rooted at its own receipt (see :func:`_reroot_registry`), so the
    returned ``receipt_registry`` is rooted at the story native-replay
    profile's own payload, not at the story chemistry manifest's -- every
    authority mounted before that point is carried forward unchanged, and
    every authority mounted after it is chained onto the new root via the
    ordinary :func:`extend_receipt_registry`.

    Four caller-supplied inputs remain genuinely opaque, undecided receipt
    payloads because no ratified derivation or production constructor exists
    yet anywhere in this repository for them (the same documented class of
    gap as ``StorySensorPortAuthority`` in :func:`mount_story_sensor_states`):
    ``story_replay_kernel_adapter_profile_payload``,
    ``pre_window_memory_state_payload``, ``pre_window_l6_state_payload``, and
    ``basin_physical_profile_payload``. ``sensor_ports`` and
    ``sensor_port_receipt_payloads`` (each port's own authority receipt plus
    its referenced boundary-source authority receipt -- exactly the extra
    payloads ``tests/glew_runtime/test_story_native_replay.py``'s own
    ``_sensor_port`` helper returns alongside each mounted port) are likewise
    caller-supplied for the same reason.
    """

    mounted_chemistry = mount_story_chemistry(
        manifest_envelope_payload=story_chemistry_profile_bytes,
        trusted_authentication_key=story_chemistry_authentication_key,
        expected_key_id=story_chemistry_expected_key_id,
    )
    if mounted_chemistry.status is not StoryChemistryStatus.MOUNTED or mounted_chemistry.runtime is None:
        raise ReceiptError(
            "six-lane runtime requires a mounted story chemistry manifest: "
            f"{mounted_chemistry.reason}"
        )
    story_runtime = mounted_chemistry.runtime
    registry = extend_receipt_registry(
        story_runtime.receipt_registry, *sensor_port_receipt_payloads
    )

    five_sense_topology, registry = mount_field_topology(
        topology_id=five_sense_topology_id,
        manifest=story_runtime.manifest,
        receipt_registry=registry,
    )

    causal_grid, registry = mount_causal_grid(
        grid_id=causal_grid_id,
        timestamps=causal_timestamps,
        positive_weights=causal_positive_weights,
        receipt_registry=registry,
    )

    five_sense_support, registry = mount_support_domain(
        domain_id=five_sense_support_domain_id,
        topology=five_sense_topology,
        receipt_registry=registry,
        required_port_keys=five_sense_support_required_port_keys,
    )

    five_sense_resonance_graph, resonance_operator, registry = mount_resonance_graph_and_operator(
        graph_id=five_sense_resonance_graph_id,
        required_edges=five_sense_resonance_required_edges,
        operator_id=resonance_operator_id,
        precision_bits=resonance_precision_bits,
        receipt_registry=registry,
        topology=five_sense_topology,
    )

    sensor_ports_tuple = tuple(sensor_ports)
    sensor_states, registry = mount_story_sensor_states(
        manifest=story_runtime.manifest,
        ports=sensor_ports_tuple,
        receipt_registry=registry,
    )

    kernel_adapter_registry = extend_receipt_registry(
        registry, story_replay_kernel_adapter_profile_payload
    )
    kernel_adapter_profile_receipt_sha256 = receipt_sha256(
        story_replay_kernel_adapter_profile_payload
    )
    story_replay_profile_payload = story_native_replay_profile_receipt_payload(
        profile_id=story_replay_profile_id,
        provider_id=story_replay_provider_id,
        topology_authority_receipt_sha256=five_sense_topology.authority_receipt_sha256,
        grid_receipt_sha256=causal_grid.grid_receipt_sha256,
        support_domain_receipt_sha256=five_sense_support.authority_receipt_sha256,
        resonance_graph_receipt_sha256=five_sense_resonance_graph.authority_receipt_sha256,
        resonance_operator_receipt_sha256=resonance_operator.authority_receipt_sha256,
        kernel_adapter_id=story_replay_kernel_adapter_id,
        kernel_adapter_profile_receipt_sha256=kernel_adapter_profile_receipt_sha256,
        ports=sensor_ports_tuple,
    )
    registry = _reroot_registry(
        profile_payload=story_replay_profile_payload,
        prior_registry=kernel_adapter_registry,
    )
    story_replay_profile = MountedStoryNativeReplayProfile(
        profile_id=story_replay_profile_id,
        provider_id=story_replay_provider_id,
        topology=five_sense_topology,
        grid=causal_grid,
        support_domain=five_sense_support,
        resonance_graph=five_sense_resonance_graph,
        resonance_operator=resonance_operator,
        kernel_adapter_id=story_replay_kernel_adapter_id,
        kernel_adapter_profile_receipt_sha256=kernel_adapter_profile_receipt_sha256,
        ports=sensor_ports_tuple,
        authority_receipt_sha256=receipt_sha256(story_replay_profile_payload),
        authority_receipt_payload=story_replay_profile_payload,
    )
    story_replay_profile.verify(registry)

    typed_language_binding, registry = mount_typed_language_kernel_binding(
        adapter_id=typed_language_adapter_id,
        interface_id=typed_language_interface_id,
        phase_calibration_id=typed_language_phase_calibration_id,
        phase_kappa=typed_language_phase_kappa,
        derivation_payload=typed_language_derivation_payload,
        receipt_registry=registry,
    )

    six_lane_topology, registry = _mount_six_lane_topology(
        topology_id=six_lane_topology_id,
        five_sense_topology=five_sense_topology,
        language_port_id=language_port_id,
        receipt_registry=registry,
    )

    six_lane_support, registry = mount_support_domain(
        domain_id=six_lane_support_domain_id,
        topology=six_lane_topology,
        receipt_registry=registry,
        required_port_keys=six_lane_support_required_port_keys,
    )

    six_lane_resonance_graph, six_lane_resonance_operator, registry = mount_resonance_graph_and_operator(
        graph_id=six_lane_resonance_graph_id,
        required_edges=six_lane_resonance_required_edges,
        operator_id=resonance_operator_id,
        precision_bits=resonance_precision_bits,
        receipt_registry=registry,
        topology=six_lane_topology,
    )

    precision_authority, registry = mount_precision_schedule_authority(
        authority_id=expression_precision_authority_id,
        maximum_precision_bits=expression_maximum_precision_bits,
        receipt_registry=registry,
    )

    mode_bank, registry = mount_expression_mode_bank(
        topology=six_lane_topology,
        precision_authority=precision_authority,
        receipt_registry=registry,
    )

    genesis_time = sensor_states[0].last_timestamp
    if any(state.last_timestamp != genesis_time for state in sensor_states):
        raise ReceiptError(
            "six-lane pre-window state requires every mounted sensor state to "
            "share one common genesis instant"
        )
    zero_amplitudes = tuple(
        ExactComplex(Fraction(0)) for _ in range(six_lane_topology.dimension)
    )
    initial_field_payload = exact_field_state_receipt_payload(
        six_lane_topology.authority_receipt_sha256, genesis_time, zero_amplitudes
    )
    registry = extend_receipt_registry(registry, initial_field_payload)
    initial_field_state = ExactFieldState(
        six_lane_topology.authority_receipt_sha256,
        genesis_time,
        zero_amplitudes,
        receipt_sha256(initial_field_payload),
    )
    initial_field_state.verify(registry)

    chemistry_state_payload = story_replay_chemistry_state_receipt_payload(
        story_runtime=story_runtime, sensor_states=sensor_states
    )
    registry = extend_receipt_registry(
        registry,
        chemistry_state_payload,
        pre_window_memory_state_payload,
        pre_window_l6_state_payload,
    )
    pre_window_state, registry = mount_pre_window_state(
        state_id=pre_window_state_id,
        chemistry_state_receipt_sha256=receipt_sha256(chemistry_state_payload),
        field_state=initial_field_state,
        mode_bank=mode_bank,
        memory_state_receipt_sha256=receipt_sha256(pre_window_memory_state_payload),
        l6_state_receipt_sha256=receipt_sha256(pre_window_l6_state_payload),
        topology=six_lane_topology,
        receipt_registry=registry,
    )

    l5_profile, registry = mount_l5_governance_profile(
        profile_id=l5_governance_profile_id,
        topology=six_lane_topology,
        receipt_registry=registry,
    )

    basin_profile, registry = mount_story_global_uf_basin_profile(
        profile_id=basin_profile_id,
        story_profile=story_replay_profile,
        physical_profile_payload=basin_physical_profile_payload,
        initial_field_state=initial_field_state,
        hbar=basin_hbar,
        hamiltonian=tuple(basin_hamiltonian),
        local_rates=tuple(basin_local_rates),
        source_time_unit=basin_source_time_unit,
        max_connected_component_dimension=basin_max_connected_component_dimension,
        field_precision_bits=basin_field_precision_bits,
        precision_authority=precision_authority,
        mode_bank=mode_bank,
        l5_governance=l5_profile,
        pre_window_state=pre_window_state,
        topology=six_lane_topology,
        receipt_registry=registry,
    )

    return MountedSixLaneRuntime(
        story_chemistry_runtime=story_runtime,
        story_native_replay_profile=story_replay_profile,
        field_topology=six_lane_topology,
        causal_grid=causal_grid,
        support_domain=six_lane_support,
        resonance_graph=six_lane_resonance_graph,
        resonance_operator=six_lane_resonance_operator,
        sensor_states=sensor_states,
        typed_language_kernel_binding=typed_language_binding,
        precision_authority=precision_authority,
        expression_mode_bank=mode_bank,
        pre_window_state=pre_window_state,
        l5_governance_profile=l5_profile,
        story_global_uf_basin_profile=basin_profile,
        receipt_registry=registry,
    )


__all__ = (
    "MountedSixLaneRuntime",
    "extend_receipt_registry",
    "mount_causal_grid",
    "mount_expression_mode_bank",
    "mount_field_topology",
    "mount_l5_governance_profile",
    "mount_precision_schedule_authority",
    "mount_pre_window_state",
    "mount_resonance_graph_and_operator",
    "mount_six_lane_runtime",
    "mount_story_global_uf_basin_profile",
    "mount_story_sensor_states",
    "mount_support_domain",
    "mount_typed_language_kernel_binding",
)
