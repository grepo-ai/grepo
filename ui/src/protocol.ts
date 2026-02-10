/**
 * NDJSON stdio protocol. No WebSocket.
 * Single structured message schema: discriminated union with strict runtime validation.
 */

// ---------------------------------------------------------------------------
// Value types (explicit shapes per message type)
// ---------------------------------------------------------------------------

/** UI -> backend: first message; status flag and project root */
export interface InitValue {
  status: boolean;
  rootDir: string;
}

/** Backend -> UI: init accepted */
export interface ReadyValue {
  status: boolean;
}

/** Backend -> UI: backend/agent state */
export interface StatusValue {
  busy?: boolean;
  thinking?: boolean;
  compaction?: boolean;
}

/** Backend -> UI: tool call started; name is short (list, read, grep, glob, code_search, write) */
export interface ToolStartValue {
  id: string;
  name: string;
  args: Record<string, unknown>;
  data?: string | null;
}

/** Backend -> UI: tool result content item (path snippet or file:line) */
export type ToolResultContentItem =
  | string
  | { path: string; snippet?: string; root?: string; line?: number | string | null }
  | { file: string; line?: number | string };

/** Backend -> UI: tool result format */
export type ToolResultFormat =
  | "list_files"
  | "read_file"
  | "grep"
  | "glob"
  | "code"
  | "raw"
  | "error";

export interface ToolResultValue {
  id: string;
  name: string;
  content: string | ToolResultContentItem[];
  format?: ToolResultFormat;
}

/** Backend -> UI: per-cycle cost stats */
export interface CostValue {
  total_input_tokens: number;
  total_output_tokens: number;
  cache_creation_input_tokens?: number;
  cache_read_input_tokens?: number;
  cost: string;
  context_window_used: string;
}

/** Reserved for human-in-the-loop (e.g. edit approval); not yet sent over stdio */
export interface InterruptValue {
  old_code?: string;
  new_code?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Discriminated unions: UI -> backend (stdin) and backend -> UI (stdout)
// ---------------------------------------------------------------------------

export type StdinMessage =
  | { type: "init"; value: InitValue }
  | { type: "query"; value: string }
  | { type: "set_thinking"; value: boolean }
  | { type: "cancel"; value: unknown };

export type StdoutMessage =
  | { type: "ready"; value: ReadyValue }
  | { type: "status"; value: StatusValue }
  | { type: "delta"; value: string }
  | { type: "done"; value: null }
  | { type: "error"; value: string }
  | { type: "tool_start"; value: ToolStartValue }
  | { type: "tool_result"; value: ToolResultValue }
  | { type: "thinking"; value: string }
  | { type: "cost"; value: CostValue }
  | { type: "interrupt"; value: InterruptValue };

/** All message types: stdin (UI->backend) or stdout (backend->UI) */
export type StdioMessage = StdinMessage | StdoutMessage;

/** Type guard: is this a valid StdinMessage (for encoding/sending from UI)? */
export function isStdinMessage(m: unknown): m is StdinMessage {
  if (!m || typeof m !== "object" || !("type" in m) || !("value" in m)) return false;
  const t = (m as { type: string }).type;
  const v = (m as { value: unknown }).value;
  switch (t) {
    case "init":
      return (
        typeof v === "object" &&
        v !== null &&
        "status" in v &&
        typeof (v as InitValue).status === "boolean" &&
        "rootDir" in v &&
        typeof (v as InitValue).rootDir === "string"
      );
    case "query":
      return typeof v === "string";
    case "set_thinking":
      return typeof v === "boolean";
    case "cancel":
      return true;
    default:
      return false;
  }
}

/** Type guard: is this a valid StdoutMessage (for decoding/receiving in UI)? */
export function isStdoutMessage(m: unknown): m is StdoutMessage {
  if (!m || typeof m !== "object" || !("type" in m) || !("value" in m)) return false;
  const t = (m as { type: string }).type;
  const v = (m as { value: unknown }).value;
  switch (t) {
    case "ready":
      return (
        typeof v === "object" &&
        v !== null &&
        "status" in v &&
        typeof (v as ReadyValue).status === "boolean"
      );
    case "status":
      if (typeof v !== "object" || v === null) return false;
      const s = v as Record<string, unknown>;
      return (
        (s.busy === undefined || typeof s.busy === "boolean") &&
        (s.thinking === undefined || typeof s.thinking === "boolean") &&
        (s.compaction === undefined || typeof s.compaction === "boolean")
      );
    case "delta":
    case "thinking":
    case "error":
      return typeof v === "string";
    case "done":
      return v === null;
    case "tool_start":
      if (typeof v !== "object" || v === null) return false;
      const ts = v as Record<string, unknown>;
      return (
        typeof ts.id === "string" &&
        typeof ts.name === "string" &&
        typeof ts.args === "object" &&
        ts.args !== null
      );
    case "tool_result":
      if (typeof v !== "object" || v === null) return false;
      const tr = v as Record<string, unknown>;
      return (
        typeof tr.id === "string" &&
        typeof tr.name === "string" &&
        (typeof tr.content === "string" || Array.isArray(tr.content))
      );
    case "cost":
      if (typeof v !== "object" || v === null) return false;
      const c = v as Record<string, unknown>;
      return (
        typeof c.total_input_tokens === "number" &&
        typeof c.total_output_tokens === "number" &&
        typeof c.cost === "string" &&
        typeof c.context_window_used === "string"
      );
    case "interrupt":
      return typeof v === "object" && v !== null;
    default:
      return false;
  }
}

// ---------------------------------------------------------------------------
// Encode (UI sends StdinMessage) / Decode (UI receives StdoutMessage)
// ---------------------------------------------------------------------------

export function encode(msg: StdinMessage): string {
  if (!isStdinMessage(msg)) {
    throw new Error(`Protocol encode: invalid stdin message type=${(msg as { type?: string }).type}`);
  }
  return JSON.stringify(msg);
}

/**
 * Decode one NDJSON line from backend. Returns null for empty/invalid JSON.
 * Strict: returns StdoutMessage only if shape is valid; otherwise null.
 */
export function decode(line: string): StdoutMessage | null {
  const t = line.trim();
  if (!t) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(t);
  } catch {
    return null;
  }
  if (!isStdoutMessage(parsed)) return null;
  return parsed;
}
