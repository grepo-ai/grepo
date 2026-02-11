import React, { useCallback, useEffect, useRef, useState } from "react";
import { Box, Text, useApp, useInput } from "ink";
import TextInput from "ink-text-input";
import Markdown from "@inkkit/ink-markdown";
import chalk from "chalk";
import type { StdoutMessage } from "./protocol.js";
import { useBackend } from "./useBackend.js";
import { Intro } from "./ui/Intro.jsx";
import { SpinnerPanel } from "./ui/SpinnerPanel.jsx";
import { Footer } from "./ui/Footer.jsx";
import { ToolTree, type ToolNode } from "./ui/ToolTree.jsx";
import { CommandPalette } from "./ui/CommandPalette.jsx";
import { colors } from "./colors.js";
import { highlightCode, parseFencedCodeBlock } from "./codeHighlight.js";

type TurnEventKind =
  | "user"
  | "thinking"
  | "assistant_delta"
  | "tool_start"
  | "tool_result"
  | "error"
  | "cost";

interface TurnEvent {
  kind: TurnEventKind;
  /**
   * Payload varies by kind:
   * - user: string (user text)
   * - thinking: string (one thinking chunk)
   * - assistant_delta: string (one streamed answer chunk)
   * - tool_start / tool_result: { toolId: string }
   * - error: string
   * - cost: Record<string, unknown>
   */
  payload: unknown;
}

interface Turn {
  id: number;
  userText: string;
  events: TurnEvent[];
  toolNodes: Record<string, ToolNode>;
}

function mergeUniqueChildren(
  existing: ToolNode["children"] | undefined,
  incoming: ToolNode["children"] | undefined
): ToolNode["children"] {
  const result: ToolNode["children"] = [];
  const seen = new Set<string>();

  const add = (child: ToolNode["children"][number]) => {
    const key =
      typeof child === "string"
        ? `s:${child}`
        : `o:${child.label}:${child.path ?? ""}:${child.link ?? ""}:${
            child.isCode ? "1" : "0"
          }`;
    if (seen.has(key)) return;
    seen.add(key);
    result.push(child);
  };

  for (const c of existing ?? []) add(c);
  for (const c of incoming ?? []) add(c);

  return result;
}

function getVersion(): string {
  return "0.1.0";
}

export default function App() {
  const { exit } = useApp();
  const backend = useBackend();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [activeTurnId, setActiveTurnId] = useState<number | null>(null);
  const [streamBuf, setStreamBuf] = useState(""); // active turn only
  const [thinkingBuf, setThinkingBuf] = useState(""); // active turn only
  const [draft, setDraft] = useState("");
  const [cost, setCost] = useState<Record<string, unknown> | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteIndex, setPaletteIndex] = useState(0);
  const streamBufRef = useRef("");
  const thinkingBufRef = useRef("");
  const nextTurnIdRef = useRef(1);

  const appendEventToActiveTurn = useCallback(
    (event: TurnEvent) => {
      setTurns((prev) => {
        if (activeTurnId === null) return prev;
        return prev.map((t) =>
          t.id === activeTurnId ? { ...t, events: [...t.events, event] } : t
        );
      });
    },
    [activeTurnId]
  );

  const updateTurnByToolId = useCallback((toolId: string, updater: (turn: Turn) => Turn) => {
    setTurns((prev) => {
      let found = false;
      const next = prev.map((t) => {
        if (t.toolNodes[toolId]) {
          found = true;
          return updater(t);
        }
        return t;
      });
      return next;
    });
  }, []);

  const appendEventForToolId = useCallback(
    (toolId: string, event: TurnEvent) => {
      setTurns((prev) => {
        let found = false;
        let next = prev.map((t) => {
          if (!found && t.toolNodes[toolId]) {
            found = true;
            return { ...t, events: [...t.events, event] };
          }
          return t;
        });
        if (found) return next;
        if (activeTurnId === null) return next;
        next = next.map((t) =>
          t.id === activeTurnId ? { ...t, events: [...t.events, event] } : t
        );
        return next;
      });
    },
    [activeTurnId]
  );

  const updateActiveTurn = useCallback(
    (updater: (turn: Turn) => Turn) => {
      setTurns((prev) => {
        if (activeTurnId === null) return prev;
        return prev.map((t) => (t.id === activeTurnId ? updater(t) : t));
      });
    },
    [activeTurnId]
  );

  const handleMessage = useCallback(
    (m: StdoutMessage) => {
      if (m.type === "delta") {
        streamBufRef.current += m.value;
        setStreamBuf(streamBufRef.current);
        appendEventToActiveTurn({
          kind: "assistant_delta",
          // Store only the new chunk so each delta
          // is rendered as its own event in order.
          payload: m.value,
        });
        return;
      }
      if (m.type === "thinking") {
        thinkingBufRef.current += m.value;
        setThinkingBuf(thinkingBufRef.current);
        appendEventToActiveTurn({
          kind: "thinking",
          // Store only the new chunk so each thinking
          // update is rendered as its own event in order.
          payload: m.value,
        });
        return;
      }
      if (m.type === "done") {
        // End of streaming for this turn: just clear the buffers.
        // We intentionally do NOT accumulate or render a final combined message.
        streamBufRef.current = "";
        setStreamBuf("");
        thinkingBufRef.current = "";
        setThinkingBuf("");
        return;
      }
      if (m.type === "tool_start") {
        const v = m.value;
        updateActiveTurn((turn) => ({
          ...turn,
          toolNodes: {
            ...turn.toolNodes,
            [v.id]: {
              id: v.id,
              name: v.name,
              data: v.data ?? undefined,
              children: [],
            },
          },
        }));
        appendEventToActiveTurn({
          kind: "tool_start",
          payload: { toolId: v.id },
        });
        return;
      }
      if (m.type === "tool_result") {
        const v = m.value;
        updateTurnByToolId(v.id, (turn) => {
          const node = turn.toolNodes[v.id];
          if (!node) return turn;
          const children: ToolNode["children"] = [];
          if (v.format === "error" && typeof v.content === "string") {
            children.push(v.content);
          } else if (v.format === "code" && typeof v.content === "string") {
            const code = v.content.trimEnd();
            const fenced =
              code.startsWith("```") && code.includes("\n")
                ? code
                : `\`\`\`python\n${code}\n\`\`\``;
            children.push({ label: fenced, isCode: true });
          } else if (Array.isArray(v.content)) {
            for (const c of v.content) {
              if (typeof c === "string") children.push(c);
              else if (c && typeof c === "object" && "path" in c) {
                const p = c as { path: string; line?: number; root?: string };
                const label =
                  p.line != null ? `${p.path}:${p.line}` : p.path;
                children.push({
                  label,
                  path: p.path,
                  line: p.line,
                  root: p.root,
                });
              } else if (c && typeof c === "object" && "file" in c)
                children.push({
                  label: `${(c as { file: string }).file}:${(c as { line?: string }).line ?? ""}`,
                });
            }
          } else if (typeof v.content === "string") {
            children.push(v.content);
          }
          return {
            ...turn,
            toolNodes: {
              ...turn.toolNodes,
              [v.id]: {
                ...node,
                children: mergeUniqueChildren(node.children, children),
              },
            },
          };
        });
        appendEventForToolId(v.id, {
          kind: "tool_result",
          payload: { toolId: v.id },
        });
        return;
      }
      if (m.type === "cost") {
        setCost(m.value as Record<string, unknown>);
        appendEventToActiveTurn({
          kind: "cost",
          payload: m.value as Record<string, unknown>,
        });
        return;
      }
      if (m.type === "error") {
        appendEventToActiveTurn({
          kind: "error",
          payload: `Error: ${m.value}`,
        });
      }
    },
    [appendEventToActiveTurn, updateActiveTurn, updateTurnByToolId, appendEventForToolId]
  );

  useEffect(() => {
    backend.setOnMessage(handleMessage);
  }, [backend, handleMessage]);

  const submit = useCallback(() => {
    // Don't submit if the command palette was just used;
    // first Enter only fills the input bar.
    if (paletteOpen) return;
    const text = draft.trim();
    if (!text || backend.busy) return;
    backend.setError(null);
    setCost(null);
    const id = nextTurnIdRef.current++;
    setTurns((prev) => [
      ...prev,
      {
        id,
        userText: text,
        events: [{ kind: "user", payload: text }],
        toolNodes: {},
      },
    ]);
    setActiveTurnId(id);
    setDraft("");
    // Reset streaming buffers for the new query so all backend messages
    // (delta, thinking, tools, etc.) start fresh for this turn.
    streamBufRef.current = "";
    setStreamBuf("");
    thinkingBufRef.current = "";
    setThinkingBuf("");
    backend.send("query", text);
  }, [draft, backend]);

  const isTty = Boolean(process.stdin.isTTY && process.stdout.isTTY);
  useInput(
    (input, key) => {
    if (key.ctrl && key.c) {
      if (backend.busy) {
        backend.send("cancel", true);
      } else {
        exit();
      }
      return;
    }
    if (key.tab) {
      const next = !backend.thinking;
      backend.setThinking(next);
      backend.send("set_thinking", next);
      return;
    }
    if (input === "/" && !draft) {
      setPaletteOpen(true);
      setPaletteIndex(0);
    }
    if (paletteOpen) {
      if (key.upArrow) setPaletteIndex((i) => (i - 1 + 4) % 4);
      if (key.downArrow) setPaletteIndex((i) => (i + 1) % 4);
      if (key.escape) setPaletteOpen(false);
      if (key.return) {
        const cmds = ["plan", "ask", "help", "settings"];
        setDraft(`/${cmds[paletteIndex]}`);
        setPaletteOpen(false);
      }
    }
  },
    // Keep input handling active even while a turn is in progress.
    // Submission is still guarded in `submit` via `backend.busy`.
    { isActive: isTty }
  );

  if (backend.error) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text color={colors.red}>{backend.error}</Text>
      </Box>
    );
  }

  if (!backend.ready) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text dimColor>starting grepo...</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column">
      <Intro version={getVersion()} />
      <Box flexDirection="column" marginTop={0} minHeight={0}>
        {(() => {
          const recentTurns = turns.slice(-10);
          const lastTurnId = recentTurns[recentTurns.length - 1]?.id ?? null;
          return (
            <>
              {recentTurns.map((turn) => {
                const events = turn.events;
                const renderedToolIds = new Set<string>();

                return (
                  <Box key={turn.id} flexDirection="column" marginBottom={1}>
                    <Box marginBottom={1}>
                      <Text
                        color="#F982FF"
                        backgroundColor="#292929"
                        wrap="wrap"
                      >
                        {"> "}
                        {turn.userText}
                      </Text>
                    </Box>
                    {events.map((event, idx) => {
                      const key = `turn-${turn.id}-event-${idx}-${event.kind}`;
                      if (event.kind === "thinking") {
                        const text = String(event.payload ?? "");
                        if (!text) return null;
                        return (
                          <Box key={key} flexDirection="column" marginBottom={1}>
                            <Text wrap="wrap" color={colors.thinkingText}>
                              {text}
                            </Text>
                          </Box>
                        );
                      }
                      if (event.kind === "assistant_delta") {
                        const text = String(event.payload ?? "");
                        if (!text) return null;
                        const fenced = parseFencedCodeBlock(text);
                        return (
                          <Box key={key} flexDirection="row" marginBottom={1}>
                            <Text color={colors.inputBarBg}>● </Text>
                            <Box marginLeft={1}>
                              {fenced ? (
                                <Text>{highlightCode(fenced.code, fenced.language)}</Text>
                              ) : (
                                <Markdown
                                  heading={chalk.hex(colors.paletteHighlight).bold}
                                  firstHeading={chalk.hex(colors.introTextPink).bold}
                                  code={chalk.hex(colors.green)}
                                  codespan={chalk.hex(colors.orange)}
                                >
                                  {text}
                                </Markdown>
                              )}
                            </Box>
                          </Box>
                        );
                      }
                      if (event.kind === "tool_start" || event.kind === "tool_result") {
                        const toolId = (event.payload as { toolId: string }).toolId;
                        if (renderedToolIds.has(toolId)) return null;
                        renderedToolIds.add(toolId);
                        const node = turn.toolNodes[toolId];
                        if (!node) return null;
                        return (
                          <Box key={key} marginBottom={1}>
                            <ToolTree nodes={[node]} />
                          </Box>
                        );
                      }
                      if (event.kind === "error") {
                        const text = String(event.payload ?? "");
                        return (
                          <Box key={key} marginBottom={1}>
                            <Text color={colors.red}>{text}</Text>
                          </Box>
                        );
                      }
                      // cost events are tracked but rendered only once globally
                      // using the latest `cost` state below the spinner.
                      if (event.kind === "user") {
                        // Already rendered as turn.userText above.
                        return null;
                      }
                      return null;
                    })}
                  </Box>
                );
              })}
            </>
          );
        })()}
      </Box>
      <SpinnerPanel busy={backend.busy} />
      {cost ? (
        <Box marginTop={1} marginLeft={1}>
          <Text dimColor>
            ↑ {String(cost.total_input_tokens)} ↓ {String(cost.total_output_tokens)}
            {(cost as Record<string, unknown>).context_window_used != null
              ? ` • ${String((cost as Record<string, unknown>).context_window_used)}`
              : ""}{" "}
            • {String(cost.cost)}
          </Text>
        </Box>
      ) : null}
      <Box marginTop={1} minHeight={2} flexDirection="column" justifyContent="flex-end">
        <Box paddingX={1} paddingY={0} borderStyle="single" borderColor={colors.inputBarBg}>
          <Text color={colors.accent}>
            <TextInput
              value={draft}
              onChange={setDraft}
              onSubmit={submit}
              showCursor
            />
          </Text>
        </Box>
      </Box>
      <Footer
        thinking={backend.thinking}
        compaction={backend.compaction}
        onExitStats={!!cost}
      />
      {paletteOpen ? (
        <CommandPalette
          visible
          selection={paletteIndex}
          onSelect={(cmd) => {
            setDraft(`/${cmd}`);
            setPaletteOpen(false);
          }}
        />
      ) : null}
    </Box>
  );
}
