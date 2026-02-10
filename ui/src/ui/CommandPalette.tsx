import React from "react";
import { Box, Text } from "ink";
import { colors } from "../colors.js";

const MAIN_COMMANDS = ["Plan", "Ask", "Help", "Settings"];

export function CommandPalette({
  visible,
  selection,
  onSelect,
}: {
  visible: boolean;
  selection: number;
  onSelect: (cmd: string) => void;
}) {
  if (!visible) return null;

  return (
    <Box flexDirection="column" marginTop={1} marginLeft={1}>
      <Text dimColor>Commands (↑/↓ + Enter, Esc to close)</Text>
      {MAIN_COMMANDS.map((cmd, i) => (
        <Box key={cmd}>
          <Text
            color={i === selection ? "#FFBA61" : "#A6B5DE"}
          >
            {i === selection ? "> " : "  "}
            {cmd}
          </Text>
        </Box>
      ))}
    </Box>
  );
}
