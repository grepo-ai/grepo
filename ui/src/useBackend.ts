import { spawn, type ChildProcess } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { useEffect, useRef, useState } from "react";
import {
  decode,
  encode,
  type StdoutMessage,
  type StdinMessage,
  type InitValue,
} from "./protocol.js";

const COALESCE_MS = 80;
const DEBUG = process.env.GREPO_DEBUG === "1";

/** Package root of the grepo UI (e.g. .../grepo-ui or .../grepo when bundled). */
function getPackageRoot(): string {
  const url = import.meta.url;
  const dir = path.dirname(url.startsWith("file:") ? fileURLToPath(url) : url);
  return path.resolve(dir, "..");
}

/**
 * Resolve the backend "src" directory for PYTHONPATH so that
 * "python3 -m cli.backend_stdio" works. Used when grepo-stdio is not on PATH.
 * Checks: package_root/python/src (bundled), package_root/../src (dev), then cwd-relative.
 */
function getBackendSrcPath(): string | null {
  const pkgRoot = getPackageRoot();
  const cwd = process.cwd();
  const candidates = [
    path.join(pkgRoot, "python", "src"), // distributed: backend bundled in package
    path.join(pkgRoot, "..", "src"), // development: grepo/ui and grepo/src
    path.join(cwd, "..", "src"), // grepo/ui -> grepo/src
    path.join(cwd, "..", "..", "grepo", "src"),
    path.join(cwd, "grepo", "src"),
    path.join(cwd, "src"),
  ];
  for (const srcPath of candidates) {
    if (fs.existsSync(path.join(srcPath, "cli", "backend_stdio.py"))) {
      return srcPath;
    }
  }
  return null;
}

export function useBackend() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [compaction, setCompaction] = useState(false);
  const procRef = useRef<ChildProcess | null>(null);
  const queueRef = useRef<StdoutMessage[]>([]);
  const drainTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef<((m: StdoutMessage) => void) | null>(null);

  const flushQueue = () => {
    if (queueRef.current.length === 0) return;
    const batch = queueRef.current;
    queueRef.current = [];
    for (const m of batch) {
      if (m.type === "ready") {
        setReady(true);
        setError(null);
      } else if (m.type === "error") {
        setError(m.value);
      } else if (m.type === "status") {
        const v = m.value;
        if (v.busy !== undefined) setBusy(v.busy);
        if (v.thinking !== undefined) setThinking(v.thinking);
        if (v.compaction !== undefined) setCompaction(v.compaction);
      }
      onMessageRef.current?.(m);
    }
  };

  useEffect(() => {
    const rootDir = process.cwd();
    const env = { ...process.env };

    // Use bundled/dev backend when found; otherwise grepo-stdio from PATH (pip install grepo)
    const useGrepoStdio = process.platform === "win32" ? "grepo-stdio.cmd" : "grepo-stdio";
    const backendSrc = getBackendSrcPath();
    if (backendSrc) env.PYTHONPATH = backendSrc;

    const spawnBackend = (): ChildProcess => {
      if (backendSrc) {
        return spawn("python3", ["-m", "cli.backend_stdio"], {
          cwd: rootDir,
          env,
          stdio: ["pipe", "pipe", "pipe"],
        });
      }
      return spawn(useGrepoStdio, [], {
        cwd: rootDir,
        env,
        stdio: ["pipe", "pipe", "pipe"],
        shell: process.platform === "win32",
      });
    };

    const child = spawnBackend();
    procRef.current = child;

    let stderrBuffer = "";
    child.stderr?.on("data", (chunk: Buffer) => {
      // Buffer stderr so we can show a helpful message if the backend exits
      // with a non-zero code, but do not echo it directly into the Ink UI.
      stderrBuffer += chunk.toString();
    });

    child.on("error", (err: NodeJS.ErrnoException) => {
      if (err.code === "ENOENT") {
        setError(
          "Backend not found. Install the Python backend: pip install grepo (or run from repo with backend in python/ or ../src)."
        );
      } else {
        setError(err.message);
      }
    });

    let buffer = "";
    child.stdout?.on("data", (chunk: Buffer) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const m = decode(line);
        if (!m) {
          if (DEBUG && line.trim().length > 0) {
            console.error("[grepo] invalid message dropped");
          }
          continue;
        }
        if (DEBUG) {
          if (m.type === "delta" || m.type === "thinking") {
            const raw = typeof m.value === "string" ? m.value : JSON.stringify(m.value);
            const preview =
              raw.length > 80
                ? `${raw.slice(0, 80).replace(/\n/g, "\\n")}…`
                : raw.replace(/\n/g, "\\n");
            console.error(`[grepo] ← ${m.type} ${JSON.stringify(preview)}`);
          } else {
            console.error(`[grepo] ← ${m.type}`);
          }
        }
        queueRef.current.push(m);
        if (drainTimerRef.current) clearTimeout(drainTimerRef.current);
        drainTimerRef.current = setTimeout(() => {
          drainTimerRef.current = null;
          flushQueue();
        }, COALESCE_MS);
      }
    });
    child.on("exit", (code) => {
      procRef.current = null;
      setReady(false);
      if (code !== 0 && code !== null) {
        const trace = stderrBuffer.trim();
        const msg = trace
          ? `Backend exited with code ${code}. Stderr:\n${trace.slice(-4000)}`
          : `Backend exited with code ${code}`;
        setError((prev) => prev || msg);
      }
    });

    const init: StdinMessage = {
      type: "init",
      value: { status: true, rootDir } satisfies InitValue,
    };
    if (child.stdin?.writable) {
      child.stdin.write(encode(init) + "\n");
      if (DEBUG) console.error("[grepo] → init");
    }

    return () => {
      if (drainTimerRef.current) clearTimeout(drainTimerRef.current);
      flushQueue();
      try {
        child.kill();
      } catch {
        // ignore
      }
    };
  }, []);

  /** Send a typed stdin message to the backend. */
  function send<K extends StdinMessage["type"]>(
    type: K,
    value: Extract<StdinMessage, { type: K }>["value"]
  ): void {
    const p = procRef.current;
    if (!p?.stdin?.writable) return;
    p.stdin.write(encode({ type, value } as StdinMessage) + "\n");
    if (DEBUG) console.error(`[grepo] → ${type}`);
  }

  return {
    ready,
    error,
    busy,
    thinking,
    compaction,
    setReady,
    setError,
    setBusy,
    setThinking,
    setCompaction,
    setOnMessage: (fn: (m: StdoutMessage) => void) => {
      onMessageRef.current = fn;
    },
    flushQueue,
    send,
  };
}
