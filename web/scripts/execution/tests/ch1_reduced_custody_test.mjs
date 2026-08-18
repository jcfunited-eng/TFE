import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const strategist = await readFile(new URL("../3wa_strategist.mjs", import.meta.url), "utf8");
const bridge = await readFile(new URL("../alpaca_bridge.mjs", import.meta.url), "utf8");

assert.match(bridge, /CH1_REDUCED_ALLOCATION_PCT = 3\.5/);
assert.doesNotMatch(strategist, /l5_unified_shadow/);
assert.doesNotMatch(bridge, /from\s+["'][^"']*l5_unified_shadow/);
assert.match(strategist, /signal\.signal_class === "3WA"/);
assert.doesNotMatch(strategist, /degrading to empty species map/);

console.log("CH1 reduced custody: all assertions passed");
