import React, { useMemo } from "react";
import { Box, Text } from "ink";
import figlet from "figlet";
import { colors } from "../colors.js";

function getBanner(): string {
  try {
    return figlet.textSync("grepo", { font: "Stop" });
  } catch {
    try {
      return figlet.textSync("grepo", { font: "Standard" });
    } catch {
      return "grepo";
    }
  }
}

export function Intro({ version = "0.1.0" }: { version?: string }) {
  const banner = useMemo(getBanner, []);
  const cwd = process.cwd();
  return (
    <Box flexDirection="column" paddingX={1} paddingY={0}>
      <Text color={colors.accent}>{banner}</Text>
      <Box marginTop={1} flexDirection="column" marginBottom={1}>
        <Text color={colors.grey}>dir: {cwd}</Text>
        <Text color={colors.grey} italic>version: {version}</Text>
      </Box>
    </Box>
  );
}
