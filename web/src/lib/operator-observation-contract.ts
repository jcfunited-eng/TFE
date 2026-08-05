export const GUALA_OBSERVATION_PATH =
  "/api/v1/gualaloom/observation";
export const GUALA_OBSERVATION_SCHEMA =
  "guala.observation_snapshot.v5";
export const WHOLE_ORGANISM_WIRING_SCHEMA =
  "guala.whole_organism.permanent_wiring.observation.v2";
export const WHOLE_ORGANISM_MANIFEST_SCHEMA =
  "guala.whole_organism.manifest_state.v1";
export const WHOLE_ORGANISM_LATEST_ACTIVITY_SCHEMA =
  "guala.whole_organism.latest_episode_activity.v1";
export const WHOLE_ORGANISM_CURRENT_OWNER_SCHEMA =
  "guala.whole_organism.current_owner_state.v1";
export const FULL_FIELD_NAMES = [
  "D_k",
  "M_k",
  "R_rev_k",
  "U_star_k",
  "C_k",
  "P_k",
  "B_k",
] as const;
export const MAX_GUALA_OBSERVATION_BYTES = 2_097_152;

type JsonScalar = string | number | boolean | null;
export type ObservationJson =
  | JsonScalar
  | ObservationJson[]
  | { [key: string]: ObservationJson };

export type GualaObservationSnapshot = {
  [key: string]: ObservationJson | undefined;
  schema: typeof GUALA_OBSERVATION_SCHEMA;
  observed_at_tick: number;
  identity: string;
  snapshot_receipt_sha256: string;
  full_field_authority: {
    [key: string]: ObservationJson;
    view_contract: {
      [key: string]: ObservationJson;
      decision_authority: false;
      projection: string;
      projection_loss: string;
      required_fields: string[];
    };
    senses: ObservationJson[];
  };
  passive_whole_organism_thing_learning: {
    [key: string]: ObservationJson;
    master_sense: ObservationJson;
    whole_organism_permanent_wiring: {
      [key: string]: ObservationJson;
      schema: typeof WHOLE_ORGANISM_WIRING_SCHEMA;
      manifest_state: {
        [key: string]: ObservationJson;
        schema: typeof WHOLE_ORGANISM_MANIFEST_SCHEMA;
      };
      latest_episode_activity: {
        [key: string]: ObservationJson;
        schema: typeof WHOLE_ORGANISM_LATEST_ACTIVITY_SCHEMA;
      };
      current_owner_state: {
        [key: string]: ObservationJson;
        schema: typeof WHOLE_ORGANISM_CURRENT_OWNER_SCHEMA;
      };
    };
    latest_resolution: ObservationJson;
    reciprocal_exact_trace: {
      [key: string]: ObservationJson;
    };
  };
  persistence_health: {
    [key: string]: ObservationJson;
    diary: {
      [key: string]: ObservationJson;
    };
    physical_bytes: {
      [key: string]: ObservationJson;
    };
  };
  whole_organism_cognitive_progression: {
    [key: string]: ObservationJson;
  };
  dreaming: {
    [key: string]: ObservationJson;
  };
  neuron_population?: { [key: string]: ObservationJson };
  internal_neurochemical_flow?: { [key: string]: ObservationJson };
  tapestry_relations?: { [key: string]: ObservationJson };
  recognition_attention?: { [key: string]: ObservationJson };
  other_perspective_model?: { [key: string]: ObservationJson };
  reflection_meta_monitor?: { [key: string]: ObservationJson };
  durable_sensed_consequence?: { [key: string]: ObservationJson };
  dream_wake_weave?: { [key: string]: ObservationJson };
  embodied_glyph_curriculum?: { [key: string]: ObservationJson };
  embodied_reading_lesson_controller?: {
    [key: string]: ObservationJson;
  };
  mechanism_counts_states?: { [key: string]: ObservationJson };
  cold_persistence_bounds?: { [key: string]: ObservationJson };
};

export class OperatorObservationContractError extends Error {
  readonly httpStatus: number;
  readonly code: string;

  constructor(httpStatus: number, code: string) {
    super(code);
    this.name = "OperatorObservationContractError";
    this.httpStatus = httpStatus;
    this.code = code;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isSha256(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function validateBoundedJson(
  value: unknown,
  state: { nodes: number },
  depth: number,
): asserts value is ObservationJson {
  state.nodes += 1;
  if (state.nodes > 16_384 || depth > 16) {
    throw new OperatorObservationContractError(
      502,
      "upstream_observation_exceeds_structure_limit",
    );
  }
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new OperatorObservationContractError(
        502,
        "upstream_observation_number_invalid",
      );
    }
    return;
  }
  if (typeof value === "string") {
    if (
      new TextEncoder().encode(value).byteLength >
      MAX_GUALA_OBSERVATION_BYTES
    ) {
      throw new OperatorObservationContractError(
        502,
        "upstream_observation_string_too_long",
      );
    }
    return;
  }
  if (Array.isArray(value)) {
    if (value.length > 4_096) {
      throw new OperatorObservationContractError(
        502,
        "upstream_observation_array_too_long",
      );
    }
    for (const item of value) {
      validateBoundedJson(item, state, depth + 1);
    }
    return;
  }
  if (!isRecord(value) || Object.keys(value).length > 512) {
    throw new OperatorObservationContractError(
      502,
      "upstream_observation_object_invalid",
    );
  }
  for (const [key, item] of Object.entries(value)) {
    if (!key || key.length > 256) {
      throw new OperatorObservationContractError(
        502,
        "upstream_observation_key_invalid",
      );
    }
    validateBoundedJson(item, state, depth + 1);
  }
}

function requireRecord(
  value: unknown,
  errorCode: string,
): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new OperatorObservationContractError(502, errorCode);
  }
  return value;
}

function validateFullField(value: unknown): void {
  const authority = requireRecord(
    value,
    "upstream_full_field_authority_invalid",
  );
  const contract = requireRecord(
    authority.view_contract,
    "upstream_full_field_contract_invalid",
  );
  const requiredFields = contract.required_fields;
  if (
    contract.decision_authority !== false ||
    typeof contract.projection !== "string" ||
    typeof contract.projection_loss !== "string" ||
    !Array.isArray(requiredFields) ||
    requiredFields.length !== FULL_FIELD_NAMES.length ||
    !FULL_FIELD_NAMES.every(
      (name, index) => requiredFields[index] === name,
    ) ||
    !Array.isArray(authority.senses)
  ) {
    throw new OperatorObservationContractError(
      502,
      "upstream_full_field_contract_invalid",
    );
  }
  for (const senseValue of authority.senses) {
    const sense = requireRecord(
      senseValue,
      "upstream_full_field_sense_invalid",
    );
    if (!Array.isArray(sense.substreams)) {
      throw new OperatorObservationContractError(
        502,
        "upstream_full_field_sense_invalid",
      );
    }
    for (const substreamValue of sense.substreams) {
      const substream = requireRecord(
        substreamValue,
        "upstream_full_field_substream_invalid",
      );
      if (
        !Array.isArray(substream.fields) ||
        substream.fields.length !== FULL_FIELD_NAMES.length
      ) {
        throw new OperatorObservationContractError(
          502,
          "upstream_full_field_tuple_invalid",
        );
      }
      for (let index = 0; index < FULL_FIELD_NAMES.length; index += 1) {
        const field = substream.fields[index];
        if (
          !Array.isArray(field) ||
          field.length !== 2 ||
          field[0] !== FULL_FIELD_NAMES[index]
        ) {
          throw new OperatorObservationContractError(
            502,
            "upstream_full_field_tuple_invalid",
          );
        }
      }
    }
  }
}

function validatePermanentWiring(value: unknown): void {
  const wiring = requireRecord(
    value,
    "upstream_permanent_wiring_invalid",
  );
  const manifest = requireRecord(
    wiring.manifest_state,
    "upstream_permanent_wiring_manifest_invalid",
  );
  const activity = requireRecord(
    wiring.latest_episode_activity,
    "upstream_permanent_wiring_activity_invalid",
  );
  const counts = requireRecord(
    activity.activity_counts,
    "upstream_permanent_wiring_activity_invalid",
  );
  const current = requireRecord(
    wiring.current_owner_state,
    "upstream_permanent_wiring_current_state_invalid",
  );
  const currentMechanisms = requireRecord(
    current.mechanisms,
    "upstream_permanent_wiring_current_state_invalid",
  );
  if (
    wiring.schema !== WHOLE_ORGANISM_WIRING_SCHEMA ||
    wiring.status !== "mounted" ||
    manifest.schema !== WHOLE_ORGANISM_MANIFEST_SCHEMA ||
    manifest.status !== "mounted" ||
    manifest.mechanism_count !== 28 ||
    !isSha256(manifest.manifest_receipt_sha256) ||
    !Array.isArray(manifest.mechanisms) ||
    manifest.mechanisms.length !== 28 ||
    activity.schema !== WHOLE_ORGANISM_LATEST_ACTIVITY_SCHEMA ||
    current.schema !== WHOLE_ORGANISM_CURRENT_OWNER_SCHEMA ||
    current.status !== "observed" ||
    Object.keys(currentMechanisms).length !== 28
  ) {
    throw new OperatorObservationContractError(
      502,
      "upstream_permanent_wiring_invalid",
    );
  }
  if (activity.status === "not_observed_since_process_start") {
    if (
      activity.contribution_states !== null ||
      counts.perturbed !== null ||
      counts.quiescent !== null ||
      counts.unavailable !== null
    ) {
      throw new OperatorObservationContractError(
        502,
        "upstream_permanent_wiring_activity_invalid",
      );
    }
    return;
  }
  if (
    activity.status !== "observed" ||
    !isRecord(activity.contribution_states) ||
    Object.keys(activity.contribution_states).length !== 28 ||
    !Number.isSafeInteger(counts.perturbed) ||
    !Number.isSafeInteger(counts.quiescent) ||
    !Number.isSafeInteger(counts.unavailable) ||
    Number(counts.perturbed) < 0 ||
    Number(counts.quiescent) < 0 ||
    Number(counts.unavailable) < 0 ||
    Number(counts.perturbed) +
      Number(counts.quiescent) +
      Number(counts.unavailable) !==
      28
  ) {
    throw new OperatorObservationContractError(
      502,
      "upstream_permanent_wiring_activity_invalid",
    );
  }
}

export function validateObservationSnapshot(
  value: unknown,
): GualaObservationSnapshot {
  validateBoundedJson(value, { nodes: 0 }, 0);
  const snapshot = requireRecord(
    value,
    "upstream_observation_schema_invalid",
  );
  if (
    snapshot.schema !== GUALA_OBSERVATION_SCHEMA ||
    !Number.isSafeInteger(snapshot.observed_at_tick) ||
    Number(snapshot.observed_at_tick) < 0 ||
    typeof snapshot.identity !== "string" ||
    !snapshot.identity ||
    !isSha256(snapshot.snapshot_receipt_sha256)
  ) {
    throw new OperatorObservationContractError(
      502,
      "upstream_observation_schema_invalid",
    );
  }

  validateFullField(snapshot.full_field_authority);
  const passive = requireRecord(
    snapshot.passive_whole_organism_thing_learning,
    "upstream_passive_learning_invalid",
  );
  validatePermanentWiring(
    passive.whole_organism_permanent_wiring,
  );
  if (!Object.hasOwn(passive, "latest_resolution")) {
    throw new OperatorObservationContractError(
      502,
      "upstream_latest_resolution_missing",
    );
  }
  requireRecord(
    passive.reciprocal_exact_trace,
    "upstream_reciprocal_trace_invalid",
  );
  if (!Object.hasOwn(passive, "master_sense")) {
    throw new OperatorObservationContractError(
      502,
      "upstream_master_sense_missing",
    );
  }

  const persistence = requireRecord(
    snapshot.persistence_health,
    "upstream_persistence_health_invalid",
  );
  requireRecord(
    persistence.diary,
    "upstream_persistence_diary_invalid",
  );
  requireRecord(
    persistence.physical_bytes,
    "upstream_physical_bytes_invalid",
  );
  requireRecord(
    snapshot.whole_organism_cognitive_progression,
    "upstream_cognitive_progression_invalid",
  );
  requireRecord(
    snapshot.dreaming,
    "upstream_dreaming_status_invalid",
  );
  return snapshot as GualaObservationSnapshot;
}

function parseRequiredApiOrigin(): URL {
  const configured = String(
    process.env.GUALA_OPERATOR_API_ORIGIN ?? "",
  ).trim();
  if (!configured) {
    throw new OperatorObservationContractError(
      500,
      "operator_api_origin_missing",
    );
  }
  let parsed: URL;
  try {
    parsed = new URL(configured);
  } catch {
    throw new OperatorObservationContractError(
      500,
      "operator_api_origin_invalid",
    );
  }
  if (
    parsed.protocol !== "https:" ||
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    (parsed.pathname !== "" && parsed.pathname !== "/")
  ) {
    throw new OperatorObservationContractError(
      500,
      "operator_api_origin_invalid",
    );
  }
  return new URL(parsed.origin);
}

function requireOperatorApiKey(): string {
  const key = String(process.env.GUALA_OPERATOR_API_KEY ?? "").trim();
  if (
    key.length < 16 ||
    key.length > 4_096 ||
    /[\u0000-\u001f\u007f]/.test(key)
  ) {
    throw new OperatorObservationContractError(
      500,
      "operator_api_key_unavailable",
    );
  }
  return key;
}

async function readBoundedJson(response: Response): Promise<unknown> {
  const declaredLength = response.headers.get("content-length");
  if (declaredLength !== null) {
    const parsedLength = Number(declaredLength);
    if (
      !Number.isSafeInteger(parsedLength) ||
      parsedLength < 0 ||
      parsedLength > MAX_GUALA_OBSERVATION_BYTES
    ) {
      throw new OperatorObservationContractError(
        502,
        "upstream_observation_too_large",
      );
    }
  }
  if (!response.body) {
    throw new OperatorObservationContractError(
      502,
      "upstream_observation_empty",
    );
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_GUALA_OBSERVATION_BYTES) {
      await reader.cancel();
      throw new OperatorObservationContractError(
        502,
        "upstream_observation_too_large",
      );
    }
    chunks.push(value);
  }
  const encoded = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    encoded.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(encoded));
  } catch {
    throw new OperatorObservationContractError(
      502,
      "upstream_observation_json_invalid",
    );
  }
}

export async function readOperatorObservation(): Promise<GualaObservationSnapshot> {
  const origin = parseRequiredApiOrigin();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(
      new URL(GUALA_OBSERVATION_PATH, origin),
      {
        method: "GET",
        redirect: "error",
        cache: "no-store",
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          "X-API-Key": requireOperatorApiKey(),
        },
      },
    );
    if (response.status !== 200) {
      throw new OperatorObservationContractError(
        502,
        "upstream_observation_failed",
      );
    }
    return validateObservationSnapshot(await readBoundedJson(response));
  } catch (error) {
    if (error instanceof OperatorObservationContractError) throw error;
    throw new OperatorObservationContractError(
      502,
      "upstream_observation_unavailable",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export function operatorObservationErrorResponse(error: unknown): {
  status: number;
  body: { schema: "tfe.guala.operator_observation.error.v1"; error: string };
} {
  if (error instanceof OperatorObservationContractError) {
    return {
      status: error.httpStatus,
      body: {
        schema: "tfe.guala.operator_observation.error.v1",
        error: error.code,
      },
    };
  }
  return {
    status: 500,
    body: {
      schema: "tfe.guala.operator_observation.error.v1",
      error: "operator_observation_failed",
    },
  };
}
