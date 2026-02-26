/**
 * Score all unscored sessions in an exported JSON file.
 * Uses the actual instrument registry + scoring functions.
 *
 * Usage: npx tsx scripts/score-export.ts <input.json> [output.json]
 */

import "../src/instruments/init";
import { getInstrument, getAllInstruments } from "../src/instruments/registry";
import { readFileSync, writeFileSync } from "fs";

const inputPath = process.argv[2];
const outputPath = process.argv[3] ?? inputPath.replace(".json", "-scored.json");

if (!inputPath) {
  console.error("Usage: npx tsx scripts/score-export.ts <input.json> [output.json]");
  process.exit(1);
}

const data = JSON.parse(readFileSync(inputPath, "utf-8"));
const sessions = data.sessions ?? {};
const results = data.results ?? {};

console.log(`Loaded ${Object.keys(sessions).length} sessions, ${Object.keys(results).length} existing results`);
console.log(`Registry has ${getAllInstruments().length} instruments`);

let scored = 0;
for (const [id, session] of Object.entries(sessions)) {
  if (results[id]) {
    console.log(`  ${id}: already scored (${results[id].scores?.length ?? 0} scales)`);
    continue;
  }

  const registered = getInstrument(id);
  if (!registered) {
    console.log(`  ${id}: not in registry (skipped)`);
    continue;
  }

  const { instrument, score } = registered;
  const sess = session as any;
  if (sess.responses.length < instrument.items.length) {
    console.log(`  ${id}: incomplete (${sess.responses.length}/${instrument.items.length})`);
    continue;
  }

  try {
    results[id] = score(instrument, sess);
    scored++;
    console.log(`  ${id}: scored -> ${results[id].scores.length} scales`);
  } catch (e: any) {
    console.error(`  ${id}: scoring failed — ${e.message}`);
  }
}

const output = { ...data, sessions, results, scoredAt: Date.now() };
writeFileSync(outputPath, JSON.stringify(output, null, 2));
console.log(`\nScored ${scored} new instruments. Saved to ${outputPath}`);
