/**
 * Generates per-scene voiceover lines via edge-tts into public/vo/.
 * One mp3 per line so each can be scheduled at its Sequence's frame.
 *
 *   node scripts/gen-vo.mjs            # all lines
 *   node scripts/gen-vo.mjs s1_pain    # specific lines only
 */
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { LINES } from "./vo-lines.mjs";

const VOICE = "en-US-AndrewMultilingualNeural";
const RATE = "+8%";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "../public/vo");

const wanted = process.argv.slice(2);
const entries = Object.entries(LINES).filter(
  ([name]) => wanted.length === 0 || wanted.includes(name),
);

mkdirSync(OUT, { recursive: true });
for (const [name, line] of entries) {
  const file = join(OUT, `${name}.mp3`);
  const text = typeof line === "string" ? line : line.text;
  const rate = typeof line === "string" ? RATE : (line.rate ?? RATE);
  const voice = typeof line === "string" ? VOICE : (line.voice ?? VOICE);
  execFileSync(
    "python",
    ["-m", "edge_tts", "--voice", voice, `--rate=${rate}`, "--text", text, "--write-media", file],
    { stdio: "inherit" },
  );
  console.log(`wrote vo/${name}.mp3`);
}
