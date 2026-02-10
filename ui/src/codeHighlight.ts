/**
 * Rich-like terminal syntax highlighting using cli-highlight (highlight.js).
 * Use for code blocks in assistant messages and tool results.
 */
import chalk from "chalk";
import { highlight as cliHighlight } from "cli-highlight";
import { colors } from "./colors.js";

/**
 * Night Owl-inspired theme for terminal code blocks.
 * Colors pulled from sdras/night-owl-vscode-theme.
 */
const richLikeTheme = {
  // structure / control flow
  keyword: chalk.hex("#c792ea"),
  "meta-keyword": chalk.hex("#c792ea"),

  // language + stdlib surface
  built_in: chalk.hex("#82AAFF"),
  type: chalk.hex("#c5e478"),
  class: chalk.hex("#ffcb8b"),
  function: chalk.hex("#82AAFF"),
  title: chalk.hex("#82AAFF"),

  // values
  literal: chalk.hex("#F78C6C"),
  number: chalk.hex("#F78C6C"),
  string: chalk.hex("#ecc48d"),
  regexp: chalk.hex("#5ca7e4"),
  symbol: chalk.hex("#F78C6C"),
  subst: chalk.hex("#d6deeb"),

  // commentary & metadata
  comment: chalk.hex("#637777"),
  doctag: chalk.hex("#637777"),
  meta: chalk.hex("#7fdbca"),
  "meta-string": chalk.hex("#ecc48d"),

  // identifiers & everything else
  params: chalk.hex("#d6deeb"),
  default: chalk.hex("#d6deeb"),
} as const;

/**
 * Highlight code for terminal output (Rich-like syntax highlighting).
 * Returns a string with ANSI escape codes; render with Ink <Text>{result}</Text>.
 */
export function highlightCode(code: string, language?: string): string {
  try {
    const options: Parameters<typeof cliHighlight>[1] = {
      theme: richLikeTheme,
      ignoreIllegals: true,
    };
    if (language && language.trim()) {
      options.language = language.toLowerCase();
    }
    // When no language is set, cli-highlight will auto-detect.
    return cliHighlight(code, options);
  } catch {
    return code;
  }
}

/** Match ```lang?\n...\n``` and return { language?, code } or null */
export function parseFencedCodeBlock(
  text: string
): { language?: string; code: string } | null {
  const match = text.match(/^```(\w*)\n?([\s\S]*?)```$/);
  if (!match) return null;
  const [, lang, raw] = match;

  // Strip blank lines at top/bottom and common leading indentation so
  // code visually starts at the left "edge" while preserving relative indents.
  const lines = raw.replace(/\t/g, "  ").split("\n");

  // Trim leading/trailing empty lines
  while (lines.length && !lines[0].trim()) lines.shift();
  while (lines.length && !lines[lines.length - 1].trim()) lines.pop();

  if (!lines.length) {
    return { language: lang || undefined, code: "" };
  }

  // Compute minimal indentation across non-empty lines
  let minIndent = Infinity;
  for (const line of lines) {
    if (!line.trim()) continue;
    const m = line.match(/^(\s*)/);
    const indent = m ? m[1].length : 0;
    if (indent < minIndent) minIndent = indent;
  }

  if (!Number.isFinite(minIndent) || minIndent <= 0) {
    return { language: lang || undefined, code: lines.join("\n") };
  }

  const dedented = lines
    .map((line) => (line.length >= minIndent ? line.slice(minIndent) : line))
    .join("\n")
    .trimEnd();

  return { language: lang || undefined, code: dedented };
}
