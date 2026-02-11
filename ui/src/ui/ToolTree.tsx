import React from "react";
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

export function ToolTree({ nodes }: { nodes: ToolNode[] }) {
  return (
    <Box flexDirection="column">
      {nodes.map((node) => (
        <Box key={node.id} flexDirection="column" marginLeft={0}>
          <Box flexDirection="row">
            <Text color={colors.lightPink}>● </Text>
            <Text color={colors.green} bold>
              {NODE_LABELS[node.name] ?? node.name}
            </Text>
            {node.data ? (
              <Text color={colors.green}> ({node.data})</Text>
            ) : null}
          </Box>
          {(() => {
            const children = node.children ?? [];
            if (!children.length) return null;
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
                    // Render branch and code on the same line so the block
                    // starts at the tree edge instead of on the next line.
                    // We also avoid forcing a branch color here so it doesn't
                    // stand out as orange vs. the code itself.
                    return (
                      <Box key={i}>
                        <Text>
                          {branch}
                          {highlighted}
                        </Text>
                      </Box>
                    );
                  }

                // For non-code children that carry file locations, render them
                // as clickable links using a file:// URI so the OS opens the
                // file in the user's default application (e.g. their editor).
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

                  // Prefer full absolute path when we have a root + relative path.
                  let fullPath = filePath;
                  if (rootPath && filePath && !filePath.startsWith("/")) {
                    const root = rootPath.endsWith("/") ? rootPath.slice(0, -1) : rootPath;
                    fullPath = `${root}/${filePath}`;
                  }

                  const displayLabel = c.label;
                  if (fullPath) {
                    const locationText = line ? `${fullPath}:${line}` : fullPath;
                    // file:// so the OS opens in default app (editor); line is shown in locationText.
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

                  // Fallback: just render the label normally.
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
          })()}
        </Box>
      ))}
    </Box>
  );
}
