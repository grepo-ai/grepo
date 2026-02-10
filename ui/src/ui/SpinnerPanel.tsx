import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";
import cliSpinners, { type SpinnerName } from "cli-spinners";

const SPINNER_NAME: SpinnerName = "line";
const spinner = cliSpinners[SPINNER_NAME];

const PHRASES = ["Waking the gremlins", "Burning the GPUs", "Not getting bored"];
const DOTS = ["", ".", "..", "..."];
const PHRASE_INTERVAL_MS = 3000;
const DOTS_INTERVAL_MS = 400;
const SPINNER_INTERVAL_MS = Math.max(40, Math.floor(spinner.interval / 2));

function CliSpinnerChar() {
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setFrameIndex((i) => (i + 1) % spinner.frames.length);
    }, SPINNER_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return <Text color="#FFBA61">{spinner.frames[frameIndex]}</Text>;
}

function LoaderPhrase() {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [dotIndex, setDotIndex] = useState(0);

  useEffect(() => {
    const phraseId = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % PHRASES.length);
    }, PHRASE_INTERVAL_MS);
    const dotsId = setInterval(() => {
      setDotIndex((i) => (i + 1) % DOTS.length);
    }, DOTS_INTERVAL_MS);
    return () => {
      clearInterval(phraseId);
      clearInterval(dotsId);
    };
  }, []);

  return (
    <Text color="#FFBA61">
      {PHRASES[phraseIndex]}
      {DOTS[dotIndex]}
    </Text>
  );
}

export function SpinnerPanel({ busy }: { busy: boolean }) {
  return (
    <Box paddingX={1} paddingY={0}>
      {busy ? (
        <Text color="#FFBA61">
          <CliSpinnerChar /> <LoaderPhrase />
        </Text>
      ) : null}
    </Box>
  );
}

export function SpinnerPanelIdle() {
  return <Box paddingX={1} paddingY={0} />;
}
