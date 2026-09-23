/**
 * ENTRY-R5 liquidity floor, re-based 2026-09-23 from market cap to average
 * dollar volume. Values below are real rows from runtime_decisions_latest and
 * runtime_metrics_latest on 2026-09-23 (run 578df27a).
 *
 * Run: node web/scripts/execution/tests/ch2_liquidity_floor_test.mjs
 */

import assert from "node:assert/strict";
import { liquidityFloorPasses, CH2_MIN_AVG_DOLLAR_VOLUME } from "../ch2_strategist.mjs";

let passed = 0;
function t(name, fn) {
  fn();
  passed++;
  console.log(`ok - ${name}`);
}

t("floor is $2,000,000 a day", () => assert.equal(CH2_MIN_AVG_DOLLAR_VOLUME, 2_000_000));

// Names the cap filter dropped for having no cap on file
t("DOC   20.60 x 4,555,939 = $93.9M passes",  () => assert.equal(liquidityFloorPasses(20.6,  4555939.678), true));
t("IVZ   30.53 x 3,816,142 = $116.5M passes", () => assert.equal(liquidityFloorPasses(30.53, 3816142.978), true));
t("BFST  30.67 x 204,500 = $6.27M passes (cap table said 944.4)", () => assert.equal(liquidityFloorPasses(30.67, 204500.214), true));
t("AVBH  31.80 x 65,321 = $2.08M passes, just above", () => assert.equal(liquidityFloorPasses(31.8, 65321.161), true));

// Names that are genuinely thin
t("FNRN  17.39 x 102,459 = $1.78M fails", () => assert.equal(liquidityFloorPasses(17.39, 102459.385), false));
t("REKT  18.00 x 7,835 = $141k fails",    () => assert.equal(liquidityFloorPasses(18, 7835.187), false));
t("COIO  7.21 x 1,345 = $9.7k fails",     () => assert.equal(liquidityFloorPasses(7.21, 1345.056), false));

// Edges
t("exactly on the floor passes",     () => assert.equal(liquidityFloorPasses(10, 200_000), true));
t("one share short of the floor fails", () => assert.equal(liquidityFloorPasses(10, 199_999.9), false));
t("missing price fails",             () => assert.equal(liquidityFloorPasses(null, 1e9), false));
t("missing volume fails",            () => assert.equal(liquidityFloorPasses(50, undefined), false));
t("zero volume fails",               () => assert.equal(liquidityFloorPasses(50, 0), false));
t("strings from the database parse", () => assert.equal(liquidityFloorPasses("20.6", "4555939.6"), true));
t("garbage strings fail",            () => assert.equal(liquidityFloorPasses("abc", "4555939.6"), false));
t("custom floor honoured",           () => assert.equal(liquidityFloorPasses(10, 100_000, 5_000_000), false));

console.log(`${passed}/${passed} passed`);
