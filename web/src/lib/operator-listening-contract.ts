import { requireExternalOrigin } from "@/lib/external-url";
import { randomBytes } from "node:crypto";

export const OPERATOR_LISTENING_CSRF_HEADER =
  "x-tfe-operator-listening-csrf";
export const OPERATOR_LISTENING_CSRF_VALUE =
  "tfe.guala.operator_listening.csrf.v1";

export const BFF_START_REQUEST_SCHEMA =
  "tfe.guala.operator_listening.start.request.v1";
export const BFF_START_RESPONSE_SCHEMA =
  "tfe.guala.operator_listening.start.response.v1";
export const BFF_POLL_REQUEST_SCHEMA =
  "tfe.guala.operator_listening.poll.request.v1";
export const BFF_POLL_RESPONSE_SCHEMA =
  "tfe.guala.operator_listening.poll.response.v1";
export const BFF_ERROR_SCHEMA =
  "tfe.guala.operator_listening.error.v1";

/*
 * These four Guala constants are the isolated upstream adapter boundary.
 * The async Guala implementation must supply these exact paths and schemas;
 * the browser and page do not depend on them.
 */
export const GUALA_ASYNC_START_PATH =
  "/api/v1/embodiment/learned-body-act-trial";
export const GUALA_ASYNC_POLL_PATH =
  "/api/v1/embodiment/learned-body-act-trial";
export const GUALA_ASYNC_START_REQUEST_SCHEMA =
  "guala.embodiment.learned_body_act_trial.request.v1";
export const GUALA_ASYNC_START_RESPONSE_SCHEMA =
  "guala.embodiment.learned_body_act_trial.accepted.v1";
export const GUALA_ASYNC_POLL_RESPONSE_SCHEMA =
  "guala.embodiment.learned_body_act_trial.status.v1";

export const MAX_BROWSER_REQUEST_BYTES = 512;
export const MAX_GUALA_TRIAL_RESULT_BYTES = 475_480;
export const EMPTY_COMPLETED_STATUS_ENVELOPE_BYTES = 260;
export const MAX_UPSTREAM_TERMINAL_RESPONSE_BYTES =
  EMPTY_COMPLETED_STATUS_ENVELOPE_BYTES -
  2 +
  MAX_GUALA_TRIAL_RESULT_BYTES;
export const MIN_POLL_AFTER_MS = 250;
export const MAX_POLL_AFTER_MS = 5_000;
export const MIN_MATERIAL_ACTION_DURATION_US = 1_000;
export const MAX_MATERIAL_ACTION_DURATION_US = 5_000_000;
export const GUALA_SELF_BODY_PORT_ID = "guala.embodiment.w1";

const TASK_ID_PATTERN = /^[0-9a-f]{64}$/;
const MIN_POSITION_MM = -(2 ** 31);
const MAX_POSITION_MM = (2 ** 31) - 1;
const FORBIDDEN_OBSERVATION_KEYS = new Set([
  "expected_word",
  "expected_words",
  "ground_truth",
  "label",
  "labels",
  "target_word",
  "target_words",
]);

type JsonScalar = string | number | boolean | null;
export type BoundedJson =
  | JsonScalar
  | BoundedJson[]
  | { [key: string]: BoundedJson };

export type OperatorTaskStatus =
  | "accepted"
  | "processing"
  | "complete"
  | "failed";

type Position = {
  x_mm: number;
  y_mm: number;
  z_mm: number;
};

export type PhysicalActionChoice =
  | {
      operation: "move";
      duration_microseconds: number;
      target_pose: {
        position: Position;
        heading_millidegrees: number;
      };
    }
  | {
      operation: "pick";
      duration_microseconds: number;
      object_id: string;
    }
  | {
      operation: "place";
      duration_microseconds: number;
      object_id: string;
      target_position: Position;
    };

export type OperatorStartResult = {
  schema: typeof BFF_START_RESPONSE_SCHEMA;
  task_id: string;
  status: "accepted";
  poll_after_ms: number;
};

export type OperatorPollResult = {
  schema: typeof BFF_POLL_RESPONSE_SCHEMA;
  task_id: string;
  status: OperatorTaskStatus;
  poll_after_ms?: number;
  observation?: BoundedJson;
  failure_code?: string;
};

export class OperatorListeningContractError extends Error {
  readonly httpStatus: number;
  readonly code: string;

  constructor(httpStatus: number, code: string) {
    super(code);
    this.name = "OperatorListeningContractError";
    this.httpStatus = httpStatus;
    this.code = code;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(
  value: Record<string, unknown>,
  required: readonly string[],
  optional: readonly string[] = [],
): boolean {
  const actual = Object.keys(value).sort();
  const allowed = new Set([...required, ...optional]);
  if (!required.every((key) => Object.hasOwn(value, key))) return false;
  return actual.every((key) => allowed.has(key));
}

function boundedInteger(
  value: unknown,
  minimum: number,
  maximum: number,
): number {
  if (
    !Number.isInteger(value) ||
    Number(value) < minimum ||
    Number(value) > maximum
  ) {
    throw new OperatorListeningContractError(
      400,
      "material_action_integer_invalid",
    );
  }
  return Number(value);
}

function parsePosition(value: unknown): Position {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ["x_mm", "y_mm", "z_mm"])
  ) {
    throw new OperatorListeningContractError(
      400,
      "material_action_position_invalid",
    );
  }
  return {
    x_mm: boundedInteger(value.x_mm, MIN_POSITION_MM, MAX_POSITION_MM),
    y_mm: boundedInteger(value.y_mm, MIN_POSITION_MM, MAX_POSITION_MM),
    z_mm: boundedInteger(value.z_mm, MIN_POSITION_MM, MAX_POSITION_MM),
  };
}

function parseObjectId(value: unknown): string {
  if (
    typeof value !== "string" ||
    !value ||
    value.trim() !== value ||
    new TextEncoder().encode(value).byteLength > 256
  ) {
    throw new OperatorListeningContractError(
      400,
      "material_action_object_id_invalid",
    );
  }
  return value;
}

function parseMaterialAction(
  value: Record<string, unknown>,
): PhysicalActionChoice {
  const duration = boundedInteger(
    value.duration_microseconds,
    MIN_MATERIAL_ACTION_DURATION_US,
    MAX_MATERIAL_ACTION_DURATION_US,
  );
  if (value.operation === "move") {
    if (
      !hasExactKeys(value, [
        "schema",
        "operation",
        "duration_microseconds",
        "target_pose",
      ]) ||
      !isRecord(value.target_pose) ||
      !hasExactKeys(value.target_pose, [
        "position",
        "heading_millidegrees",
      ])
    ) {
      throw new OperatorListeningContractError(
        400,
        "material_action_move_invalid",
      );
    }
    return {
      operation: "move",
      duration_microseconds: duration,
      target_pose: {
        position: parsePosition(value.target_pose.position),
        heading_millidegrees: boundedInteger(
          value.target_pose.heading_millidegrees,
          0,
          359_999,
        ),
      },
    };
  }
  if (value.operation === "pick") {
    if (
      !hasExactKeys(value, [
        "schema",
        "operation",
        "duration_microseconds",
        "object_id",
      ])
    ) {
      throw new OperatorListeningContractError(
        400,
        "material_action_pick_invalid",
      );
    }
    return {
      operation: "pick",
      duration_microseconds: duration,
      object_id: parseObjectId(value.object_id),
    };
  }
  if (value.operation === "place") {
    if (
      !hasExactKeys(value, [
        "schema",
        "operation",
        "duration_microseconds",
        "object_id",
        "target_position",
      ])
    ) {
      throw new OperatorListeningContractError(
        400,
        "material_action_place_invalid",
      );
    }
    return {
      operation: "place",
      duration_microseconds: duration,
      object_id: parseObjectId(value.object_id),
      target_position: parsePosition(value.target_position),
    };
  }
  throw new OperatorListeningContractError(
    400,
    "material_action_operation_invalid",
  );
}

export function parseTaskId(value: unknown): string {
  if (typeof value !== "string" || !TASK_ID_PATTERN.test(value)) {
    throw new OperatorListeningContractError(400, "task_id_invalid");
  }
  return value;
}

function normalizeSemanticKey(value: string): string {
  return value.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function validateBoundedJson(
  value: unknown,
  state: { nodes: number },
  depth: number,
): asserts value is BoundedJson {
  state.nodes += 1;
  if (state.nodes > 512 || depth > 8) {
    throw new OperatorListeningContractError(
      502,
      "upstream_observation_exceeds_structure_limit",
    );
  }
  if (
    value === null ||
    typeof value === "boolean"
  ) {
    return;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new OperatorListeningContractError(
        502,
        "upstream_observation_number_invalid",
      );
    }
    return;
  }
  if (typeof value === "string") {
    if (
      new TextEncoder().encode(value).byteLength >
      MAX_UPSTREAM_TERMINAL_RESPONSE_BYTES
    ) {
      throw new OperatorListeningContractError(
        502,
        "upstream_observation_string_too_long",
      );
    }
    return;
  }
  if (Array.isArray(value)) {
    if (value.length > 128) {
      throw new OperatorListeningContractError(
        502,
        "upstream_observation_array_too_long",
      );
    }
    for (const item of value) {
      validateBoundedJson(item, state, depth + 1);
    }
    return;
  }
  if (!isRecord(value) || Object.keys(value).length > 64) {
    throw new OperatorListeningContractError(
      502,
      "upstream_observation_object_invalid",
    );
  }
  for (const [key, item] of Object.entries(value)) {
    if (!key || key.length > 64) {
      throw new OperatorListeningContractError(
        502,
        "upstream_observation_key_invalid",
      );
    }
    if (FORBIDDEN_OBSERVATION_KEYS.has(normalizeSemanticKey(key))) {
      throw new OperatorListeningContractError(
        502,
        "upstream_observation_contains_tutoring_answer",
      );
    }
    validateBoundedJson(item, state, depth + 1);
  }
}

async function readBoundedJson(response: Response): Promise<unknown> {
  const declaredLength = response.headers.get("content-length");
  if (declaredLength !== null) {
    const parsedLength = Number(declaredLength);
    if (
      !Number.isSafeInteger(parsedLength) ||
      parsedLength < 0 ||
      parsedLength > MAX_UPSTREAM_TERMINAL_RESPONSE_BYTES
    ) {
      throw new OperatorListeningContractError(
        502,
        "upstream_response_too_large",
      );
    }
  }
  if (!response.body) {
    throw new OperatorListeningContractError(502, "upstream_response_empty");
  }

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_UPSTREAM_TERMINAL_RESPONSE_BYTES) {
      await reader.cancel();
      throw new OperatorListeningContractError(
        502,
        "upstream_response_too_large",
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
    throw new OperatorListeningContractError(
      502,
      "upstream_response_json_invalid",
    );
  }
}

function parseRequiredApiOrigin(): URL {
  const configured = String(
    process.env.GUALA_OPERATOR_API_ORIGIN ?? "",
  ).trim();
  if (!configured) {
    throw new OperatorListeningContractError(
      500,
      "operator_api_origin_missing",
    );
  }

  let parsed: URL;
  try {
    parsed = new URL(configured);
  } catch {
    throw new OperatorListeningContractError(
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
    throw new OperatorListeningContractError(
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
    throw new OperatorListeningContractError(
      500,
      "operator_api_key_unavailable",
    );
  }
  return key;
}

export function enforceOperatorCsrf(request: Request): void {
  let configuredOrigin: URL;
  try {
    configuredOrigin = requireExternalOrigin();
  } catch {
    throw new OperatorListeningContractError(
      500,
      "public_base_url_unavailable",
    );
  }

  const suppliedOrigin = String(request.headers.get("origin") ?? "").trim();
  const fetchSite = String(
    request.headers.get("sec-fetch-site") ?? "",
  ).trim();
  const csrfValue = String(
    request.headers.get(OPERATOR_LISTENING_CSRF_HEADER) ?? "",
  );
  const mediaType = String(
    request.headers.get("content-type") ?? "",
  )
    .split(";", 1)[0]
    .trim()
    .toLowerCase();
  if (
    request.headers.has("authorization") ||
    request.headers.has("x-api-key")
  ) {
    throw new OperatorListeningContractError(
      400,
      "client_authority_header_forbidden",
    );
  }

  let parsedOrigin: URL;
  try {
    parsedOrigin = new URL(suppliedOrigin);
  } catch {
    throw new OperatorListeningContractError(403, "csrf_origin_invalid");
  }
  if (
    parsedOrigin.origin !== configuredOrigin.origin ||
    suppliedOrigin !== parsedOrigin.origin ||
    fetchSite !== "same-origin" ||
    csrfValue !== OPERATOR_LISTENING_CSRF_VALUE ||
    mediaType !== "application/json"
  ) {
    throw new OperatorListeningContractError(403, "csrf_check_failed");
  }
}

async function parseBrowserJson(
  request: Request,
): Promise<Record<string, unknown>> {
  const declaredLength = request.headers.get("content-length");
  if (declaredLength !== null) {
    const parsedLength = Number(declaredLength);
    if (
      !Number.isSafeInteger(parsedLength) ||
      parsedLength < 0 ||
      parsedLength > MAX_BROWSER_REQUEST_BYTES
    ) {
      throw new OperatorListeningContractError(413, "request_too_large");
    }
  }
  const encoded = await request.text();
  if (new TextEncoder().encode(encoded).byteLength > MAX_BROWSER_REQUEST_BYTES) {
    throw new OperatorListeningContractError(413, "request_too_large");
  }
  let value: unknown;
  try {
    value = JSON.parse(encoded);
  } catch {
    throw new OperatorListeningContractError(400, "request_json_invalid");
  }
  if (!isRecord(value)) {
    throw new OperatorListeningContractError(400, "request_schema_invalid");
  }
  return value;
}

export async function parseStartBrowserRequest(
  request: Request,
): Promise<PhysicalActionChoice> {
  enforceOperatorCsrf(request);
  const value = await parseBrowserJson(request);
  if (value.schema !== BFF_START_REQUEST_SCHEMA) {
    throw new OperatorListeningContractError(400, "request_schema_invalid");
  }
  return parseMaterialAction(value);
}

export async function parsePollBrowserRequest(
  request: Request,
): Promise<string> {
  enforceOperatorCsrf(request);
  const value = await parseBrowserJson(request);
  if (
    !hasExactKeys(value, ["schema", "task_id"]) ||
    value.schema !== BFF_POLL_REQUEST_SCHEMA
  ) {
    throw new OperatorListeningContractError(400, "request_schema_invalid");
  }
  return parseTaskId(value.task_id);
}

async function callGuala(
  path: string,
  method: "GET" | "POST",
  expectedStatuses: readonly number[],
  body?: Record<string, BoundedJson>,
): Promise<unknown> {
  const origin = parseRequiredApiOrigin();
  const apiKey = requireOperatorApiKey();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(new URL(path, origin), {
      method,
      redirect: "error",
      cache: "no-store",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "X-API-Key": apiKey,
        ...(body === undefined
          ? {}
          : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!expectedStatuses.includes(response.status)) {
      throw new OperatorListeningContractError(
        502,
        "upstream_request_failed",
      );
    }
    return await readBoundedJson(response);
  } catch (error) {
    if (error instanceof OperatorListeningContractError) throw error;
    throw new OperatorListeningContractError(
      502,
      "upstream_request_unavailable",
    );
  } finally {
    clearTimeout(timeout);
  }
}

function requireSelfBodyPortId(): string {
  const configured = String(
    process.env.GUALA_SELF_BODY_PORT_ID ?? "",
  ).trim();
  if (configured !== GUALA_SELF_BODY_PORT_ID) {
    throw new OperatorListeningContractError(
      500,
      "self_body_port_id_unavailable",
    );
  }
  return configured;
}

export async function startOperatorListening(
  action: PhysicalActionChoice,
): Promise<OperatorStartResult> {
  const nonce = randomBytes(32).toString("hex");
  const raw = await callGuala(
    GUALA_ASYNC_START_PATH,
    "POST",
    [202],
    {
      tutor_id: "joe",
      nonce,
      port_id: requireSelfBodyPortId(),
      ...action,
    },
  );
  if (
    !isRecord(raw) ||
    !hasExactKeys(raw, [
      "schema",
      "state",
      "operation_id",
      "request_sha256",
    ]) ||
    raw.schema !== GUALA_ASYNC_START_RESPONSE_SCHEMA ||
    raw.state !== "accepted" ||
    typeof raw.request_sha256 !== "string" ||
    !/^[0-9a-f]{64}$/.test(raw.request_sha256)
  ) {
    throw new OperatorListeningContractError(
      502,
      "upstream_start_schema_invalid",
    );
  }
  return {
    schema: BFF_START_RESPONSE_SCHEMA,
    task_id: parseTaskId(raw.operation_id),
    status: "accepted",
    poll_after_ms: 500,
  };
}

export async function pollOperatorListening(
  taskId: string,
): Promise<OperatorPollResult> {
  const parsedTaskId = parseTaskId(taskId);
  const raw = await callGuala(
    `${GUALA_ASYNC_POLL_PATH}/${parsedTaskId}`,
    "GET",
    [200, 202, 409],
  );
  if (
    !isRecord(raw) ||
    raw.schema !== GUALA_ASYNC_POLL_RESPONSE_SCHEMA ||
    raw.operation_id !== parsedTaskId ||
    typeof raw.state !== "string" ||
    typeof raw.request_sha256 !== "string" ||
    !/^[0-9a-f]{64}$/.test(raw.request_sha256)
  ) {
    throw new OperatorListeningContractError(
      502,
      "upstream_poll_schema_invalid",
    );
  }

  if (raw.state === "accepted" || raw.state === "running") {
    if (
      !hasExactKeys(raw, [
        "schema",
        "operation_id",
        "request_sha256",
        "state",
      ])
    ) {
      throw new OperatorListeningContractError(
        502,
        "upstream_poll_schema_invalid",
      );
    }
    return {
      schema: BFF_POLL_RESPONSE_SCHEMA,
      task_id: parsedTaskId,
      status: raw.state === "running" ? "processing" : "accepted",
      poll_after_ms: 500,
    };
  }

  if (raw.state === "completed") {
    if (
      !hasExactKeys(raw, [
        "schema",
        "operation_id",
        "request_sha256",
        "state",
        "result",
      ])
    ) {
      throw new OperatorListeningContractError(
        502,
        "upstream_poll_schema_invalid",
      );
    }
    validateBoundedJson(raw.result, { nodes: 0 }, 0);
    return {
      schema: BFF_POLL_RESPONSE_SCHEMA,
      task_id: parsedTaskId,
      status: "complete",
      observation: raw.result,
    };
  }

  if (raw.state === "failed") {
    if (
      !hasExactKeys(raw, [
        "schema",
        "operation_id",
        "request_sha256",
        "state",
        "failure_code",
      ]) ||
      typeof raw.failure_code !== "string" ||
      !/^[a-z0-9_]{1,64}$/.test(raw.failure_code)
    ) {
      throw new OperatorListeningContractError(
        502,
        "upstream_poll_schema_invalid",
      );
    }
    return {
      schema: BFF_POLL_RESPONSE_SCHEMA,
      task_id: parsedTaskId,
      status: "failed",
      failure_code: raw.failure_code,
    };
  }

  throw new OperatorListeningContractError(
    502,
    "upstream_poll_status_invalid",
  );
}

export function operatorErrorResponse(error: unknown): {
  status: number;
  body: { schema: typeof BFF_ERROR_SCHEMA; error: string };
} {
  if (error instanceof OperatorListeningContractError) {
    return {
      status: error.httpStatus,
      body: { schema: BFF_ERROR_SCHEMA, error: error.code },
    };
  }
  return {
    status: 500,
    body: { schema: BFF_ERROR_SCHEMA, error: "operator_listening_failed" },
  };
}
