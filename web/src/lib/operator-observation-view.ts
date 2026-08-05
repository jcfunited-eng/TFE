const GUALA_OBSERVATION_SCHEMA =
  "guala.observation_snapshot.v5";
const FULL_FIELD_NAMES = [
  "D_k",
  "M_k",
  "R_rev_k",
  "U_star_k",
  "C_k",
  "P_k",
  "B_k",
] as const;

export type ObservationDisplayState =
  | "available"
  | "quiescent"
  | "unknown"
  | "unavailable";

export type ObservationDisplay = {
  state: ObservationDisplayState;
  text: string;
};

export type FullFieldDisplayRow = {
  sense: string;
  state: string;
  substream: string;
  tuple: string;
  fields: string;
};

export const BRAIN_WIRING_PANEL_SPECS = [
  { key: "neuron_population", title: "Neuron population" },
  {
    key: "internal_neurochemical_flow",
    title: "Internal neurochemical flow",
  },
  { key: "tapestry_relations", title: "Tapestry and relations" },
  {
    key: "recognition_attention",
    title: "Recognition and attention",
  },
  {
    key: "other_perspective_model",
    title: "Other-perspective model",
  },
  {
    key: "reflection_meta_monitor",
    title: "Reflection and meta-monitor",
  },
  {
    key: "durable_sensed_consequence",
    title: "Durable sensed consequence",
  },
  { key: "dream_wake_weave", title: "Dream / wake / weave" },
  {
    key: "embodied_glyph_curriculum",
    title: "Embodied glyph curriculum",
  },
  {
    key: "embodied_reading_lesson_controller",
    title: "Embodied reading lesson boundary",
  },
  {
    key: "mechanism_counts_states",
    title: "Mechanism counts and states",
  },
  {
    key: "cold_persistence_bounds",
    title: "Cold and persistence bounds",
  },
] as const;

export type BrainWiringPanel = {
  key: (typeof BRAIN_WIRING_PANEL_SPECS)[number]["key"];
  title: string;
  value: ObservationDisplay;
};

export type OperatorObservationView = {
  identity: string;
  tick: string;
  receipt: string;
  passiveLearning: ObservationDisplay;
  permanentWiring: ObservationDisplay;
  latestResolution: ObservationDisplay;
  reciprocalExactTrace: ObservationDisplay;
  masterSense: ObservationDisplay;
  persistenceDiary: ObservationDisplay;
  physicalBytes: ObservationDisplay;
  cognitiveProgression: ObservationDisplay;
  dreaming: ObservationDisplay;
  fullFieldContract: ObservationDisplay;
  fullFieldRows: FullFieldDisplayRow[];
  brainWiringPanels: BrainWiringPanel[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasOwn(value: unknown, key: string): boolean {
  return isRecord(value) && Object.hasOwn(value, key);
}

function exactText(value: unknown): string {
  if (value === null) return "null";
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  return JSON.stringify(value, null, 2);
}

function recordDisplay(value: unknown): ObservationDisplay {
  if (!isRecord(value)) {
    return { state: "unknown", text: "unknown / not supplied" };
  }
  const status =
    typeof value.status === "string"
      ? value.status
      : typeof value.state === "string"
        ? value.state
        : typeof value.available === "boolean"
          ? value.available
            ? "available"
            : "unavailable"
          : "served without status";
  const unavailable =
    value.available === false ||
    status === "unavailable" ||
    status === "retired" ||
    status === "not_mounted";
  const quiescent = status === "quiescent";
  const unknown = status === "unknown" || status === "not_observed";
  return {
    state: unavailable
      ? "unavailable"
      : quiescent
        ? "quiescent"
        : unknown
          ? "unknown"
          : "available",
    text: exactText(value),
  };
}

function brainRecordDisplay(value: unknown): ObservationDisplay {
  if (!isRecord(value)) {
    return {
      state: "unavailable",
      text: "unavailable / not supplied",
    };
  }
  return recordDisplay(value);
}

export function projectOperatorObservation(
  snapshot: unknown,
): OperatorObservationView {
  if (
    !isRecord(snapshot) ||
    snapshot.schema !== GUALA_OBSERVATION_SCHEMA
  ) {
    throw new Error("observation_snapshot.v5 unavailable");
  }
  const passive = isRecord(
    snapshot.passive_whole_organism_thing_learning,
  )
    ? snapshot.passive_whole_organism_thing_learning
    : null;
  const persistence = isRecord(snapshot.persistence_health)
    ? snapshot.persistence_health
    : null;
  const authority = isRecord(snapshot.full_field_authority)
    ? snapshot.full_field_authority
    : null;
  const contract =
    authority && isRecord(authority.view_contract)
      ? authority.view_contract
      : null;
  const required =
    contract && Array.isArray(contract.required_fields)
      ? contract.required_fields
      : [];
  const completeField =
    required.length === FULL_FIELD_NAMES.length &&
    FULL_FIELD_NAMES.every((name, index) => required[index] === name);

  const fullFieldRows: FullFieldDisplayRow[] = [];
  const senses =
    authority && Array.isArray(authority.senses)
      ? authority.senses
      : [];
  for (const senseValue of senses) {
    if (!isRecord(senseValue)) continue;
    const substreams = Array.isArray(senseValue.substreams)
      ? senseValue.substreams
      : [];
    for (const substreamValue of substreams) {
      if (!isRecord(substreamValue)) continue;
      const fields = Array.isArray(substreamValue.fields)
        ? substreamValue.fields
        : [];
      const names = fields.map((field) =>
        Array.isArray(field) && field.length === 2 ? field[0] : null,
      );
      const completeTuple =
        names.length === FULL_FIELD_NAMES.length &&
        FULL_FIELD_NAMES.every((name, index) => names[index] === name);
      fullFieldRows.push({
        sense: exactText(senseValue.sense ?? "unknown"),
        state: exactText(senseValue.state ?? "unknown"),
        substream: exactText(
          substreamValue.substream_id ?? "unavailable",
        ),
        tuple: exactText(
          hasOwn(substreamValue, "tuple_index")
            ? substreamValue.tuple_index
            : "unavailable",
        ),
        fields: completeTuple
          ? fields
              .map((field) => {
                const pair = field as [unknown, unknown];
                return `${exactText(pair[0])}=${exactText(pair[1])}`;
              })
              .join(" · ")
          : "complete field unavailable",
      });
    }
  }

  const fieldStatus = recordDisplay(authority);
  const fieldContractText = contract
    ? [
        fieldStatus.text,
        `decision authority ${
          contract.decision_authority === false ? "false" : "unknown"
        }`,
        `field order ${completeField ? "complete" : "unknown"}`,
        `projection ${exactText(contract.projection ?? "unknown")}`,
        `projection loss ${exactText(
          contract.projection_loss ?? "unknown / not supplied",
        )}`,
      ].join(" · ")
    : "unknown / not supplied";

  const masterSense: ObservationDisplay =
    passive && hasOwn(passive, "master_sense")
      ? {
          state: "available",
          text:
            passive.master_sense === null
              ? "master_sense: none"
              : `master_sense: ${exactText(passive.master_sense)}`,
        }
      : { state: "unknown", text: "unknown / not supplied" };

  return {
    identity:
      typeof snapshot.identity === "string" && snapshot.identity
        ? snapshot.identity
        : "identity unavailable",
    tick: Number.isSafeInteger(snapshot.observed_at_tick)
      ? String(snapshot.observed_at_tick)
      : "unknown",
    receipt:
      typeof snapshot.snapshot_receipt_sha256 === "string" &&
      /^[0-9a-f]{64}$/.test(snapshot.snapshot_receipt_sha256)
        ? snapshot.snapshot_receipt_sha256
        : "unavailable",
    passiveLearning: recordDisplay(passive),
    permanentWiring: recordDisplay(
      passive?.whole_organism_permanent_wiring,
    ),
    latestResolution: recordDisplay(passive?.latest_resolution),
    reciprocalExactTrace: recordDisplay(
      passive?.reciprocal_exact_trace,
    ),
    masterSense,
    persistenceDiary: recordDisplay(persistence?.diary),
    physicalBytes: recordDisplay(persistence?.physical_bytes),
    cognitiveProgression: recordDisplay(
      snapshot.whole_organism_cognitive_progression,
    ),
    dreaming: recordDisplay(snapshot.dreaming),
    fullFieldContract: {
      state:
        authority?.available === true && completeField
          ? "available"
          : fieldStatus.state,
      text: fieldContractText,
    },
    fullFieldRows,
    brainWiringPanels: BRAIN_WIRING_PANEL_SPECS.map((panel) => ({
      key: panel.key,
      title: panel.title,
      value: brainRecordDisplay(snapshot[panel.key]),
    })),
  };
}
