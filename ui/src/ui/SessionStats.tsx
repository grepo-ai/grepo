import React from "react";
import { Box, Text } from "ink";
import { colors } from "../colors.js";

const LABELS: Record<string, string> = {
  total_input_tokens: "Total input tokens",
  total_output_tokens: "Total output tokens",
  cache_creation_input_tokens: "Cache write",
  cache_read_input_tokens: "Cache read",
  session_cost: "Total cost ($)",
  context_window_used: "Context window",
  model_used: "Models used",
};

function formatCostValue(key: string, value: unknown, stats: Record<string, unknown>): string {
  if (key === "context_window_used" && value != null) {
    const pct = String(value);
    const up = stats.total_input_tokens != null ? String(stats.total_input_tokens) : "";
    const down = stats.total_output_tokens != null ? String(stats.total_output_tokens) : "";
    if (up || down) return `${pct} (↑${up} ↓${down})`;
    return pct;
  }
  if (key === "session_cost" && typeof value === "string" && value.startsWith("$")) return `• ${value}`;
  if (typeof value === "string" && value.startsWith("$")) return `• ${value}`;
  return String(value);
}

export function SessionStats({ stats }: { stats: Record<string, unknown> }) {
  return (
    <Box flexDirection="column" marginTop={1}>
      {Object.entries(stats).map(([key, value]) => {
        return (
          <Box key={key}>
            <Text dimColor>{LABELS[key] ?? key}: </Text>
            <Text>{formatCostValue(key, value, stats)}</Text>
          </Box>
        );
      })}
    </Box>
  );
}
