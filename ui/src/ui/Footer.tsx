import React from "react";
import { Box, Text } from "ink";
import Spinner from "ink-spinner";
import { colors } from "../colors.js";

export function Footer({
  thinking,
  compaction,
  onExitStats,
}: {
  thinking: boolean;
  compaction: boolean;
  onExitStats?: boolean;
}) {
  const left = "Press / for commands • ctrl+o (expand tools) • ctrl+c (quit)";
  const right = thinking
    ? "Thinking on (tab to toggle)"
    : "Thinking off (tab to toggle)";

  return (
    <Box paddingX={1} paddingY={0}>
      <Box flexGrow={1}>
        <Text dimColor>{left}</Text>
      </Box>
      {compaction ? (
        <Box>
          <Text color={colors.lightPurple}>
            <Spinner type="dots3" /> compacting context
          </Text>
        </Box>
      ) : (
        <Box>
          <Text color={thinking ? colors.lightPurple : undefined} dimColor={!thinking}>
            {right}
          </Text>
        </Box>
      )}
    </Box>
  );
}
