import React, { useState, useEffect } from "react";
import { Box, Text } from "ink";
import { colors } from "../colors.js";
import { highlightCode, parseFencedCodeBlock } from "../codeHighlight.js";

export interface ToolNode {
  id: string;
  name: string;
  data?: string;
  children?: Array<
    | string
    | {
        label: string;
        /** Absolute or project-relative file path for editor integration. */
        path?: string;
        /** Optional project root for relative paths (from tools like glob/list_files). */
        root?: string;
        /** Optional 1-based line number associated with this location. */
        line?: number | string | null;
        /** Optional hyperlink; currently unused but kept for future extensibility. */
        link?: string;
        isCode?: boolean;
      }
  >;
}

const NODE_LABELS: Record<string, string> = {
  list: "List",
  read: "Read",
  write: "Write",
  grep: "Grep",
  glob: "Glob",
  code_search: "Code Search",
  edit: "Edit",
};

const CODE_SEARCH_COLLAPSED_LINES = 5;

function getCollapsedSummary(node: ToolNode): string | null {
  const n = (node.children ?? []).length;
  switch (node.name) {
    case "list":
      return `Found ${n} file${n !== 1 ? "s" : ""}`;
    case "read":
      return `Read ${n} file${n !== 1 ? "s" : ""}`;
    case "grep":
      return `Found ${n} match${n !== 1 ? "es" : ""}`;
    case "glob":
      return `Found ${n} file${n !== 1 ? "s" : ""}`;
    case "write":
      return node.data ? `Wrote ${node.data}` : "Wrote file";
    case "edit":
      return node.data ? `Edited ${node.data}` : "Edited file";
    default:
      return null;
  }
}

function formatDataLabel(name: string, data: string): string {
  if (name === "grep" || name === "glob") return `(pattern: ${data})`;
  return `(${data})`;
}

function BlinkingDot() {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const id = setInterval(() => setVisible((v) => !v), 450);
    return () => clearInterval(id);
  }, []);
  return <Text color={visible ? colors.lightPink : undefined}>{visible ? "● " : "  "}</Text>;
}

interface ToolTreeProps {
  nodes: ToolNode[];
  expanded?: boolean;
  isActive?: boolean;
}

export function ToolTree({ nodes, expanded = false, isActive = false }: ToolTreeProps) {
  return (
    <Box flexDirection="column">
      {nodes.map((node) => (
        <Box key={node.id} flexDirection="column" marginLeft={0}>
          <Box flexDirection="row">
            {isActive ? <BlinkingDot /> : <Text color={colors.lightPink}>● </Text>}
            <Text color={colors.green} bold>
              {NODE_LABELS[node.name] ?? node.name}
            </Text>
            {node.data ? (
              <Text color={colors.green}> {formatDataLabel(node.name, node.data)}</Text>
            ) : null}
          </Box>
          {(() => {
            const children = node.children ?? [];
            if (!children.length) return null;

            if (!expanded && node.name === "code_search") {
              return <CollapsedCodeSearch children={children} />;
            }
            if (!expanded && node.name !== "code_search") {
              const summary = getCollapsedSummary(node);
              if (!summary) return null;
              return (
                <Box flexDirection="column" marginLeft={2}>
                  <Box>
                    <Text>└─ {summary} </Text>
                    <Text color={colors.grey}>(ctrl+o to expand)</Text>
                  </Box>
                </Box>
              );
            }

            return <ExpandedChildren children={children} />;
          })()}
        </Box>
      ))}
    </Box>
  );
}

function CollapsedCodeSearch({
  children,
}: {
  children: NonNullable<ToolNode["children"]>;
}) {
  return (
    <Box flexDirection="column" marginLeft={2}>
      {children.map((c, i) => {
        if (typeof c === "string" || !c.isCode) {
          return (
            <Box key={i}>
              <Text color={colors.lightPurple}>└─ {typeof c === "string" ? c : c.label}</Text>
            </Box>
          );
        }
        const parsed = parseFencedCodeBlock(c.label);
        const code = parsed?.code ?? c.label;
        const lines = code.split("\n");
        const truncated = lines.length > CODE_SEARCH_COLLAPSED_LINES;
        const visibleCode = truncated
          ? lines.slice(0, CODE_SEARCH_COLLAPSED_LINES).join("\n")
          : code;
        const highlighted = highlightCode(visibleCode, parsed?.language);
        return (
          <Box key={i} flexDirection="column">
            <Box>
              <Text>
                └─ {highlighted}
              </Text>
            </Box>
            {truncated ? (
              <Box marginLeft={3}>
                <Text color={colors.grey}>… {lines.length - CODE_SEARCH_COLLAPSED_LINES} more lines (ctrl+o to expand)</Text>
              </Box>
            ) : null}
          </Box>
        );
      })}
    </Box>
  );
}

function ExpandedChildren({
  children,
}: {
  children: NonNullable<ToolNode["children"]>;
}) {
  return (
    <Box flexDirection="column" marginLeft={2}>
      {children.map((c, i) => {
        const isLast = i === children.length - 1;
        const branch = isLast ? "└─ " : "├─ ";

        if (typeof c === "string") {
          return (
            <Box key={i}>
              <Text>
                {branch}
                {c}
              </Text>
            </Box>
          );
        }

        if (c.isCode) {
          const parsed = parseFencedCodeBlock(c.label);
          const code = parsed?.code ?? c.label;
          const highlighted = highlightCode(code, parsed?.language);
          return (
            <Box key={i}>
              <Text>
                {branch}
                {highlighted}
              </Text>
            </Box>
          );
        }

        const filePath = (c as any).path as string | undefined;
        const rootPath = (c as any).root as string | undefined;
        const rawLine = (c as any).line as number | string | null | undefined;

        let line: number | undefined;
        if (typeof rawLine === "number") {
          line = rawLine > 0 ? rawLine : undefined;
        } else if (typeof rawLine === "string" && rawLine.trim()) {
          const parsed = Number(rawLine.replace(/^:/, ""));
          if (!Number.isNaN(parsed) && parsed > 0) line = parsed;
        }

        let fullPath = filePath;
        if (rootPath && filePath && !filePath.startsWith("/")) {
          const root = rootPath.endsWith("/") ? rootPath.slice(0, -1) : rootPath;
          fullPath = `${root}/${filePath}`;
        }

        const displayLabel = c.label;
        if (fullPath) {
          const locationText = line ? `${fullPath}:${line}` : fullPath;
          const encodedPath = fullPath
            .split("/")
            .map((seg) => encodeURIComponent(seg))
            .join("/");
          const target = `file:///${encodedPath}`;

          const OSC = "\u001B]";
          const BEL = "\u0007";
          const linkWrapped =
            `${OSC}8;;${target}${BEL}` +
            locationText +
            `${OSC}8;;${BEL}`;

          return (
            <Box key={i}>
              <Text color={colors.lightPurple}>
                {branch}
                {linkWrapped}
              </Text>
            </Box>
          );
        }

        return (
          <Box key={i}>
            <Text color={colors.lightPurple}>
              {branch}
              {displayLabel}
              {c.link ? ` ${c.link}` : ""}
            </Text>
          </Box>
        );
      })}
    </Box>
  );
}
